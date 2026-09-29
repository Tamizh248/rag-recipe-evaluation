"""Orchestrates a substitution request: ground it directly against one
recipe's own stored chunks (fetched by recipe_id, not similarity search),
resolve the swap against the fixed tables in app.substitution.tables, and
have the LLM (real or local) phrase the adapted recipe strictly from what
those fixed facts say. Every citation resolves to a real chunk_id, exactly
like ChatService (app.services.chat_service).
"""

import re

from app.core.tracing import (
    RetrievedChunkTrace,
    TraceLogger,
    TraceRecord,
    get_substitution_trace_logger,
    new_trace_id,
    now_iso,
)
from app.generation.llm import LLMProvider
from app.models.substitution import SubstitutionAnswer, SubstitutionResponse
from app.substitution.prompts import SUBSTITUTION_PROMPT_VERSION, build_substitution_prompt
from app.substitution.tables import Diet, allergens_for, allergens_for_substitute, find_substitute
from app.vectorstore.chroma_store import ChromaStore

_OVEN_LINE_RE = re.compile(r"[^.\n]*\d+\s*°?C[^.\n]*\d+\s*°?F[^.\n]*\.?", re.IGNORECASE)
_YIELD_LINE_RE = re.compile(r"Yields[^.\n]*\.", re.IGNORECASE)


def _refusal(reason: str) -> SubstitutionAnswer:
    return SubstitutionAnswer(answerable=False, answer=reason)


def _parse_ingredient_names(ingredients_text: str) -> list[str]:
    names = []
    for line in ingredients_text.splitlines():
        cell = line.split("|", 1)[0].strip()
        if not cell or cell.lower() == "ingredient":
            continue
        names.append(cell.lower())
    return names


def _extract_oven(method_text: str) -> str:
    match = _OVEN_LINE_RE.search(method_text)
    return match.group(0).strip() if match else ""


def _extract_servings(title_text: str) -> str:
    match = _YIELD_LINE_RE.search(title_text)
    return match.group(0).strip() if match else title_text.strip().splitlines()[0]


def _format_allergen_sentence(allergens: set) -> str:
    if not allergens:
        return "Contains no major allergens on file for the adapted recipe."
    names = sorted(a.value for a in allergens)
    return f"Contains {', '.join(names)}."


class SubstitutionService:
    def __init__(
        self,
        store: ChromaStore,
        llm_provider: LLMProvider,
        model_provider: str = "unknown",
        model_name: str = "unknown",
        trace_logger: TraceLogger | None = None,
    ):
        self.store = store
        self.llm_provider = llm_provider
        self.model_provider = model_provider
        self.model_name = model_name
        self.trace_logger = trace_logger or get_substitution_trace_logger()

    def substitute(self, recipe_id: str, ingredient: str, diet: str) -> SubstitutionResponse:
        chunks = self.store.get_recipe_chunks("structure_aware", recipe_id)
        if not chunks or "ingredients" not in chunks or "method" not in chunks:
            return self._to_response(_refusal(f"No recipe found with recipe_id {recipe_id!r}."), [])

        ingredients_chunk = chunks["ingredients"]
        method_chunk = chunks["method"]
        title_chunk = chunks.get("title")
        allergens_chunk = chunks.get("allergens")
        retrieved_ids = [c.chunk_id for c in chunks.values()]

        ingredient_names = _parse_ingredient_names(ingredients_chunk.text)
        target = ingredient.strip().lower()
        if target not in ingredient_names:
            return self._to_response(
                _refusal(f"{recipe_id!r} does not list {ingredient!r} as an ingredient."), retrieved_ids
            )

        try:
            Diet(diet)
        except ValueError:
            valid = ", ".join(d.value for d in Diet)
            return self._to_response(_refusal(f"Unknown diet {diet!r}. Valid diets: {valid}."), retrieved_ids)

        substitute = find_substitute(target, diet)

        other_allergens = set()
        for name in ingredient_names:
            if name != target:
                other_allergens.update(allergens_for(name))
        expected_allergens = other_allergens | (set(allergens_for_substitute(substitute)) if substitute else set())

        oven = _extract_oven(method_chunk.text)
        servings = _extract_servings(title_chunk.text) if title_chunk else ""

        trace = self._start_trace(recipe_id, ingredient, diet, retrieved_ids)

        prompt = build_substitution_prompt(
            target_ingredient=target,
            diet=diet,
            fixed_substitute=substitute,
            original_ingredients=ingredients_chunk.text,
            original_method=method_chunk.text,
            original_oven=oven,
            original_servings=servings,
            original_allergens=allergens_chunk.text if allergens_chunk else "",
            expected_allergens=_format_allergen_sentence(expected_allergens),
            retrieved_chunk_ids=retrieved_ids,
        )
        trace.llm_called = True
        raw_output = self.llm_provider.generate(prompt)
        trace.prompt = prompt
        trace.raw_llm_output = raw_output

        try:
            answer = SubstitutionAnswer.model_validate_json(raw_output)
        except Exception:
            answer = _refusal("Could not parse the substitution answer.")

        # Same citation discipline as ChatService: never trust a citation
        # the LLM invented outside what was actually retrieved.
        retrieved_id_set = set(retrieved_ids)
        if answer.answerable and not all(c.chunk_id in retrieved_id_set for c in answer.citations):
            answer = _refusal("Citation outside the retrieved recipe's own chunks.")

        trace.answerable = answer.answerable
        trace.answer = answer.answer
        trace.citations = [c.chunk_id for c in answer.citations]
        trace.final_refused = not answer.answerable
        self.trace_logger.log(trace)

        return self._to_response(answer, retrieved_ids)

    def _start_trace(self, recipe_id: str, ingredient: str, diet: str, retrieved_ids: list[str]) -> TraceRecord:
        return TraceRecord(
            trace_id=new_trace_id(),
            timestamp=now_iso(),
            prompt_version=SUBSTITUTION_PROMPT_VERSION,
            question=f"substitute {ingredient!r} in {recipe_id!r} for diet={diet!r}",
            strategy="structure-aware",
            dietary_tag_filters=[diet],
            retrieved=[RetrievedChunkTrace(chunk_id=cid, score=1.0, recipe_id=recipe_id, section="", text="") for cid in retrieved_ids],
            model_provider=self.model_provider,
            model_name=self.model_name,
            refused_pre_llm=False,
        )

    @staticmethod
    def _to_response(answer: SubstitutionAnswer, retrieved_ids: list[str]) -> SubstitutionResponse:
        return SubstitutionResponse(
            answer=answer.answer,
            refused=not answer.answerable,
            substitute_ingredient=answer.substitute_ingredient,
            adapted_ingredients=answer.adapted_ingredients,
            adapted_method=answer.adapted_method,
            oven=answer.oven,
            servings=answer.servings,
            allergens=answer.allergens,
            citations=answer.citations,
            retrieved_chunk_ids=sorted(retrieved_ids),
        )

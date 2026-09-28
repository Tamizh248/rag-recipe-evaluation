"""Deterministic, no-API-key generation stand-in for substitution answers -
same role as app.generation.llm.LocalExtractiveProvider, but for the
substitution JSON contract (app.substitution.prompts) instead of the plain
grounding contract. Parses the exact prompt build_substitution_prompt()
produces and composes the answer mechanically: it never invents a
substitute or an allergen, only rearranges what the prompt already contains.
"""

import json
import re

from app.generation.llm import AnthropicProvider, LLMProvider

_FIELD_RE = re.compile(
    r"TARGET_INGREDIENT: (?P<target>.*)\n"
    r"DIET: (?P<diet>.*)\n"
    r"FIXED_SUBSTITUTE: (?P<substitute>.*)\n\n"
    r"ORIGINAL_INGREDIENTS:\n(?P<ingredients>.*?)\n\n"
    r"ORIGINAL_METHOD:\n(?P<method>.*?)\n\n"
    r"ORIGINAL_OVEN:\n(?P<oven>.*?)\n\n"
    r"ORIGINAL_SERVINGS:\n(?P<servings>.*?)\n\n"
    r"ORIGINAL_ALLERGENS:\n(?P<allergens>.*?)\n\n"
    r"EXPECTED_ALLERGENS:\n(?P<expected_allergens>.*?)\n\n"
    r"RETRIEVED_CHUNK_IDS: (?P<chunk_ids>.*)",
    re.DOTALL,
)


def _replace_ingredient_line(line: str, target: str, substitute: str) -> str:
    cells = line.split("|")
    if cells and cells[0].strip().lower() == target.strip().lower():
        return " | ".join([substitute] + [cell.strip() for cell in cells[1:]])
    return line


def _method_replacement_pattern(target: str, method_text: str) -> str:
    """Method prose doesn't always spell an ingredient the same way its
    table row does ("Eggs (whole)" in the table, just "eggs" in the method;
    "Walnuts (chopped)" in the table, "chopped walnuts" in the method) - try
    the exact table name first, then the name with its trailing
    parenthetical stripped, and use whichever one actually appears."""
    if re.search(re.escape(target), method_text, flags=re.IGNORECASE):
        return target
    base = re.sub(r"\s*\([^)]*\)\s*$", "", target).strip()
    if base and re.search(re.escape(base), method_text, flags=re.IGNORECASE):
        return base
    return target


class LocalSubstitutionProvider(LLMProvider):
    def generate(self, prompt: str) -> str:
        match = _FIELD_RE.search(prompt)
        if not match:
            return json.dumps(
                {
                    "answerable": False,
                    "answer": "Could not parse the substitution request.",
                    "substitute_ingredient": None,
                    "adapted_ingredients": [],
                    "adapted_method": "",
                    "oven": "",
                    "servings": "",
                    "allergens": "",
                    "citations": [],
                }
            )

        fields = match.groupdict()
        target = fields["target"].strip()
        diet = fields["diet"].strip()
        substitute = fields["substitute"].strip()
        chunk_ids = [c.strip() for c in fields["chunk_ids"].split(",") if c.strip()]

        if substitute == "NONE_ON_FILE":
            return json.dumps(
                {
                    "answerable": False,
                    "answer": "No verified substitute is on file for this ingredient under this diet.",
                    "substitute_ingredient": None,
                    "adapted_ingredients": [],
                    "adapted_method": "",
                    "oven": "",
                    "servings": "",
                    "allergens": "",
                    "citations": [],
                }
            )

        adapted_ingredients = [
            _replace_ingredient_line(line, target, substitute)
            for line in fields["ingredients"].strip().splitlines()
        ]
        method_text = fields["method"].strip()
        pattern = _method_replacement_pattern(target, method_text)
        adapted_method = re.sub(re.escape(pattern), substitute, method_text, flags=re.IGNORECASE)

        return json.dumps(
            {
                "answerable": True,
                "answer": f"Use {substitute} in place of {target} for a {diet} version of this recipe.",
                "substitute_ingredient": substitute,
                "adapted_ingredients": adapted_ingredients,
                "adapted_method": adapted_method,
                "oven": fields["oven"].strip(),
                "servings": fields["servings"].strip(),
                "allergens": fields["expected_allergens"].strip(),
                "citations": [{"chunk_id": chunk_id} for chunk_id in chunk_ids],
            }
        )


def get_substitution_provider(provider_name: str, api_key: str, model: str) -> LLMProvider:
    """Same factory pattern as app.generation.llm.get_llm_provider - shares
    LLM_PROVIDER/LLM_API_KEY/LLM_MODEL, so switching to a real Claude model
    upgrades both chat answers AND substitution answers with the same
    single .env change."""
    if provider_name == "anthropic":
        return AnthropicProvider(api_key=api_key, model=model)
    if provider_name == "local":
        return LocalSubstitutionProvider()
    raise ValueError(f"Unknown LLM_PROVIDER: {provider_name}")

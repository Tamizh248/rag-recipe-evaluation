"""Build the Week-5 trace corpus by running a broad, realistic spread of
recipe questions through the REAL chat pipeline (app/services/chat_service.py) -
retrieval -> grounding -> LLM -> citation/refusal, exactly what /api/chat does.
Every answer, citation, and refusal below is genuinely produced by that
pipeline; nothing in traces.jsonl is hand-written or simulated.

Assumption (disclosed, same as the rest of this project's evaluation write-ups):
no historical user-question log exists for this app yet, so this script is
this project's honest stand-in for "the recipe assistant running all week" -
it deliberately spans direct fact lookups, paraphrases, cross-recipe
comparisons, negation ("is X gluten-free?"), ambiguous no-recipe-named
questions, scaling/math, aggregation-across-recipes, and out-of-corpus
nutrition/substitution questions, because a corpus of only easy direct
lookups would teach Week 5's random sample nothing.

Usage:
    python scripts/generate_traces.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.config import get_settings
from app.core.tracing import TRACES_PATH
from app.embeddings.sentence_transformer import get_embedding_model
from app.generation.llm import get_llm_provider
from app.retrieval.retriever import Retriever
from app.services.chat_service import ChatService
from app.vectorstore.chroma_store import ChromaStore

STRATEGY = "structure-aware"

RECIPES = [
    ("sourdough_country_2kg", "Sourdough Country Loaf"),
    ("rye_sourdough_900g", "Caraway Rye Sourdough"),
    ("rosemary_olive_focaccia_1500g", "Rosemary Olive Focaccia"),
    ("brioche_sourdough_900g", "Sourdough Brioche Loaf"),
    ("cinnamon_raisin_walnut_800g", "Cinnamon Raisin Walnut Sourdough"),
    ("whole_wheat_flaxseed_1800g", "Whole Wheat Flaxseed Sourdough"),
]


def _direct_fact_questions() -> list[str]:
    questions = []
    for _, name in RECIPES:
        questions.append(f"How much fine sea salt, in grams, is used in the {name}?")
        questions.append(f"What is the baker's percentage of salt in the {name}?")
        questions.append(f"What temperature should the oven be for baking the {name}?")
        questions.append(f"How long does the {name} bake for?")
        questions.append(f"What allergens does the {name} contain?")
        questions.append(f"What is step 3 of the {name} method?")
    return questions


def _casual_paraphrase_questions() -> list[str]:
    return [
        "how much salt for the country loaf sourdough",
        "whats the oven temp for the rye bread with caraway",
        "how long do i leave the focaccia dough before baking it",
        "brioche loaf bake time and temp?",
        "does the walnut cinnamon raisin bread have nuts in it",
        "flaxseed sourdough autolyse time",
        "how much water in the big country sourdough loaf",
        "salt percentage rye bread",
        "when do i add the caraway seeds",
        "how long to cold proof the whole wheat one",
        "internal temp for the brioche when its done",
        "how much olive oil does the focaccia need",
        "walnut bread bake temperature",
        "how much starter goes in the focaccia dough",
        "sourdough brioche egg wash step",
    ]


def _cross_recipe_comparison_questions() -> list[str]:
    return [
        "Which recipe has a higher hydration percentage, the Sourdough Country Loaf or the Whole Wheat Flaxseed Sourdough?",
        "Which uses more salt in total, the Rosemary Olive Focaccia or the Sourdough Brioche Loaf?",
        "Between the Caraway Rye Sourdough and the Cinnamon Raisin Walnut Sourdough, which has a longer bulk ferment?",
        "Is the oven temperature for the Sourdough Country Loaf higher or lower than for the Rosemary Olive Focaccia?",
        "Which bakes longer, the Sourdough Brioche Loaf or the Whole Wheat Flaxseed Sourdough?",
        "Does the Caraway Rye Sourdough or the Sourdough Country Loaf use a higher percentage of starter?",
    ]


def _ambiguous_no_recipe_named_questions() -> list[str]:
    return [
        "How much salt should I use?",
        "What temperature should I bake at?",
        "How long does the dough need to cold proof?",
        "When do I add the starter?",
        "How long should I autolyse for?",
    ]


def _scaling_math_questions() -> list[str]:
    return [
        "If I double the Rosemary Olive Focaccia recipe, how much water do I need?",
        "If I want to make a 1kg version of the Sourdough Country Loaf, how much flour should I use?",
        "How much salt would I need for a half-batch of the Caraway Rye Sourdough?",
        "If I triple the Cinnamon Raisin Walnut Sourdough, how many grams of walnuts do I need?",
        "What quantities do I need to make two Sourdough Brioche loaves instead of one?",
        "Scale the Whole Wheat Flaxseed Sourdough recipe down to 500g of flour - what are the new ingredient weights?",
    ]


def _negation_yes_no_questions() -> list[str]:
    return [
        "Is the Caraway Rye Sourdough gluten-free?",
        "Is the Sourdough Brioche Loaf vegan?",
        "Does the Rosemary Olive Focaccia contain eggs?",
        "Is the Sourdough Country Loaf dairy-free?",
        "Does the Whole Wheat Flaxseed Sourdough contain tree nuts?",
        "Is the Cinnamon Raisin Walnut Sourdough nut-free?",
    ]


def _aggregation_questions() -> list[str]:
    return [
        "Which recipes are vegan?",
        "Which recipes contain tree nuts?",
        "List all recipes that contain dairy.",
        "How many of the six recipes are vegan?",
    ]


def _substitution_preview_questions() -> list[str]:
    """Not a supported feature yet (Week 6 adds a substitution table) - these
    exist to see, honestly, what the current grounded pipeline does when
    asked anyway: refuse, or answer from context alone."""
    return [
        "What can I use instead of butter in the Sourdough Brioche Loaf if I'm vegan?",
        "I'm dairy-free - what should I use instead of the whole milk in the brioche?",
        "What's a gluten-free substitute for the bread flour in the Sourdough Country Loaf?",
        "Can I replace the walnuts in the Cinnamon Raisin Walnut Sourdough with a different nut?",
        "What could I use instead of the active sourdough starter in the focaccia?",
        "Is there a substitute for caraway seeds in the rye bread?",
    ]


def _unanswerable_nutrition_questions() -> list[str]:
    questions = []
    facts = ["protein content", "calorie count", "sodium content per serving", "total sugar", "fiber content", "glycemic index"]
    for (_, name), fact in zip(RECIPES, facts):
        questions.append(f"What is the {fact} of the {name}?")
    return questions


def _section_step_questions() -> list[str]:
    return [
        "What is the last step of the Sourdough Country Loaf method?",
        "What happens during step 4 of the Rosemary Olive Focaccia recipe?",
        "What is the first step when making the Caraway Rye Sourdough?",
        "Describe step 6 of the Whole Wheat Flaxseed Sourdough method.",
        "What does step 2 of the Sourdough Brioche Loaf method involve?",
    ]


def build_question_set() -> list[str]:
    questions: list[str] = []
    questions += _direct_fact_questions()
    questions += _casual_paraphrase_questions()
    questions += _cross_recipe_comparison_questions()
    questions += _ambiguous_no_recipe_named_questions()
    questions += _scaling_math_questions()
    questions += _negation_yes_no_questions()
    questions += _aggregation_questions()
    questions += _substitution_preview_questions()
    questions += _unanswerable_nutrition_questions()
    questions += _section_step_questions()
    return questions


def main() -> None:
    settings = get_settings()
    embedding_model = get_embedding_model()
    store = ChromaStore(settings.chroma_persist_path)
    retriever = Retriever(store, embedding_model)
    llm_provider = get_llm_provider(settings.llm_provider, settings.llm_api_key, settings.llm_model)
    chat_service = ChatService(
        retriever,
        llm_provider,
        top_k=settings.top_k,
        model_provider=settings.llm_provider,
        model_name=settings.llm_model,
    )

    questions = build_question_set()
    print(f"Running {len(questions)} questions through the real chat pipeline...")
    for i, question in enumerate(questions, start=1):
        chat_service.answer(question, strategy=STRATEGY)
        if i % 20 == 0 or i == len(questions):
            print(f"  {i}/{len(questions)} done")

    print(f"\nWrote {len(questions)} trace records to {TRACES_PATH}")


if __name__ == "__main__":
    main()

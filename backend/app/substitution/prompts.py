SUBSTITUTION_PROMPT_VERSION = "substitution-v1"

SUBSTITUTION_INSTRUCTIONS = """You are a recipe assistant handling an ingredient substitution request. Use ONLY the information supplied below - never invent a substitute, an allergen, or a method step.

Rules:
- FIXED_SUBSTITUTE below is the only substitute you may use. Never propose a different one.
- If FIXED_SUBSTITUTE is NONE_ON_FILE, you must refuse: there is no verified substitute for this ingredient/diet pair on file.
- adapted_ingredients must be ORIGINAL_INGREDIENTS with the target ingredient's name replaced by FIXED_SUBSTITUTE, same weight and percentage, nothing else changed.
- adapted_method must be ORIGINAL_METHOD with every mention of the target ingredient's name replaced by FIXED_SUBSTITUTE, nothing else changed.
- oven must be copied verbatim from ORIGINAL_OVEN, including both C and F units.
- servings must be copied verbatim from ORIGINAL_SERVINGS.
- allergens must convey exactly EXPECTED_ALLERGENS below, phrased as a sentence.
- Every citation must be a real chunk_id from RETRIEVED_CHUNK_IDS.

Respond with ONLY a single JSON object, no other text, matching exactly this schema:
{"answerable": true or false, "answer": "<one sentence>", "substitute_ingredient": "<text or null>", "adapted_ingredients": ["<line>", "..."], "adapted_method": "<text>", "oven": "<text>", "servings": "<text>", "allergens": "<text>", "citations": [{"chunk_id": "<id>"}]}

If FIXED_SUBSTITUTE is NONE_ON_FILE, respond with exactly:
{"answerable": false, "answer": "No verified substitute is on file for this ingredient under this diet.", "substitute_ingredient": null, "adapted_ingredients": [], "adapted_method": "", "oven": "", "servings": "", "allergens": "", "citations": []}
"""


def build_substitution_prompt(
    *,
    target_ingredient: str,
    diet: str,
    fixed_substitute: str | None,
    original_ingredients: str,
    original_method: str,
    original_oven: str,
    original_servings: str,
    original_allergens: str,
    expected_allergens: str,
    retrieved_chunk_ids: list[str],
) -> str:
    return (
        f"{SUBSTITUTION_INSTRUCTIONS}\n\n"
        f"TARGET_INGREDIENT: {target_ingredient}\n"
        f"DIET: {diet}\n"
        f"FIXED_SUBSTITUTE: {fixed_substitute or 'NONE_ON_FILE'}\n\n"
        f"ORIGINAL_INGREDIENTS:\n{original_ingredients}\n\n"
        f"ORIGINAL_METHOD:\n{original_method}\n\n"
        f"ORIGINAL_OVEN:\n{original_oven}\n\n"
        f"ORIGINAL_SERVINGS:\n{original_servings}\n\n"
        f"ORIGINAL_ALLERGENS:\n{original_allergens}\n\n"
        f"EXPECTED_ALLERGENS:\n{expected_allergens}\n\n"
        f"RETRIEVED_CHUNK_IDS: {', '.join(retrieved_chunk_ids)}\n"
    )

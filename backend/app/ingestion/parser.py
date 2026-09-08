import re
from dataclasses import dataclass, field

FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)
SECTION_HEADERS = ("INGREDIENTS:", "METHOD:", "ALLERGENS:")


@dataclass
class ParsedRecipe:
    recipe_id: str
    cuisine: str
    dietary_tags: list[str]
    source_file: str
    title: str
    overview_text: str
    ingredient_header: str | None
    ingredient_rows: list[str] = field(default_factory=list)
    method_steps: list[str] = field(default_factory=list)
    allergens_text: str = ""

    @property
    def is_well_formed(self) -> bool:
        """True if the parser found all four expected recipe sections."""
        return bool(
            self.title and self.ingredient_rows and self.method_steps and self.allergens_text
        )


def strip_frontmatter(raw_text: str) -> str:
    """Return the document body with any leading `--- ... ---` front-matter removed."""
    _, body = _parse_frontmatter(raw_text)
    return body


def _parse_frontmatter(text: str) -> tuple[dict[str, str], str]:
    match = FRONTMATTER_RE.match(text)
    if not match:
        return {}, text

    raw_fields = match.group(1)
    fields: dict[str, str] = {}
    for line in raw_fields.splitlines():
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        fields[key.strip()] = value.strip()

    body = text[match.end():]
    return fields, body


def _find_section_bounds(body: str) -> dict[str, tuple[int, int]]:
    """Locate the start/end character offsets of each known section header."""
    positions: list[tuple[str, int]] = []
    for header in SECTION_HEADERS:
        idx = body.find(header)
        if idx != -1:
            positions.append((header, idx))
    positions.sort(key=lambda p: p[1])

    bounds: dict[str, tuple[int, int]] = {}
    for i, (header, start) in enumerate(positions):
        end = positions[i + 1][1] if i + 1 < len(positions) else len(body)
        bounds[header] = (start, end)
    return bounds


def _parse_ingredient_table(section_text: str) -> tuple[str | None, list[str]]:
    lines = [ln.strip() for ln in section_text.splitlines() if "|" in ln]
    if not lines:
        return None, []
    header, *rows = lines
    return header, rows


def _parse_method(section_text: str) -> list[str]:
    steps = []
    for line in section_text.splitlines():
        line = line.strip()
        if re.match(r"^\d+[.)]\s+", line):
            steps.append(re.sub(r"^\d+[.)]\s+", "", line))
    return steps


_SECTION_KEY_MAP = {
    "INGREDIENTS:": "ingredients",
    "METHOD:": "method",
    "ALLERGENS:": "allergens",
}


def get_section_spans(body: str) -> dict[str, tuple[int, int]]:
    """Map each recipe section to its (start, end) character offsets within `body`.

    Used only for post-hoc metadata tagging (e.g. by the baseline chunker,
    which must NOT use this to decide chunk boundaries) and by the
    structure-aware chunker to slice out whole sections.
    """
    bounds = _find_section_bounds(body)
    title_end = min((b[0] for b in bounds.values()), default=len(body))
    spans: dict[str, tuple[int, int]] = {"title": (0, title_end)}
    for header, (start, end) in bounds.items():
        spans[_SECTION_KEY_MAP[header]] = (start, end)
    return spans


def parse_recipe(source_file: str, raw_text: str) -> ParsedRecipe:
    """Parse a plain-text recipe card into its structural parts.

    This parser is deliberately tolerant: missing sections do not raise, they
    simply leave the corresponding field empty so callers (or tests) can
    detect and report malformed source documents rather than crashing the
    whole ingestion run.
    """
    frontmatter, body = _parse_frontmatter(raw_text)
    recipe_id = frontmatter.get("recipe_id", "")
    cuisine = frontmatter.get("cuisine", "")
    dietary_tags_raw = frontmatter.get("dietary_tags", "")
    dietary_tags = [t.strip() for t in dietary_tags_raw.split(",") if t.strip()]

    title_match = re.search(r"RECIPE:\s*(.+)", body)
    title = title_match.group(1).strip() if title_match else ""

    bounds = _find_section_bounds(body)

    # Overview = everything between the title line and the first section header
    # (captures title + any "Yields ..." line).
    overview_start = title_match.end() if title_match else 0
    overview_end = min((b[0] for b in bounds.values()), default=len(body))
    overview_text = body[overview_start:overview_end].strip()

    ingredient_header = None
    ingredient_rows: list[str] = []
    if "INGREDIENTS:" in bounds:
        start, end = bounds["INGREDIENTS:"]
        ingredient_header, ingredient_rows = _parse_ingredient_table(body[start:end])

    method_steps: list[str] = []
    if "METHOD:" in bounds:
        start, end = bounds["METHOD:"]
        method_steps = _parse_method(body[start:end])

    allergens_text = ""
    if "ALLERGENS:" in bounds:
        start, end = bounds["ALLERGENS:"]
        allergens_text = body[start + len("ALLERGENS:"):end].strip()

    if not recipe_id:
        recipe_id = re.sub(r"[^a-z0-9]+", "_", title.lower()).strip("_")

    return ParsedRecipe(
        recipe_id=recipe_id,
        cuisine=cuisine,
        dietary_tags=dietary_tags,
        source_file=source_file,
        title=title,
        overview_text=overview_text,
        ingredient_header=ingredient_header,
        ingredient_rows=ingredient_rows,
        method_steps=method_steps,
        allergens_text=allergens_text,
    )

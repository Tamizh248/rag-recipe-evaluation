from dataclasses import dataclass
from pathlib import Path

import pymupdf
from docx import Document as DocxDocument

SUPPORTED_EXTENSIONS = {".txt", ".md", ".pdf", ".docx"}


@dataclass
class RawDocument:
    source_file: str
    text: str


def _load_txt(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _load_pdf(path: Path) -> str:
    with pymupdf.open(path) as doc:
        return "\n".join(page.get_text() for page in doc)


def _load_docx(path: Path) -> str:
    doc = DocxDocument(str(path))
    return "\n".join(p.text for p in doc.paragraphs)


def load_document(path: Path) -> RawDocument:
    suffix = path.suffix.lower()
    if suffix not in SUPPORTED_EXTENSIONS:
        raise ValueError(f"Unsupported file type: {path.name}")

    if suffix in (".txt", ".md"):
        text = _load_txt(path)
    elif suffix == ".pdf":
        text = _load_pdf(path)
    elif suffix == ".docx":
        text = _load_docx(path)
    else:  # pragma: no cover - guarded above
        raise ValueError(f"Unsupported file type: {path.name}")

    return RawDocument(source_file=path.name, text=text)


def load_documents(directory: Path, filenames: list[str] | None = None) -> list[RawDocument]:
    """Load documents from a directory.

    If `filenames` is given, only those exact files are loaded (used to enforce
    the "only these 6 new cards" ingestion constraint). Otherwise every
    supported file in the directory is loaded.
    """
    if filenames is not None:
        paths = [directory / name for name in filenames]
        missing = [str(p) for p in paths if not p.exists()]
        if missing:
            raise FileNotFoundError(f"Missing recipe source files: {missing}")
    else:
        paths = sorted(
            p for p in directory.iterdir() if p.suffix.lower() in SUPPORTED_EXTENSIONS
        )

    return [load_document(p) for p in paths]

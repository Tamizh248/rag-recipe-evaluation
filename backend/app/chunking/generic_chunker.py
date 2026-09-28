def chunk_text(text: str, chunk_size: int, chunk_overlap: int) -> list[str]:
    """Fixed-size sliding window over arbitrary text, no structural awareness.

    Same windowing algorithm as `CurrentChunker` (recipe baseline), but
    decoupled from `RecipeDocument`/section metadata since uploaded
    documents have no fixed schema to label sections against.
    """
    if chunk_size <= 0:
        raise ValueError("chunk_size must be positive")
    if chunk_overlap < 0 or chunk_overlap >= chunk_size:
        raise ValueError("chunk_overlap must be >= 0 and smaller than chunk_size")

    text_len = len(text)
    if text_len == 0:
        return []

    step = chunk_size - chunk_overlap
    pieces: list[str] = []
    start = 0
    while start < text_len:
        end = min(start + chunk_size, text_len)
        piece = text[start:end].strip()
        if piece:
            pieces.append(piece)
        if end == text_len:
            break
        start += step

    return pieces

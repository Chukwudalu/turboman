def split_text(text: str, max_chars: int = 500) -> list[str]:
    """
    Split a document into chunks at paragraph boundaries.
    Chunks stay under max_chars so vector embeddings are focused.
    """
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    chunks: list[str] = []
    current = ""
    for para in paragraphs:
        if current and len(current) + len(para) + 2 > max_chars:
            chunks.append(current.strip())
            current = para
        else:
            current = f"{current}\n\n{para}" if current else para
    if current.strip():
        chunks.append(current.strip())
    return chunks

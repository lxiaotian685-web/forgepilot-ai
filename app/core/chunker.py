from __future__ import annotations

from app.core.parser import Page


def chunk_text(text: str, chunk_size: int = 400, overlap: int = 60) -> list[str]:
    if chunk_size <= 0:
        raise ValueError("chunk_size 必须大于 0")
    if overlap < 0 or overlap >= chunk_size:
        raise ValueError("overlap 必须满足 0 <= overlap < chunk_size")
    if len(text) <= chunk_size:
        return [text]

    chunks: list[str] = []
    start = 0
    while start < len(text):
        end = min(start + chunk_size, len(text))
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        if end == len(text):
            break
        start = end - overlap
    return chunks


def chunk_pages(
    pages: list[Page], chunk_size: int = 400, overlap: int = 60
) -> list[tuple[int, str]]:
    """返回 (页码, 分块文本) 列表，保留页码作为证据来源。"""
    result: list[tuple[int, str]] = []
    for page in pages:
        for text in chunk_text(page.text, chunk_size, overlap):
            result.append((page.number, text))
    return result

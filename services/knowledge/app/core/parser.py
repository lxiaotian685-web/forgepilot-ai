from __future__ import annotations

import io
from dataclasses import dataclass

PAGE_SEPARATOR = "\n\n---PAGE---\n\n"


@dataclass
class Page:
    number: int
    text: str


def parse_text(content: str, separator: str = PAGE_SEPARATOR) -> list[Page]:
    pages: list[Page] = []
    for number, raw in enumerate(content.split(separator), start=1):
        text = raw.strip()
        if text:
            pages.append(Page(number=number, text=text))
    return pages


def _read_pdf(reader) -> list[Page]:
    pages: list[Page] = []
    for number, page in enumerate(reader.pages, start=1):
        text = (page.extract_text() or "").strip()
        if text:
            pages.append(Page(number=number, text=text))
    return pages


def parse_pdf(path) -> list[Page]:
    """解析 PDF 文件为分页文本。"""
    try:
        from pypdf import PdfReader
    except ImportError as exc:
        raise RuntimeError(
            "PDF 解析需要安装 pypdf：pip install pypdf"
        ) from exc

    return _read_pdf(PdfReader(str(path)))


def parse_pdf_bytes(data: bytes) -> list[Page]:
    """解析 PDF 字节内容，供上传接口使用。"""
    try:
        from pypdf import PdfReader
    except ImportError as exc:
        raise RuntimeError(
            "PDF 解析需要安装 pypdf：pip install pypdf"
        ) from exc

    return _read_pdf(PdfReader(io.BytesIO(data)))

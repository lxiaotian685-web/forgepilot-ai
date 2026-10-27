from __future__ import annotations

from pathlib import Path

from app.core.parser import Page, parse_pdf_bytes, parse_text

TEXT_SUFFIXES = {".txt", ".md"}
PDF_SUFFIXES = {".pdf"}


class UploadError(ValueError):
    def __init__(self, status_code: int, message: str):
        super().__init__(message)
        self.status_code = status_code


def safe_filename(filename: str) -> str:
    return filename.replace("\\", "/").rsplit("/", 1)[-1].strip()


def parse_document(filename: str, data: bytes) -> list[Page]:
    suffix = Path(filename).suffix.lower()
    if suffix in PDF_SUFFIXES:
        if not data.startswith(b"%PDF-"):
            raise UploadError(415, "文件内容不是有效的 PDF")
        try:
            pages = parse_pdf_bytes(data)
        except Exception as exc:
            raise UploadError(
                422, "PDF 解析失败，请检查文件是否损坏或加密"
            ) from exc
        if not pages:
            raise UploadError(422, "PDF 中没有可提取文本")
        return pages

    if suffix in TEXT_SUFFIXES:
        text = _decode_text(data)
        pages = parse_text(text)
        if not pages:
            raise UploadError(422, "文档内容为空")
        return pages

    raise UploadError(415, "仅支持 PDF、TXT、MD 文件")


def _decode_text(data: bytes) -> str:
    if b"\x00" in data:
        raise UploadError(415, "文本文件包含二进制内容")
    for encoding in ("utf-8-sig", "gb18030"):
        try:
            return data.decode(encoding)
        except UnicodeDecodeError:
            continue
    raise UploadError(422, "文本编码无法识别，请使用 UTF-8")

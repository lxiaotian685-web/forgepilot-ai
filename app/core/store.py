from __future__ import annotations

import json
import uuid
from pathlib import Path

from app.core.chunker import chunk_pages
from app.core.parser import parse_text
from app.core.search import BM25Index
from app.schemas.document import Chunk, Document, Evidence


class KnowledgeBase:
    def __init__(self, storage_path: Path | None = None):
        self.storage_path = storage_path
        self._documents: dict[str, Document] = {}
        self._chunks: list[Chunk] = []

    def ingest(
        self,
        *,
        title: str,
        equipment_model: str,
        content: str,
        version: str = "1.0",
        source: str = "",
    ) -> tuple[Document, list[Chunk]]:
        pages = parse_text(content)
        document = Document(
            id=uuid.uuid4().hex[:12],
            title=title,
            equipment_model=equipment_model,
            version=version,
            source=source,
            page_count=len(pages),
        )
        chunks: list[Chunk] = []
        for page, text in chunk_pages(pages):
            chunks.append(
                Chunk(
                    id=uuid.uuid4().hex[:12],
                    document_id=document.id,
                    page=page,
                    chunk_index=len(chunks),
                    text=text,
                )
            )

        self._documents[document.id] = document
        self._chunks.extend(chunks)
        self.save()
        return document, chunks

    def search(
        self,
        query: str,
        equipment_model: str | None = None,
        top_k: int = 5,
    ) -> list[Evidence]:
        candidates = self._chunks
        if equipment_model:
            allowed = {
                doc_id
                for doc_id, doc in self._documents.items()
                if doc.equipment_model == equipment_model
            }
            candidates = [c for c in candidates if c.document_id in allowed]

        if not candidates:
            return []

        index = BM25Index([c.text for c in candidates])
        results: list[Evidence] = []
        for idx, score in index.search(query, top_k):
            chunk = candidates[idx]
            doc = self._documents[chunk.document_id]
            results.append(
                Evidence(
                    document_id=doc.id,
                    title=doc.title,
                    page=chunk.page,
                    snippet=chunk.text[:200],
                    score=round(score, 4),
                )
            )
        return results

    def list_documents(self) -> list[Document]:
        return list(self._documents.values())

    def clear(self) -> None:
        self._documents.clear()
        self._chunks.clear()

    def save(self) -> None:
        if self.storage_path is None:
            return
        payload = {
            "documents": [d.model_dump() for d in self._documents.values()],
            "chunks": [c.model_dump() for c in self._chunks],
        }
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        self.storage_path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
        )

    def load(self) -> None:
        if self.storage_path is None or not self.storage_path.exists():
            return
        payload = json.loads(self.storage_path.read_text(encoding="utf-8"))
        self._documents = {
            d["id"]: Document(**d) for d in payload.get("documents", [])
        }
        self._chunks = [Chunk(**c) for c in payload.get("chunks", [])]

from __future__ import annotations

import json
import os
import tempfile
import threading
import uuid
from pathlib import Path

from app.core.chunker import chunk_pages
from app.core.parser import Page, parse_text
from app.core.search import BM25Index
from app.schemas.document import Chunk, Document, Evidence

MAX_CACHED_INDEXES = 64


class KnowledgeBase:
    def __init__(self, storage_path: Path | None = None):
        self.storage_path = storage_path
        self._documents: dict[str, Document] = {}
        self._chunks: list[Chunk] = []
        self._lock = threading.RLock()
        self._version = 0
        self._index_cache: dict[tuple[int, str, str], BM25Index] = {}

    def ingest(
        self,
        *,
        title: str,
        equipment_model: str,
        content: str,
        organization_id: str = "demo-org",
        version: str = "1.0",
        source: str = "",
    ) -> tuple[Document, list[Chunk]]:
        return self.ingest_pages(
            title=title,
            equipment_model=equipment_model,
            pages=parse_text(content),
            organization_id=organization_id,
            version=version,
            source=source,
        )

    def ingest_pages(
        self,
        *,
        title: str,
        equipment_model: str,
        pages: list[Page],
        organization_id: str = "demo-org",
        version: str = "1.0",
        source: str = "",
    ) -> tuple[Document, list[Chunk]]:
        with self._lock:
            if not pages:
                raise ValueError("文档内容为空")
            document = Document(
                id=uuid.uuid4().hex[:16],
                title=title,
                equipment_model=equipment_model,
                organization_id=organization_id,
                version=version,
                source=source,
                page_count=len(pages),
            )
            chunks: list[Chunk] = []
            for page, text in chunk_pages(pages):
                chunks.append(
                    Chunk(
                        id=uuid.uuid4().hex[:16],
                        document_id=document.id,
                        page=page,
                        chunk_index=len(chunks),
                        text=text,
                    )
                )

            self._documents[document.id] = document
            self._chunks.extend(chunks)
            self._version += 1
            self._index_cache.clear()
            self.save()
            return document, chunks

    def search(
        self,
        query: str,
        equipment_model: str | None = None,
        top_k: int = 5,
        organization_id: str | None = None,
    ) -> list[Evidence]:
        with self._lock:
            candidates = self._candidates(equipment_model, organization_id)
            if not candidates:
                return []

            key = (self._version, equipment_model or "", organization_id or "")
            index = self._index_cache.get(key)
            if index is None:
                index = BM25Index([c.text for c in candidates])
                if len(self._index_cache) >= MAX_CACHED_INDEXES:
                    self._index_cache.clear()
                self._index_cache[key] = index

            results: list[Evidence] = []
            for idx, score in index.search(query, top_k):
                chunk = candidates[idx]
                doc = self._documents[chunk.document_id]
                results.append(
                    Evidence(
                        id=f"{doc.id}@{doc.version}#p{chunk.page}c{chunk.chunk_index}",
                        document_id=doc.id,
                        organization_id=doc.organization_id,
                        version=doc.version,
                        title=doc.title,
                        page=chunk.page,
                        chunk_index=chunk.chunk_index,
                        snippet=chunk.text[:200],
                        score=round(score, 4),
                    )
                )
            return results

    def list_documents(
        self,
        organization_id: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[Document]:
        with self._lock:
            documents = [
                doc
                for doc in self._documents.values()
                if organization_id is None
                or doc.organization_id == organization_id
            ]
            documents.sort(key=lambda doc: (doc.title, doc.id))
            return documents[offset : offset + limit]

    def get_document(
        self, document_id: str, organization_id: str
    ) -> tuple[Document, list[Chunk]] | None:
        with self._lock:
            document = self._documents.get(document_id)
            if document is None or document.organization_id != organization_id:
                return None
            chunks = [
                chunk for chunk in self._chunks if chunk.document_id == document_id
            ]
            return document, chunks

    def delete_document(self, document_id: str, organization_id: str) -> bool:
        with self._lock:
            document = self._documents.get(document_id)
            if document is None or document.organization_id != organization_id:
                return False
            del self._documents[document_id]
            self._chunks = [
                chunk for chunk in self._chunks if chunk.document_id != document_id
            ]
            self._version += 1
            self._index_cache.clear()
            self.save()
            return True

    def clear(self) -> None:
        with self._lock:
            self._documents.clear()
            self._chunks.clear()
            self._version += 1
            self._index_cache.clear()

    def save(self) -> None:
        if self.storage_path is None:
            return
        with self._lock:
            payload = {
                "documents": [d.model_dump() for d in self._documents.values()],
                "chunks": [c.model_dump() for c in self._chunks],
            }
            parent = self.storage_path.parent
            parent.mkdir(parents=True, exist_ok=True)
            fd, tmp_name = tempfile.mkstemp(
                prefix=".knowledge-base-", suffix=".tmp", dir=parent
            )
            try:
                with os.fdopen(fd, "w", encoding="utf-8") as handle:
                    json.dump(payload, handle, ensure_ascii=False, indent=2)
                    handle.flush()
                    os.fsync(handle.fileno())
                os.replace(tmp_name, self.storage_path)
            finally:
                if os.path.exists(tmp_name):
                    os.unlink(tmp_name)

    def load(self) -> None:
        if self.storage_path is None or not self.storage_path.exists():
            return
        with self._lock:
            payload = json.loads(self.storage_path.read_text(encoding="utf-8"))
            self._documents = {
                d["id"]: Document(**d) for d in payload.get("documents", [])
            }
            self._chunks = [Chunk(**c) for c in payload.get("chunks", [])]
            self._version += 1
            self._index_cache.clear()

    def _candidates(
        self, equipment_model: str | None, organization_id: str | None
    ) -> list[Chunk]:
        allowed = {
            doc_id
            for doc_id, doc in self._documents.items()
            if (organization_id is None or doc.organization_id == organization_id)
            and (equipment_model is None or doc.equipment_model == equipment_model)
        }
        return [chunk for chunk in self._chunks if chunk.document_id in allowed]

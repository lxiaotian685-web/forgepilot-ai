import pytest

from app.core import devices
from app.core.chunker import chunk_text
from app.core.demo import ensure_demo_documents, ingest_demo_docs
from app.core.store import KnowledgeBase


def test_resolve_equipment_model_maps_known_device():
    assert devices.resolve_equipment_model("AC-07") == ("compressor-002", "ok")
    assert devices.resolve_equipment_model("P-102") == ("pump-004", "ok")
    assert devices.resolve_equipment_model("CNC-04") == ("cnc-003", "ok")


def test_resolve_equipment_model_matching_explicit_model():
    assert devices.resolve_equipment_model("AC-07", "compressor-002") == (
        "compressor-002",
        "ok",
    )


def test_resolve_equipment_model_mismatched_explicit_model():
    assert devices.resolve_equipment_model("AC-07", "cnc-003") == (
        None,
        "model_mismatch",
    )


def test_resolve_equipment_model_unknown_device():
    assert devices.resolve_equipment_model("UNKNOWN-99") == (None, "device_not_found")


def test_resolve_equipment_model_no_doc_for_category(monkeypatch):
    monkeypatch.setitem(
        devices.DEVICE_CATALOG, "M-99", {"model": "M-99", "category": "motor"}
    )

    assert devices.resolve_equipment_model("M-99") == (None, "no_knowledge")


def test_device_catalog_maps_to_matching_doc_category():
    kb = KnowledgeBase()
    ingest_demo_docs(kb)
    kb_models = {d.equipment_model for d in kb.list_documents()}

    for device_id, info in devices.DEVICE_CATALOG.items():
        model, status = devices.resolve_equipment_model(device_id)
        assert status == "ok"
        assert model in kb_models
        assert devices.DOC_CATEGORY[model] == info["category"]


def test_ingest_demo_docs_imports_all():
    kb = KnowledgeBase()

    assert ingest_demo_docs(kb) == 3
    assert len(kb.list_documents()) == 3


def test_ensure_demo_documents_imports_when_empty(tmp_path):
    kb = KnowledgeBase(tmp_path / "kb.json")

    assert ensure_demo_documents(kb) == 3
    assert len(kb.list_documents()) == 3


def test_ensure_demo_documents_skips_when_populated(tmp_path):
    kb = KnowledgeBase(tmp_path / "kb.json")
    ingest_demo_docs(kb)

    assert ensure_demo_documents(kb) == 0
    assert len(kb.list_documents()) == 3


def test_chunk_text_rejects_invalid_overlap():
    with pytest.raises(ValueError):
        chunk_text("x" * 1_000, chunk_size=100, overlap=100)


def test_chunk_text_rejects_zero_chunk_size():
    with pytest.raises(ValueError):
        chunk_text("x" * 100, chunk_size=0)

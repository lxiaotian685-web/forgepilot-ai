from app.core.demo import ensure_demo_documents, ingest_demo_docs
from app.core.devices import resolve_equipment_model
from app.core.store import KnowledgeBase


def test_resolve_equipment_model_maps_known_device():
    assert resolve_equipment_model("AC-07") == "motor-001"
    assert resolve_equipment_model("P-102") == "compressor-002"
    assert resolve_equipment_model("CNC-01") == "cnc-003"


def test_resolve_equipment_model_prefers_explicit_model():
    assert resolve_equipment_model("AC-07", "compressor-002") == "compressor-002"


def test_resolve_equipment_model_unknown_device_is_none():
    assert resolve_equipment_model("UNKNOWN-99") is None


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

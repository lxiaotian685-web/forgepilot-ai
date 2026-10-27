import io

from fastapi.testclient import TestClient
from pypdf import PdfWriter
from pypdf.generic import DecodedStreamObject, DictionaryObject, NameObject

from app.main import app

client = TestClient(app)

TEXT_CONTENT = "概述\n\n---PAGE---\n\n排气温度过高排查：冷却器、油位。"


def _upload(
    filename: str,
    data: bytes,
    *,
    organization_id: str = "org-a",
    title: str = "上传空压机手册",
    equipment_model: str = "compressor-002",
    version: str = "1.0",
    source: str = "",
):
    return client.post(
        "/api/v1/documents/upload",
        headers={"X-Organization-Id": organization_id},
        data={
            "title": title,
            "equipment_model": equipment_model,
            "version": version,
            "source": source,
        },
        files={"file": (filename, data, "application/octet-stream")},
    )


def _make_pdf(text: str) -> bytes:
    writer = PdfWriter()
    page = writer.add_blank_page(width=300, height=144)
    font = DictionaryObject(
        {
            NameObject("/Type"): NameObject("/Font"),
            NameObject("/Subtype"): NameObject("/Type1"),
            NameObject("/BaseFont"): NameObject("/Helvetica"),
        }
    )
    font_ref = writer._add_object(font)
    page[NameObject("/Resources")] = DictionaryObject(
        {
            NameObject("/Font"): DictionaryObject(
                {NameObject("/F1"): font_ref}
            )
        }
    )
    stream = DecodedStreamObject()
    stream.set_data(
        f"BT /F1 12 Tf 72 100 Td ({text}) Tj ET".encode("latin-1")
    )
    page[NameObject("/Contents")] = writer._add_object(stream)
    buffer = io.BytesIO()
    writer.write(buffer)
    writer.close()
    return buffer.getvalue()


def _make_blank_pdf() -> bytes:
    writer = PdfWriter()
    writer.add_blank_page(width=300, height=144)
    buffer = io.BytesIO()
    writer.write(buffer)
    writer.close()
    return buffer.getvalue()


def test_upload_text_document_and_retrieve():
    response = _upload("manual.txt", TEXT_CONTENT.encode("utf-8"))

    assert response.status_code == 200
    body = response.json()
    assert body["title"] == "上传空压机手册"
    assert body["equipment_model"] == "compressor-002"
    assert body["version"] == "1.0"
    assert body["source"] == "manual.txt"
    assert body["page_count"] == 2
    assert body["chunk_count"] >= 2

    documents = client.get(
        "/api/v1/documents", headers={"X-Organization-Id": "org-a"}
    ).json()
    assert [document["title"] for document in documents] == ["上传空压机手册"]

    search = client.post(
        "/api/v1/search",
        headers={"X-Organization-Id": "org-a"},
        json={"query": "排气温度过高", "equipment_model": "compressor-002"},
    ).json()
    assert search["count"] >= 1
    assert search["results"][0]["title"] == "上传空压机手册"
    assert search["results"][0]["page"] == 2

    chat = client.post(
        "/api/v1/chat",
        headers={"X-Organization-Id": "org-a"},
        json={"device_id": "AC-07", "question": "排气温度过高怎么排查？"},
    ).json()
    assert chat["status"] == "ok"
    assert chat["sources"]
    source_ids = {source["id"] for source in chat["sources"]}
    facts = [item for item in chat["statements"] if item["type"] == "fact"]
    assert facts
    assert all(set(item["source_ids"]) <= source_ids for item in facts)


def test_upload_pdf_document_and_retrieve():
    pdf = _make_pdf(
        "Exhaust temperature too high. Check cooler and oil level."
    )

    response = _upload("manual.pdf", pdf, title="PDF 空压机手册")

    assert response.status_code == 200
    body = response.json()
    assert body["title"] == "PDF 空压机手册"
    assert body["source"] == "manual.pdf"
    assert body["page_count"] == 1
    assert body["chunk_count"] >= 1

    search = client.post(
        "/api/v1/search",
        headers={"X-Organization-Id": "org-a"},
        json={"query": "temperature", "equipment_model": "compressor-002"},
    ).json()
    assert search["count"] >= 1
    assert search["results"][0]["title"] == "PDF 空压机手册"
    assert search["results"][0]["page"] == 1


def test_upload_supports_gb18030_text():
    data = "排气温度过高排查：检查冷却器。".encode("gb18030")

    response = _upload("manual.txt", data, title="GB18030 手册")

    assert response.status_code == 200
    search = client.post(
        "/api/v1/search",
        headers={"X-Organization-Id": "org-a"},
        json={"query": "排气温度过高"},
    ).json()
    assert search["count"] >= 1
    assert search["results"][0]["title"] == "GB18030 手册"


def test_upload_uses_filename_when_title_and_source_blank():
    response = _upload("ac07.txt", TEXT_CONTENT.encode("utf-8"), title="", source="")

    assert response.status_code == 200
    body = response.json()
    assert body["title"] == "ac07"
    assert body["source"] == "ac07.txt"


def test_upload_sanitizes_path_like_filename():
    response = _upload("../../evil.txt", TEXT_CONTENT.encode("utf-8"), title="")

    assert response.status_code == 200
    body = response.json()
    assert body["title"] == "evil"
    assert body["source"] == "evil.txt"


def test_upload_rejects_unsupported_extension():
    response = _upload("manual.docx", b"content")

    assert response.status_code == 415


def test_upload_rejects_invalid_pdf_magic():
    response = _upload("manual.pdf", b"not a pdf")

    assert response.status_code == 415


def test_upload_rejects_corrupt_pdf():
    response = _upload("manual.pdf", b"%PDF-1.4 broken")

    assert response.status_code == 422


def test_upload_rejects_pdf_without_extractable_text():
    response = _upload("blank.pdf", _make_blank_pdf())

    assert response.status_code == 422


def test_upload_rejects_empty_file():
    response = _upload("empty.txt", b"")

    assert response.status_code == 422


def test_upload_rejects_blank_text_content():
    response = _upload("blank.txt", b"   \n")

    assert response.status_code == 422


def test_upload_rejects_binary_text_file():
    response = _upload("binary.txt", b"abc\x00def")

    assert response.status_code == 415


def test_upload_rejects_oversized_file(monkeypatch):
    monkeypatch.setenv("MAX_UPLOAD_BYTES", "10")

    response = _upload("big.txt", b"x" * 11)

    assert response.status_code == 413


def test_upload_can_be_disabled(monkeypatch):
    monkeypatch.setenv("C_ENABLE_INGEST", "false")

    response = _upload("manual.txt", TEXT_CONTENT.encode("utf-8"))

    assert response.status_code == 403


def test_upload_requires_equipment_model():
    response = client.post(
        "/api/v1/documents/upload",
        headers={"X-Organization-Id": "org-a"},
        data={"title": "缺少型号"},
        files={"file": ("manual.txt", TEXT_CONTENT.encode("utf-8"), "text/plain")},
    )

    assert response.status_code == 422


def test_upload_rejects_blank_equipment_model():
    response = _upload(
        "manual.txt", TEXT_CONTENT.encode("utf-8"), equipment_model="   "
    )

    assert response.status_code == 422


def test_upload_rejects_too_long_title():
    response = _upload(
        "manual.txt", TEXT_CONTENT.encode("utf-8"), title="x" * 201
    )

    assert response.status_code == 422


def test_upload_requires_org_when_auth_enabled(monkeypatch):
    monkeypatch.setenv("C_REQUIRE_AUTH", "true")

    response = client.post(
        "/api/v1/documents/upload",
        data={"equipment_model": "compressor-002"},
        files={"file": ("manual.txt", TEXT_CONTENT.encode("utf-8"), "text/plain")},
    )

    assert response.status_code == 401


def test_upload_persists_across_reload(tmp_path):
    from app.core.store import KnowledgeBase
    from app.deps import kb

    kb.storage_path = tmp_path / "kb.json"
    response = _upload("persist.txt", TEXT_CONTENT.encode("utf-8"))
    assert response.status_code == 200

    reloaded = KnowledgeBase(tmp_path / "kb.json")
    reloaded.load()

    documents = reloaded.list_documents(organization_id="org-a")
    assert [document.title for document in documents] == ["上传空压机手册"]

    results = reloaded.search(
        "排气温度过高",
        equipment_model="compressor-002",
        organization_id="org-a",
    )
    assert results
    assert results[0].title == "上传空压机手册"


def test_upload_is_org_scoped():
    upload = _upload("org-a.txt", TEXT_CONTENT.encode("utf-8"), organization_id="org-a")
    assert upload.status_code == 200

    documents = client.get(
        "/api/v1/documents", headers={"X-Organization-Id": "org-b"}
    ).json()
    assert documents == []

    search = client.post(
        "/api/v1/search",
        headers={"X-Organization-Id": "org-b"},
        json={"query": "排气温度过高"},
    ).json()
    assert search["count"] == 0

    document_id = upload.json()["document_id"]
    assert client.get(
        f"/api/v1/documents/{document_id}",
        headers={"X-Organization-Id": "org-b"},
    ).status_code == 404
    assert client.delete(
        f"/api/v1/documents/{document_id}",
        headers={"X-Organization-Id": "org-b"},
    ).status_code == 404
    assert client.get(
        f"/api/v1/documents/{document_id}",
        headers={"X-Organization-Id": "org-a"},
    ).status_code == 200

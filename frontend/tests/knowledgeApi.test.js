import assert from "node:assert/strict";
import test from "node:test";
import { listKnowledgeDocuments, uploadKnowledgeDocument } from "../src/services/knowledgeApi.js";

const session = { accessToken: "token", organization: { id: "org-1" }, user: { id: "user-1" } };

test("knowledge list uses organization scope and bearer token", async () => {
  const fetchImpl = async (url, options) => {
    assert.match(url, /documents\?limit=100&offset=0$/);
    assert.equal(options.headers.Authorization, "Bearer token");
    assert.equal(options.headers["X-Organization-Id"], "org-1");
    return { ok: true, json: async () => [{ id: "doc-1", title: "手册" }] };
  };
  assert.equal((await listKnowledgeDocuments(session, fetchImpl, "https://rag.example.com"))[0].id, "doc-1");
});

test("knowledge upload sends file and model as multipart data", async () => {
  const file = new Blob(["manual"], { type: "text/plain" });
  const fetchImpl = async (url, options) => {
    assert.match(url, /documents\/upload$/);
    assert.equal(options.method, "POST");
    assert.equal(options.body.get("equipment_model"), "AC-07");
    assert.equal(options.headers.Authorization, "Bearer token");
    return { ok: true, json: async () => ({ document_id: "doc-1", chunk_count: 1 }) };
  };
  const result = await uploadKnowledgeDocument(session, file, { title: "手册", equipmentModel: "AC-07", version: "1.0", source: "现场" }, fetchImpl, "https://rag.example.com");
  assert.equal(result.document_id, "doc-1");
});

import { test } from "node:test";
import assert from "node:assert/strict";
import { normalizeDiagnosis, requestDiagnosis, diagnosisStatuses } from "../src/services/diagnosis.js";

const payload = () => ({ device_id: "AC-07", answer: "需核验", is_mock: true, status: "ok", statements: [
  { type: "fact", text: "文档片段", source: "《演示手册》第2页" },
], sources: [{ document_id: "doc-1", title: "演示手册", page: 2, snippet: "原文", score: 1.5 }] });
const input = { deviceId: "AC-07", question: " 振动异常 " };
const config = { VITE_DATA_MODE: "api", VITE_API_BASE_URL: "https://api.example.test/" };

test("links a unique exact reference, keeps retrieval score unscaled", () => {
  const result = normalizeDiagnosis(payload(), "AC-07");
  assert.equal(result.statements[0].sourceKey, "source-0");
  assert.equal(result.sources[0].score, 1.5);
});
test("does not guess ambiguous or unknown references", () => {
  const value = payload(); value.sources.push({ ...value.sources[0], document_id: "other-version" });
  assert.equal(normalizeDiagnosis(value, "AC-07").statements[0].sourceKey, null);
  value.statements[0].source = "别的来源";
  assert.equal(normalizeDiagnosis(value, "AC-07").statements[0].sourceKey, null);
});
test("rejects wrong device and missing mock flag", () => {
  assert.throws(() => normalizeDiagnosis(payload(), "P-102"));
  assert.throws(() => normalizeDiagnosis({ ...payload(), is_mock: undefined }, "AC-07"));
});
test("rejects malformed evidence, statements and unknown status", () => {
  for (const value of [
    { ...payload(), sources: [{ ...payload().sources[0], page: null }] },
    { ...payload(), statements: [{ type: "diagnosis", text: "bad" }] },
    { ...payload(), status: "unexpected" },
  ]) assert.throws(() => normalizeDiagnosis(value, "AC-07"));
});
for (const status of Object.keys(diagnosisStatuses)) {
  test(`preserves server status ${status}`, () => assert.equal(normalizeDiagnosis({ ...payload(), status }, "AC-07").status, status));
}
test("mock is an explicit fixed sample, never calls network", async () => {
  const result = await requestDiagnosis(input, {}, () => { throw new Error("unexpected network"); });
  assert.equal(result.transport, "local-demo"); assert.equal(result.is_mock, true);
  assert.match(result.answer, /未分析/);
  const other = await requestDiagnosis({ ...input, deviceId: "P-102" }, {});
  assert.equal(other.status, "no_knowledge"); assert.deepEqual(other.sources, []);
});
test("POSTs current C contract without overriding equipment model", async () => {
  const result = await requestDiagnosis(input, { ...config, VITE_DIAGNOSIS_API_BASE_URL: "https://rag.example.test/", VITE_API_USER_ID: "demo" }, async (url, options) => {
    assert.equal(url, "https://rag.example.test/api/v1/chat");
    assert.equal(options.method, "POST"); assert.equal(options.headers["X-User-Id"], "demo");
    assert.deepEqual(JSON.parse(options.body), { device_id: "AC-07", question: "振动异常" });
    return { ok: true, json: async () => ({ ...payload(), is_mock: false }) };
  });
  assert.equal(result.transport, "api"); assert.equal(result.is_mock, false);
});
test("missing config or blank input fail explicitly", async () => {
  await assert.rejects(requestDiagnosis(input, { VITE_DATA_MODE: "api" }), /尚未配置/);
  await assert.rejects(requestDiagnosis({ ...input, question: "  " }, {}), /填写/);
});
test("HTTP, network and JSON errors do not become fake success", async () => {
  await assert.rejects(requestDiagnosis(input, config, async () => ({ ok: false, status: 503 })), /503/);
  await assert.rejects(requestDiagnosis(input, config, async () => { throw new Error("offline"); }), /offline/);
  await assert.rejects(requestDiagnosis(input, config, async () => ({ ok: true, json: async () => { throw new Error("bad json"); } })), /bad json/);
});
test("propagates cancellation", async () => {
  const controller = new AbortController();
  const promise = requestDiagnosis({ ...input, signal: controller.signal }, config, async (_, options) => new Promise((resolve, reject) => {
    options.signal.addEventListener("abort", () => reject(new DOMException("cancelled", "AbortError")));
  }));
  controller.abort();
  await assert.rejects(promise, { name: "AbortError" });
});

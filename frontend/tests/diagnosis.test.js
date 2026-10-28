import { test } from "node:test";
import assert from "node:assert/strict";
import { createDemoDiagnosisOrder, normalizeDiagnosis, requestDiagnosis, diagnosisStatuses, summarizeDiagnosis } from "../src/services/diagnosis.js";
import { devices } from "../src/data.js";

const payload = () => ({ device_id: "AC-07", answer: "需核验", is_mock: true, status: "ok", statements: [
  { type: "fact", text: "文档片段", source: "《演示手册》第2页", source_ids: ["doc-1@v1#p2c0"] },
], sources: [{ id: "doc-1@v1#p2c0", document_id: "doc-1", version: "v1", title: "演示手册", page: 2, chunk_index: 0, snippet: "原文", score: 1.5 }], conflicts: [], verification_suggestions: [] });
const input = { deviceId: "AC-07", question: " 振动异常 " };
const config = { VITE_DATA_MODE: "api", VITE_API_BASE_URL: "https://api.example.test/", VITE_DIAGNOSIS_API_BASE_URL: "https://rag.example.test/" };
const session = { accessToken: "current-user-token", organization: { id: "org-1" }, user: { id: "user-1" } };
const apiInput = { ...input, session };

test("links a unique exact reference, keeps retrieval score unscaled", () => {
  const result = normalizeDiagnosis(payload(), "AC-07");
  assert.equal(result.statements[0].sourceKey, "doc-1@v1#p2c0");
  assert.deepEqual(result.statements[0].sourceKeys, ["doc-1@v1#p2c0"]);
  assert.equal(result.sources[0].score, 1.5);
});
test("summarizes only real statement and source counts", () => {
  const value = payload();
  value.statements.push({ type: "inference", text: "可能原因" }, { type: "pending", text: "待现场核对" });
  assert.deepEqual(summarizeDiagnosis(value), { fact: 1, inference: 1, pending: 1, sources: 1 });
  assert.deepEqual(summarizeDiagnosis(null), { fact: 0, inference: 0, pending: 0, sources: 0 });
});
test("uses stable source IDs and rejects unknown or duplicate IDs", () => {
  assert.equal(normalizeDiagnosis(payload(), "AC-07").statements[0].sourceKey, "doc-1@v1#p2c0");
  const unknown = payload(); unknown.statements[0].source_ids = ["missing"];
  assert.throws(() => normalizeDiagnosis(unknown, "AC-07"), /诊断陈述格式错误/);
  const duplicate = payload(); duplicate.sources.push({ ...duplicate.sources[0] });
  assert.throws(() => normalizeDiagnosis(duplicate, "AC-07"), /证据字段不完整/);
});
test("rejects wrong device and missing mock flag", () => {
  assert.throws(() => normalizeDiagnosis(payload(), "P-102"));
  assert.throws(() => normalizeDiagnosis({ ...payload(), is_mock: undefined }, "AC-07"));
});
test("rejects malformed evidence, statements and unknown status", () => {
  for (const value of [
    { ...payload(), sources: [{ ...payload().sources[0], chunk_index: -1 }] },
    { ...payload(), statements: [{ type: "diagnosis", text: "bad" }] },
    { ...payload(), status: "unexpected" },
  ]) assert.throws(() => normalizeDiagnosis(value, "AC-07"));
});
test("accepts an explicitly unknown page without inventing a page number", () => {
  const value = payload(); value.sources[0].page = null;
  const result = normalizeDiagnosis(value, "AC-07");
  assert.match(result.sources[0].reference, /页码未知/);
});
test("validates conflicts, verification suggestions and grounded success", () => {
  const value = payload();
  value.conflicts = [{ field: "额定压力", sources: [{ origin: "device_record", value: "0.8 MPa", ref: null }] }];
  value.verification_suggestions = [{ missing_evidence: "校准记录", to_verify: "排除传感器漂移" }];
  const result = normalizeDiagnosis(value, "AC-07");
  assert.equal(result.conflicts[0].field, "额定压力");
  assert.equal(result.verification_suggestions[0].missing_evidence, "校准记录");
  const ungrounded = payload(); ungrounded.statements[0].source_ids = [];
  assert.throws(() => normalizeDiagnosis(ungrounded, "AC-07"), /缺少可核实/);
});
for (const status of Object.keys(diagnosisStatuses)) {
  test(`preserves server status ${status}`, () => assert.equal(normalizeDiagnosis({ ...payload(), status }, "AC-07").status, status));
}
test("mock uses each device's demo readings and excerpts without network", async () => {
  const result = await requestDiagnosis(input, {}, () => { throw new Error("unexpected network"); });
  assert.equal(result.transport, "local-demo"); assert.equal(result.is_mock, true);
  assert.match(result.answer, /振动异常/);
  for (const device of devices) {
    const other = await requestDiagnosis({ ...input, deviceId: device.id }, {});
    assert.equal(other.status, "ok", `${device.id} has no demo evidence`);
    assert.ok(other.sources.length > 0);
    assert.ok(other.statements.some((statement) => statement.type === "pending"));
  }
});
test("demo diagnosis order keeps risk, owner and device for the shared work order list", () => {
  const order = createDemoDiagnosisOrder({ deviceId: "CNC-04", riskLevel: "high", owner: "赵工", diagnosisId: "DEMO-DIAG-1", answer: "复核主轴。", now: new Date(2026, 9, 28, 10, 0) });
  assert.equal(order.status, "待处理");
  assert.equal(order.priority, "P1 紧急");
  assert.equal(order.deviceId, "CNC-04");
  assert.equal(order.owner, "赵工");
  assert.equal(order.dueDate, "2026-10-29");
  assert.match(order.description, /DEMO-DIAG-1/);
  assert.throws(() => createDemoDiagnosisOrder({ deviceId: "CNC-04", riskLevel: "high", owner: "", diagnosisId: "D-1" }), /负责人/);
});
test("POSTs current C contract without overriding equipment model", async () => {
  const result = await requestDiagnosis(apiInput, { ...config, VITE_DIAGNOSIS_API_BASE_URL: "https://rag.example.test/", VITE_API_USER_ID: "demo" }, async (url, options) => {
    assert.equal(url, "https://rag.example.test/api/v1/chat");
    assert.equal(options.method, "POST"); assert.equal(options.headers["X-User-Id"], "user-1");
    assert.equal(options.headers["X-Organization-Id"], "org-1");
    assert.deepEqual(JSON.parse(options.body), { device_id: "AC-07", question: "振动异常" });
    return { ok: true, json: async () => ({ ...payload(), is_mock: false }) };
  });
  assert.equal(result.transport, "api"); assert.equal(result.is_mock, false);
});

test("forwards the current session bearer token to C", async () => {
  await requestDiagnosis({ deviceId: "AC-07", question: "x", session }, {
    VITE_DATA_MODE: "api", VITE_DIAGNOSIS_API_BASE_URL: "https://rag.test", VITE_API_TOKEN: "demo-token",
  }, async (_url, options) => {
    assert.equal(options.headers.Authorization, "Bearer current-user-token");
    return { ok: true, json: async () => payload() };
  });
});
test("missing config or blank input fail explicitly", async () => {
  await assert.rejects(requestDiagnosis(input, { VITE_DATA_MODE: "api" }), /尚未配置/);
  await assert.rejects(requestDiagnosis(input, config), /登录会话/);
  await assert.rejects(requestDiagnosis({ ...input, question: "  " }, {}), /填写/);
});
test("HTTP, network and JSON errors do not become fake success", async () => {
  await assert.rejects(requestDiagnosis(apiInput, config, async () => ({ ok: false, status: 503 })), /503/);
  await assert.rejects(requestDiagnosis(apiInput, config, async () => { throw new Error("offline"); }), /offline/);
  await assert.rejects(requestDiagnosis(apiInput, config, async () => ({ ok: true, json: async () => { throw new Error("bad json"); } })), /bad json/);
});
test("propagates cancellation", async () => {
  const controller = new AbortController();
  const promise = requestDiagnosis({ ...apiInput, signal: controller.signal }, config, async (_, options) => new Promise((resolve, reject) => {
    options.signal.addEventListener("abort", () => reject(new DOMException("cancelled", "AbortError")));
  }));
  controller.abort();
  await assert.rejects(promise, { name: "AbortError" });
});

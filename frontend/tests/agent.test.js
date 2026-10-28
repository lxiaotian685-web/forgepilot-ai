import { test } from "node:test";
import assert from "node:assert/strict";
import { requestAgent } from "../src/services/agent.js";

const input = { deviceId: "AC-07", question: "驱动端振动异常", orders: [
  { id: "WO-1", deviceId: "AC-07", title: "更换轴承", status: "已完成" },
  { id: "WO-2", deviceId: "P-102", title: "检查密封", status: "处理中" },
] };

test("demo Agent uses only local data and same-device history", async () => {
  const result = await requestAgent(input, { VITE_DATA_MODE: "mock" }, () => { throw new Error("unexpected network"); });
  assert.equal(result.status, "ready_for_review");
  assert.equal(result.history.length, 1);
  assert.equal(result.history[0].id, "WO-1");
  assert.deepEqual(result.tools.map((step) => step.name), ["device_lookup", "work_order_history", "evidence_diagnosis"]);
  assert.equal(result.can_create_work_order, false);
  assert.equal(result.diagnosis.transport, "local-demo");
});

test("API Agent forwards current bearer identity and validates response", async () => {
  const session = { accessToken: "current-token", organization: { id: "org-1" }, user: { id: "user-1" } };
  const payload = { device_id: "AC-07", status: "unavailable", diagnosis: null, history: [], tools: [], can_create_work_order: false, audit_status: "unavailable", audit_id: null };
  const result = await requestAgent({ ...input, session }, { VITE_DATA_MODE: "api", VITE_DIAGNOSIS_API_BASE_URL: "https://rag.example.test/" }, async (url, options) => {
    assert.equal(url, "https://rag.example.test/api/v1/agent/assist");
    assert.equal(options.headers.Authorization, "Bearer current-token");
    assert.equal(options.headers["X-Organization-Id"], "org-1");
    assert.deepEqual(JSON.parse(options.body), { device_id: "AC-07", question: "驱动端振动异常" });
    return { ok: true, json: async () => payload };
  });
  assert.equal(result.status, "unavailable");
  await assert.rejects(requestAgent({ ...input, session }, { VITE_DATA_MODE: "api", VITE_DIAGNOSIS_API_BASE_URL: "https://rag.example.test" }, async () => ({ ok: true, json: async () => ({ ...payload, device_id: "P-102" }) })), /契约/);
});

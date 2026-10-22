import { test } from "node:test";
import assert from "node:assert/strict";
import { confirmDiagnosis, diagnosisEvidenceSnapshot, loadDiagnosisAudit, saveDiagnosis } from "../src/services/workflow.js";

const config = {
  VITE_API_BASE_URL: "https://fallback.example.test",
  VITE_BUSINESS_API_BASE_URL: "https://business.example.test/",
  VITE_API_ORGANIZATION_ID: "demo-org",
  VITE_API_USER_ID: "tech@example.com",
};

function diagnosis() {
  return {
    transport: "api",
    is_mock: false,
    status: "ok",
    answer: "建议停机检查。",
    summary: "疑似驱动端异常。",
    statements: [{ type: "fact", text: "振动升高", source_ids: ["doc@v1#p2c0"], sourceKey: "doc@v1#p2c0" }],
    sources: [{ id: "doc@v1#p2c0", document_id: "doc", version: "v1", page: 2, chunk_index: 0, title: "手册", snippet: "原文", score: 1.2, key: "doc@v1#p2c0", reference: "《手册》第2页", order: 0 }],
    conflicts: [],
    verification_suggestions: [{ missing_evidence: "振动频谱", to_verify: "轴承状态" }],
  };
}

test("builds an auditable evidence snapshot without UI-only fields", () => {
  const snapshot = diagnosisEvidenceSnapshot(diagnosis());
  assert.equal(snapshot.sources[0].id, "doc@v1#p2c0");
  assert.equal(Object.hasOwn(snapshot.sources[0], "reference"), false);
  assert.equal(Object.hasOwn(snapshot.statements[0], "sourceKey"), false);
  assert.equal(snapshot.verificationSuggestions[0].to_verify, "轴承状态");
});

test("saves only verified real API diagnosis using the B contract", async () => {
  const saved = await saveDiagnosis({
    deviceId: "AC-07", question: " 振动异常 ", result: diagnosis(), riskLevel: "high",
  }, config, async (url, options) => {
    assert.equal(url, "https://business.example.test/api/v1/diagnoses");
    assert.equal(options.headers["X-Organization-Id"], "demo-org");
    assert.equal(options.headers["X-User-Id"], "tech@example.com");
    const body = JSON.parse(options.body);
    assert.deepEqual({ deviceId: body.deviceId, question: body.question, riskLevel: body.riskLevel, confidence: body.confidence },
      { deviceId: "AC-07", question: "振动异常", riskLevel: "high", confidence: null });
    assert.equal(body.evidence.sources[0].id, "doc@v1#p2c0");
    return { ok: true, json: async () => ({ id: "DIAG-001", status: "draft" }) };
  });
  assert.equal(saved.id, "DIAG-001");
});

test("refuses demo, degraded and unclassified diagnosis saves", async () => {
  await assert.rejects(saveDiagnosis({ deviceId: "AC-07", question: "x", result: { ...diagnosis(), transport: "local-demo" }, riskLevel: "low" }, config), /真实接口/);
  await assert.rejects(saveDiagnosis({ deviceId: "AC-07", question: "x", result: { ...diagnosis(), status: "no_answer" }, riskLevel: "low" }, config), /真实接口/);
  await assert.rejects(saveDiagnosis({ deviceId: "AC-07", question: "x", result: diagnosis(), riskLevel: "" }, config), /风险等级/);
});

test("confirms idempotently through B and requires both returned records", async () => {
  const value = await confirmDiagnosis({ diagnosisId: "DIAG-001", priority: "P1 紧急", note: "已现场确认" }, config, async (url, options) => {
    assert.equal(url, "https://business.example.test/api/v1/diagnoses/DIAG-001/confirm");
    assert.deepEqual(JSON.parse(options.body), { priority: "P1 紧急", note: "已现场确认" });
    return { ok: true, json: async () => ({ diagnosis: { id: "DIAG-001" }, workOrder: { id: "WO-001" } }) };
  });
  assert.equal(value.workOrder.id, "WO-001");
  await assert.rejects(confirmDiagnosis({ diagnosisId: "" }, config), /先保存/);
});

test("loads diagnosis audit with encoded query and validates pagination", async () => {
  const items = await loadDiagnosisAudit({ diagnosisEntityId: "4d60b6e7-2f72-4e14-b718-92ac2c7f35b5" }, config, async (url, options) => {
    assert.match(url, /entityType=diagnosis/);
    assert.match(url, /entityId=4d60b6e7/);
    assert.equal(options.method, "GET");
    return { ok: true, json: async () => ({ items: [{ action: "diagnosis.confirm" }] }) };
  });
  assert.equal(items[0].action, "diagnosis.confirm");
});

test("surfaces the B error message and never treats malformed success as confirmation", async () => {
  await assert.rejects(confirmDiagnosis({ diagnosisId: "DIAG-001" }, config, async () => ({
    ok: false, status: 409, json: async () => ({ error: { message: "诊断已拒绝" } }),
  })), /诊断已拒绝/);
  await assert.rejects(confirmDiagnosis({ diagnosisId: "DIAG-001" }, config, async () => ({
    ok: true, json: async () => ({ diagnosis: { id: "DIAG-001" } }),
  })), /缺少诊断或工单编号/);
});

function apiBase(config) {
  return (config.VITE_BUSINESS_API_BASE_URL || config.VITE_API_BASE_URL || "").replace(/\/$/, "");
}

function authHeaders(config, session) {
  const headers = { Accept: "application/json", "Content-Type": "application/json" };
  if (session?.accessToken) headers.Authorization = `Bearer ${session.accessToken}`;
  else if (config.VITE_DATA_MODE === "api") throw new Error("业务操作需要当前登录会话");
  else {
    if (config.VITE_API_ORGANIZATION_ID) headers["X-Organization-Id"] = config.VITE_API_ORGANIZATION_ID;
    if (config.VITE_API_USER_ID) headers["X-User-Id"] = config.VITE_API_USER_ID;
  }
  return headers;
}

async function requestBusiness(path, options, config, fetcher, session) {
  const base = apiBase(config);
  if (!base) throw new Error("尚未配置业务服务地址，请设置 VITE_BUSINESS_API_BASE_URL。");
  const response = await fetcher(`${base}${path}`, {
    ...options,
    headers: { ...authHeaders(config, session), ...options.headers },
  });
  if (!response.ok) {
    let message = `业务请求失败（HTTP ${response.status}）。`;
    try {
      const payload = await response.json();
      if (payload?.error?.message) message = payload.error.message;
    } catch {
      // Keep the status-based message when the server does not return JSON.
    }
    throw new Error(message);
  }
  return response.json();
}

export function diagnosisEvidenceSnapshot(result) {
  return {
    status: result.status,
    summary: result.summary,
    statements: result.statements.map(({ sourceKey, sourceKeys, ...statement }) => statement),
    sources: result.sources.map(({ key, reference, order, ...source }) => source),
    conflicts: result.conflicts,
    verificationSuggestions: result.verification_suggestions,
  };
}

export async function saveDiagnosis(
  { deviceId, question, result, riskLevel, alertId = null, session },
  config = import.meta.env || {},
  fetcher = globalThis.fetch,
) {
  if (!result || result.transport !== "api" || result.is_mock || result.status !== "ok") {
    throw new Error("只有真实接口返回且证据校验通过的诊断才能保存。");
  }
  if (!["low", "medium", "high"].includes(riskLevel)) {
    throw new Error("保存前必须由人工选择风险等级。");
  }
  const payload = {
    deviceId,
    question: question.trim(),
    conclusion: result.answer,
    riskLevel,
    confidence: null,
    modelSource: "c-rag-api",
    evidence: diagnosisEvidenceSnapshot(result),
    alertId,
  };
  return requestBusiness("/api/v1/diagnoses", {
    method: "POST",
    body: JSON.stringify(payload),
  }, config, fetcher, session);
}

export async function confirmDiagnosis(
  { diagnosisId, title, priority, note, session },
  config = import.meta.env || {},
  fetcher = globalThis.fetch,
) {
  if (!diagnosisId) throw new Error("请先保存诊断，再进行人工确认。");
  const payload = {};
  if (title?.trim()) payload.title = title.trim();
  if (priority) payload.priority = priority;
  if (note?.trim()) payload.note = note.trim();
  const result = await requestBusiness(`/api/v1/diagnoses/${encodeURIComponent(diagnosisId)}/confirm`, {
    method: "POST",
    body: JSON.stringify(payload),
  }, config, fetcher, session);
  if (!result?.diagnosis?.id || !result?.workOrder?.id) {
    throw new Error("确认响应缺少诊断或工单编号，未将其视为成功。");
  }
  return result;
}

export async function loadDiagnosisAudit(
  { diagnosisEntityId, diagnosisId, session },
  config = import.meta.env || {},
  fetcher = globalThis.fetch,
) {
  let entityId = diagnosisEntityId;
  if (!entityId && diagnosisId) {
    const discoveryQuery = new URLSearchParams({
      entityType: "diagnosis", action: "diagnosis.create", pageSize: "100",
    });
    const discovery = await requestBusiness(`/api/v1/audit-events?${discoveryQuery}`, { method: "GET" }, config, fetcher, session);
    const created = discovery?.items?.find((item) => item?.after?.code === diagnosisId);
    entityId = created?.entityId;
  }
  if (!entityId) throw new Error("未找到该诊断的审计实体编号。");
  const query = new URLSearchParams({ entityType: "diagnosis", entityId });
  const payload = await requestBusiness(`/api/v1/audit-events?${query}`, { method: "GET" }, config, fetcher, session);
  if (!payload || !Array.isArray(payload.items)) {
    throw new Error("审计响应缺少 items。");
  }
  return payload.items;
}

import { deviceProfiles, evidence } from "../data.js";

// Current C contract: POST /api/v1/chat. No implicit mock fallback for failures.
export const diagnosisStatuses = {
  ok: "检索完成，需人工复核",
  device_not_found: "未找到设备档案",
  no_knowledge: "暂无适用文档",
  model_mismatch: "设备型号不一致，已拒绝检索",
  no_answer: "未找到足够证据",
  model_unavailable: "模型不可用，仅供人工阅读证据",
  device_unauthorized: "无权读取该设备",
  device_unavailable: "设备服务暂不可用",
  device_mismatch: "设备身份不一致，已拒绝诊断",
};

export function summarizeDiagnosis(result) {
  const summary = { fact: 0, inference: 0, pending: 0, sources: 0 };
  if (!result) return summary;
  for (const statement of result.statements || []) {
    if (Object.hasOwn(summary, statement.type)) summary[statement.type] += 1;
  }
  summary.sources = Array.isArray(result.sources) ? result.sources.length : 0;
  return summary;
}

export function normalizeDiagnosis(payload, deviceId) {
  if (!payload || payload.device_id !== deviceId ||
      typeof payload.answer !== "string" || typeof payload.is_mock !== "boolean" ||
      !Object.hasOwn(diagnosisStatuses, payload.status) ||
      !Array.isArray(payload.statements) || !Array.isArray(payload.sources)) {
    throw new Error("诊断响应与接口契约不一致，请联系服务端检查。");
  }
  const sourceIds = new Set();
  const sources = payload.sources.map((source, index) => {
    if (!source || typeof source.id !== "string" || !source.id || sourceIds.has(source.id) ||
        typeof source.document_id !== "string" || !source.document_id ||
        typeof source.version !== "string" || !source.version ||
        typeof source.title !== "string" || typeof source.snippet !== "string" ||
        (source.page !== null && (!Number.isInteger(source.page) || source.page < 1)) ||
        !Number.isInteger(source.chunk_index) || source.chunk_index < 0 ||
        typeof source.score !== "number" || !Number.isFinite(source.score)) {
      throw new Error("证据字段不完整，无法展示可靠引用。");
    }
    sourceIds.add(source.id);
    const location = source.page === null ? "页码未知" : `第${source.page}页`;
    return { ...source, key: source.id, reference: `《${source.title}》${location}`, order: index };
  });
  const statements = payload.statements.map((statement) => {
    if (!statement || !["fact", "inference", "pending"].includes(statement.type) ||
        typeof statement.text !== "string" ||
        (statement.source != null && typeof statement.source !== "string") ||
        !Array.isArray(statement.source_ids) ||
        statement.source_ids.some((id) => typeof id !== "string" || !sourceIds.has(id))) {
      throw new Error("诊断陈述格式错误，请联系服务端检查。");
    }
    return {
      ...statement,
      sourceKeys: [...statement.source_ids],
      sourceKey: statement.source_ids[0] || null,
    };
  });
  const conflicts = payload.conflicts ?? [];
  const verificationSuggestions = payload.verification_suggestions ?? [];
  if (!Array.isArray(conflicts) || conflicts.some((conflict) =>
    !conflict || typeof conflict.field !== "string" || !Array.isArray(conflict.sources) ||
    conflict.sources.some((source) => !source || typeof source.origin !== "string" ||
      typeof source.value !== "string" || (source.ref != null && typeof source.ref !== "string")))) {
    throw new Error("冲突字段格式错误，请联系服务端检查。");
  }
  if (!Array.isArray(verificationSuggestions) || verificationSuggestions.some((suggestion) =>
    !suggestion || typeof suggestion.missing_evidence !== "string" ||
    typeof suggestion.to_verify !== "string")) {
    throw new Error("补采建议格式错误，请联系服务端检查。");
  }
  if (payload.status === "ok" && !statements.some((statement) =>
    statement.type === "fact" && statement.source_ids.length > 0)) {
    throw new Error("成功诊断缺少可核实的事实引用，已拒绝展示为成功结果。");
  }
  return {
    ...payload,
    summary: typeof payload.summary === "string" ? payload.summary : payload.answer,
    sources,
    statements,
    conflicts,
    verification_suggestions: verificationSuggestions,
  };
}

export function demoEvidenceSources(deviceId) {
  return evidence.filter((item) => item.device === deviceId && item.preview).map((item, index) => ({
    id: `demo-${deviceId}-${index}@${item.version}#p1c0`,
    document_id: `demo-${deviceId}-${index}`,
    version: item.version,
    title: item.name,
    page: 1,
    chunk_index: 0,
    snippet: item.preview,
    score: 0,
  }));
}

export function buildDemoMeasurementQuestion(deviceId) {
  const metrics = deviceProfiles[deviceId]?.metrics;
  if (!metrics?.length) throw new Error("该设备没有演示测点，无法生成提问");
  return `${deviceId} 演示测点：${metrics.map((item) => `${item.label} ${item.value}${item.unit}（${item.limit}）`).join("；")}。请根据这些虚构示例数据列出需要现场复核的项目。`;
}

export function createDemoDiagnosisOrder({ deviceId, riskLevel, owner, diagnosisId, answer, now = new Date() }) {
  if (!deviceProfiles[deviceId]) throw new Error("请选择有效的演示设备。");
  if (!owner?.trim()) throw new Error("请选择演示工单负责人。");
  const priority = { high: "P1 紧急", medium: "P2 高", low: "P3 中" }[riskLevel];
  if (!priority || !diagnosisId) throw new Error("请先保存人工分级的演示诊断。");
  const tomorrow = new Date(now);
  tomorrow.setDate(tomorrow.getDate() + 1);
  const dateText = (date) => `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, "0")}-${String(date.getDate()).padStart(2, "0")}`;
  return {
    id: `DEMO-WO-${now.getTime()}`, title: `${deviceId} 诊断复核与现场检查`, deviceId,
    owner: owner.trim(), priority, status: "待处理", startDate: dateText(now), dueDate: dateText(tomorrow),
    description: `来源演示诊断 ${diagnosisId}。${answer}`, checklist: [false, false, false],
    updated: "刚刚", draft: false,
  };
}

function demoDiagnosis(deviceId, question) {
  const profile = deviceProfiles[deviceId];
  const sources = demoEvidenceSources(deviceId);
  const watch = profile?.metrics?.filter((metric) => ["danger", "warning"].includes(metric.tone)) || [];
  const focus = watch[0] || profile?.metrics?.[0];
  const finding = focus ? `${focus.label}演示值 ${focus.value} ${focus.unit}（${focus.limit}）` : "暂无演示测点";
  const hasEvidence = Boolean(profile && sources.length);
  return normalizeDiagnosis({
    device_id: deviceId,
    status: hasEvidence ? "ok" : "no_knowledge",
    is_mock: true,
    answer: hasEvidence
      ? `演示规则根据 ${deviceId} 的虚构测点和资料生成提示：${finding}。你填写的现象是“${question.trim().slice(0, 100)}”。请先复测并核对工况，再由人员判断风险等级；此结果未调用模型，也未访问真实 RAG 服务。`
      : "该设备暂无可展示的演示测点或资料；请检查设备档案。",
    statements: hasEvidence ? [
      { type: "fact", text: sources[0].snippet, source: `《${sources[0].title}》第1页`, source_ids: [sources[0].id] },
      { type: "inference", text: watch.length ? `演示规则提示关注：${finding}。这不是故障结论。` : `演示测点未显示越限；仍需根据现场现象复核 ${focus?.label || "相关指标"}。`, source: null, source_ids: [] },
      { type: "pending", text: "请补充采样时间、测点与单位、当前工况及现场复测记录。", source: null, source_ids: [] },
    ] : [],
    sources,
    conflicts: [],
    verification_suggestions: hasEvidence ? [
      { missing_evidence: "现场复测", to_verify: `${focus?.label || "关键指标"}是否持续偏离` },
      { missing_evidence: "点检记录", to_verify: "核对最近一次维护及传感器校准时间" },
    ] : [],
  }, deviceId);
}

export async function requestDiagnosis({ deviceId, question, signal, session }, config = import.meta.env || {}, fetcher = globalThis.fetch) {
  if (!deviceId || !question.trim()) throw new Error("请选择设备并填写现场现象。");
  if (signal?.aborted) throw new DOMException("请求已取消", "AbortError");
  if ((config.VITE_DATA_MODE || "mock") === "mock") {
    return { ...demoDiagnosis(deviceId, question), transport: "local-demo" };
  }
  const base = (config.VITE_DIAGNOSIS_API_BASE_URL || "").replace(/\/$/, "");
  if (!base) throw new Error("尚未配置诊断服务地址，请设置 VITE_DIAGNOSIS_API_BASE_URL。");
  if (!session?.accessToken || !session?.organization?.id || !session?.user?.id) throw new Error("诊断服务需要当前登录会话");
  const headers = { Accept: "application/json", "Content-Type": "application/json" };
  headers.Authorization = `Bearer ${session.accessToken}`;
  headers["X-Organization-Id"] = session.organization.id;
  headers["X-User-Id"] = session.user.id;
  const controller = new AbortController();
  const cancel = () => controller.abort();
  signal?.addEventListener("abort", cancel, { once: true });
  const timer = setTimeout(cancel, 30000);
  try {
    const response = await fetcher(`${base}/api/v1/chat`, {
      method: "POST", headers, signal: controller.signal,
      body: JSON.stringify({ device_id: deviceId, question: question.trim() }),
    });
    if (!response.ok) throw new Error(`诊断请求失败（HTTP ${response.status}），未生成新结论。`);
    return { ...normalizeDiagnosis(await response.json(), deviceId), transport: "api" };
  } catch (error) {
    if (signal?.aborted) throw new DOMException("请求已取消", "AbortError");
    if (controller.signal.aborted) throw new Error("诊断请求超过 30 秒，请稍后重试。");
    throw error;
  } finally {
    clearTimeout(timer);
    signal?.removeEventListener("abort", cancel);
  }
}

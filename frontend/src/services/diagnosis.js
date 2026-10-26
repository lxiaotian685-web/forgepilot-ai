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

function demoDiagnosis(deviceId) {
  return normalizeDiagnosis({
    device_id: deviceId,
    status: deviceId === "AC-07" ? "ok" : "no_knowledge",
    is_mock: true,
    answer: deviceId === "AC-07"
      ? "这是固定的界面演示样例，未分析你输入的现象，也未调用模型。示例展示如何核对文档和记录待验证项，不构成设备故障判断。"
      : "本地样例只覆盖 AC-07；该设备没有演示证据，请配置诊断服务后重试。",
    statements: deviceId === "AC-07" ? [
      { type: "fact", text: "示例文档说明：异常振动应结合工况及维护记录复核。", source: "《空压机演示检查说明》第1页", source_ids: ["local-demo@v1.0#p1c0"] },
      { type: "pending", text: "待人工补充振动采样位置、单位、采样时间与工况，不能仅凭异响确定故障。", source: null, source_ids: [] },
    ] : [],
    sources: deviceId === "AC-07" ? [{ id: "local-demo@v1.0#p1c0", document_id: "local-demo", version: "1.0", title: "空压机演示检查说明", page: 1, chunk_index: 0, snippet: "虚构界面样例，非企业手册。异常振动应结合工况及维护记录复核。", score: 0 }] : [],
    conflicts: [],
    verification_suggestions: [],
  }, deviceId);
}

export async function requestDiagnosis({ deviceId, question, signal, session }, config = import.meta.env || {}, fetcher = globalThis.fetch) {
  if (!deviceId || !question.trim()) throw new Error("请选择设备并填写现场现象。");
  if (signal?.aborted) throw new DOMException("请求已取消", "AbortError");
  if ((config.VITE_DATA_MODE || "mock") === "mock") {
    return { ...demoDiagnosis(deviceId), transport: "local-demo" };
  }
  const base = (config.VITE_DIAGNOSIS_API_BASE_URL || config.VITE_API_BASE_URL || "").replace(/\/$/, "");
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

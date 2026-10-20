// Current C contract: POST /api/v1/chat. No implicit mock fallback for failures.
export const diagnosisStatuses = {
  ok: "检索完成，需人工复核",
  device_not_found: "未找到设备档案",
  no_knowledge: "暂无适用文档",
  model_mismatch: "设备型号不一致，已拒绝检索",
  no_answer: "未找到足够证据",
  model_unavailable: "模型不可用，仅供人工阅读证据",
};

export function normalizeDiagnosis(payload, deviceId) {
  if (!payload || payload.device_id !== deviceId ||
      typeof payload.answer !== "string" || typeof payload.is_mock !== "boolean" ||
      !Object.hasOwn(diagnosisStatuses, payload.status) ||
      !Array.isArray(payload.statements) || !Array.isArray(payload.sources)) {
    throw new Error("诊断响应与接口契约不一致，请联系服务端检查。");
  }
  const sources = payload.sources.map((source, index) => {
    if (!source || typeof source.document_id !== "string" || !source.document_id ||
        typeof source.title !== "string" || typeof source.snippet !== "string" ||
        !Number.isInteger(source.page) || source.page < 1 ||
        typeof source.score !== "number" || !Number.isFinite(source.score)) {
      throw new Error("证据字段不完整，无法展示可靠引用。");
    }
    return { ...source, key: `source-${index}`, reference: `《${source.title}》第${source.page}页` };
  });
  const statements = payload.statements.map((statement) => {
    if (!statement || !["fact", "inference", "pending"].includes(statement.type) ||
        typeof statement.text !== "string" ||
        (statement.source != null && typeof statement.source !== "string")) {
      throw new Error("诊断陈述格式错误，请联系服务端检查。");
    }
    // The legacy contract only has display refs, not stable source IDs.
    // Never guess when a ref is absent or matches more than one result.
    const matches = sources.filter((source) => source.reference === statement.source);
    return { ...statement, sourceKey: matches.length === 1 ? matches[0].key : null };
  });
  return { ...payload, sources, statements };
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
      { type: "fact", text: "示例文档说明：异常振动应结合工况及维护记录复核。", source: "《空压机演示检查说明》第1页" },
      { type: "pending", text: "待人工补充振动采样位置、单位、采样时间与工况，不能仅凭异响确定故障。", source: null },
    ] : [],
    sources: deviceId === "AC-07" ? [{ document_id: "local-demo", title: "空压机演示检查说明", page: 1, snippet: "虚构界面样例，非企业手册。异常振动应结合工况及维护记录复核。", score: 0 }] : [],
  }, deviceId);
}

export async function requestDiagnosis({ deviceId, question, signal }, config = import.meta.env || {}, fetcher = globalThis.fetch) {
  if (!deviceId || !question.trim()) throw new Error("请选择设备并填写现场现象。");
  if (signal?.aborted) throw new DOMException("请求已取消", "AbortError");
  if ((config.VITE_DATA_MODE || "mock") === "mock") {
    return { ...demoDiagnosis(deviceId), transport: "local-demo" };
  }
  const base = (config.VITE_DIAGNOSIS_API_BASE_URL || config.VITE_API_BASE_URL || "").replace(/\/$/, "");
  if (!base) throw new Error("尚未配置诊断服务地址，请设置 VITE_DIAGNOSIS_API_BASE_URL。");
  const headers = { Accept: "application/json", "Content-Type": "application/json" };
  if (config.VITE_API_ORGANIZATION_ID) headers["X-Organization-Id"] = config.VITE_API_ORGANIZATION_ID;
  if (config.VITE_API_USER_ID) headers["X-User-Id"] = config.VITE_API_USER_ID;
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

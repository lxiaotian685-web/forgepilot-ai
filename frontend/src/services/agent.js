import { normalizeDiagnosis, requestDiagnosis } from "./diagnosis.js";

export async function requestAgent({ deviceId, question, session, orders = [], signal }, config = import.meta.env || {}, fetcher = globalThis.fetch) {
  if (!deviceId || !question?.trim()) throw new Error("请选择设备并填写现场现象。");
  if ((config.VITE_DATA_MODE || "mock") === "mock") {
    const diagnosis = await requestDiagnosis({ deviceId, question, session, signal }, config, fetcher);
    const history = orders.filter((order) => order.deviceId === deviceId).slice(0, 5).map((order) => ({
      id: order.id, device_id: deviceId, title: order.title, status: order.status,
    }));
    return {
      device_id: deviceId, status: diagnosis.status === "ok" ? "ready_for_review" : "needs_evidence",
      diagnosis, history, tools: [
        { name: "device_lookup", status: "ok", summary: `已读取演示设备 ${deviceId}`, count: 1 },
        { name: "work_order_history", status: "ok", summary: "已读取当前会话的演示工单", count: history.length },
        { name: "evidence_diagnosis", status: diagnosis.status === "ok" ? "ok" : "unavailable", summary: "已运行本地演示规则，未调用模型", count: diagnosis.sources.length },
      ],
      requires_human_confirmation: true, can_create_work_order: false, is_demo: true,
      audit_status: "unavailable", audit_id: null,
    };
  }
  const base = (config.VITE_DIAGNOSIS_API_BASE_URL || "").replace(/\/$/, "");
  if (!base) throw new Error("尚未配置 Agent 服务地址。");
  if (!session?.accessToken || !session?.organization?.id || !session?.user?.id) throw new Error("Agent 需要当前登录会话。");
  const response = await fetcher(`${base}/api/v1/agent/assist`, {
    method: "POST", signal,
    headers: {
      Accept: "application/json", "Content-Type": "application/json",
      Authorization: `Bearer ${session.accessToken}`,
      "X-Organization-Id": session.organization.id, "X-User-Id": session.user.id,
    },
    body: JSON.stringify({ device_id: deviceId, question: question.trim() }),
  });
  if (!response.ok) throw new Error(`Agent 请求失败（HTTP ${response.status}）。`);
  const payload = await response.json();
  if (payload?.device_id !== deviceId || !Array.isArray(payload.tools) || !Array.isArray(payload.history) || payload.can_create_work_order !== false || !["recorded", "unavailable"].includes(payload.audit_status)) {
    throw new Error("Agent 响应与接口契约不一致。");
  }
  return {
    ...payload,
    diagnosis: payload.diagnosis ? { ...normalizeDiagnosis(payload.diagnosis, deviceId), transport: "api" } : null,
  };
}

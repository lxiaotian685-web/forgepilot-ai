const runtimeEnv = import.meta.env || {};
const baseUrl = (runtimeEnv.VITE_API_BASE_URL || "").replace(/\/$/, "");

async function request(path, token, { method = "GET", body, fetchImpl = globalThis.fetch, apiBaseUrl = baseUrl } = {}) {
  if (!apiBaseUrl || !token) throw new Error("缺少后端地址或登录令牌");
  const response = await fetchImpl(`${apiBaseUrl}${path}`, {
    method,
    headers: { Accept: "application/json", Authorization: `Bearer ${token}`, ...(body ? { "Content-Type": "application/json" } : {}) },
    ...(body ? { body: JSON.stringify(body) } : {}),
  });
  if (!response.ok) {
    let message = `工单请求失败（${response.status}）`;
    try { message = (await response.json())?.error?.message || message; } catch { /* retain status */ }
    const error = new Error(message);
    error.status = response.status;
    throw error;
  }
  return response.json();
}

export async function listWorkOrders(token, fetchImpl = globalThis.fetch, apiBaseUrl = baseUrl) {
  const items = [];
  let page = 1;
  while (true) {
    const result = await request(`/api/v1/work-orders?page=${page}&pageSize=100`, token, { fetchImpl, apiBaseUrl });
    if (!Array.isArray(result.items) || !Number.isInteger(result.total)) throw new Error("工单列表响应格式不正确");
    items.push(...result.items);
    if (items.length >= result.total || result.items.length === 0) return items;
    page += 1;
  }
}

export const createWorkOrder = (token, body, fetchImpl, apiBaseUrl = baseUrl) => request("/api/v1/work-orders", token, { method: "POST", body, fetchImpl, apiBaseUrl });
export const patchWorkOrder = (token, id, body, fetchImpl, apiBaseUrl = baseUrl) => request(`/api/v1/work-orders/${encodeURIComponent(id)}`, token, { method: "PATCH", body, fetchImpl, apiBaseUrl });

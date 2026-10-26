const baseUrl = (import.meta.env?.VITE_API_BASE_URL || "").replace(/\/$/, "");

export async function listAuditEvents(token, fetchImpl = globalThis.fetch, apiBaseUrl = baseUrl) {
  if (!token || !apiBaseUrl) throw new Error("审计服务或登录信息未配置");
  const items = [];
  for (let page = 1; ; page += 1) {
    const response = await fetchImpl(`${apiBaseUrl}/api/v1/audit-events?page=${page}&pageSize=100`, {
      headers: { Accept: "application/json", Authorization: `Bearer ${token}` },
    });
    if (!response.ok) {
      let message = `审计记录请求失败（${response.status}）`;
      try { message = (await response.json())?.error?.message || message; } catch { /* use status */ }
      const error = new Error(message);
      error.status = response.status;
      throw error;
    }
    const result = await response.json();
    if (!Array.isArray(result.items) || !Number.isInteger(result.total)) throw new Error("审计记录响应格式不正确");
    items.push(...result.items);
    if (items.length >= result.total || result.items.length === 0) return items;
  }
}

const runtimeEnv = import.meta.env || {};
const baseUrl = (runtimeEnv.VITE_API_BASE_URL || "").replace(/\/$/, "");

export const memberRoleLabels = {
  owner: "企业负责人",
  admin: "系统管理员",
  manager: "维护主管",
  technician: "维修人员",
  viewer: "只读访客",
};

async function memberRequest(path, token, { method = "GET", body, fetchImpl = globalThis.fetch, apiBaseUrl = baseUrl } = {}) {
  if (!apiBaseUrl || !token) throw new Error("缺少后端地址或登录令牌");
  const response = await fetchImpl(`${apiBaseUrl}${path}`, {
    method,
    headers: {
      Accept: "application/json",
      Authorization: `Bearer ${token}`,
      ...(body ? { "Content-Type": "application/json" } : {}),
    },
    ...(body ? { body: JSON.stringify(body) } : {}),
  });
  if (!response.ok) {
    let message = `人员接口请求失败（${response.status}）`;
    try { message = (await response.json())?.error?.message || message; } catch { /* keep status message */ }
    const error = new Error(message);
    error.status = response.status;
    throw error;
  }
  return response.json();
}

export async function listMembers(token, fetchImpl = globalThis.fetch, apiBaseUrl = baseUrl) {
  const members = [];
  let page = 1;
  while (true) {
    const result = await memberRequest(`/api/v1/members?page=${page}&pageSize=100`, token, { fetchImpl, apiBaseUrl });
    if (!Array.isArray(result.items) || !Number.isInteger(result.total)) throw new Error("人员列表响应格式不正确");
    members.push(...result.items);
    if (members.length >= result.total || result.items.length === 0) return members;
    page += 1;
  }
}

export const createMember = (token, payload, fetchImpl, apiBaseUrl = baseUrl) => memberRequest("/api/v1/members", token, { method: "POST", body: payload, fetchImpl, apiBaseUrl });
export const patchMember = (token, id, payload, fetchImpl, apiBaseUrl = baseUrl) => memberRequest(`/api/v1/members/${encodeURIComponent(id)}`, token, { method: "PATCH", body: payload, fetchImpl, apiBaseUrl });

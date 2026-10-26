import * as mockData from "../data.js";

const runtimeEnv = import.meta.env || {};
const mode = runtimeEnv.VITE_DATA_MODE || "mock";
const baseUrl = (runtimeEnv.VITE_API_BASE_URL || "").replace(/\/$/, "");
const organizationId = runtimeEnv.VITE_API_ORGANIZATION_ID || "";
const userId = runtimeEnv.VITE_API_USER_ID || "";

const businessResources = {
  devices: "/api/v1/devices",
  alerts: "/api/v1/alerts",
  workOrders: "/api/v1/work-orders",
};

export class ApiRequestError extends Error {
  constructor(status, path) {
    super(`API request failed: ${status}`);
    this.name = "ApiRequestError";
    this.status = status;
    this.path = path;
  }
}

export function buildRequestHeaders({ accessToken, dataMode = mode, demoOrganizationId = organizationId, demoUserId = userId } = {}) {
  if (dataMode === "api" && !accessToken) throw new ApiRequestError(401, "authentication");
  const headers = { Accept: "application/json" };
  if (accessToken) headers.Authorization = `Bearer ${accessToken}`;
  else if (dataMode !== "api") {
    if (demoOrganizationId) headers["X-Organization-Id"] = demoOrganizationId;
    if (demoUserId) headers["X-User-Id"] = demoUserId;
  }
  return headers;
}

async function request(path, accessToken) {
  const headers = buildRequestHeaders({ accessToken });

  const response = await fetch(`${baseUrl}${path}`, {
    headers,
  });

  if (!response.ok) {
    throw new ApiRequestError(response.status, path);
  }

  return response.json();
}

export async function importDevices(items, accessToken, fetchImpl = globalThis.fetch, apiBaseUrl = baseUrl) {
  if (!apiBaseUrl || !accessToken) throw new ApiRequestError(401, "/api/v1/devices/import");
  const response = await fetchImpl(`${apiBaseUrl}/api/v1/devices/import`, {
    method: "POST",
    headers: { ...buildRequestHeaders({ accessToken, dataMode: "api" }), "Content-Type": "application/json" },
    body: JSON.stringify({ items: items.map(({ id, name, type, plant, location }) => ({ id, name, type, plant, location })) }),
  });
  if (!response.ok) {
    let message = `设备导入失败（${response.status}）`;
    try { message = (await response.json())?.error?.message || message; } catch { /* retain status */ }
    const error = new ApiRequestError(response.status, "/api/v1/devices/import");
    error.message = message;
    throw error;
  }
  return response.json();
}

export async function loadDeviceParameters(deviceId, accessToken) {
  const result = await request(`/api/v1/devices/${encodeURIComponent(deviceId)}/parameters?latest=true&pageSize=100`, accessToken);
  if (!Array.isArray(result.items)) throw new Error("设备测点响应格式不正确");
  return result.items;
}

function formatTimestamp(value) {
  if (!value) return "暂无更新";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return new Intl.DateTimeFormat("zh-CN", {
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
  }).format(date);
}

function normalizeCollection(key, payload) {
  if (!payload || !Array.isArray(payload.items)) {
    throw new Error(`${key} API response is missing items`);
  }

  if (key === "alerts") {
    return payload.items.map((item) => ({
      ...item,
      owner: item.owner || "未指派",
      time: formatTimestamp(item.time),
    }));
  }

  if (key === "workOrders") {
    return payload.items.map((item) => ({
      ...item,
      owner: item.owner || "未指派",
      updated: formatTimestamp(item.updated),
    }));
  }

  return payload.items;
}

async function loadBusinessCollection(key, path, accessToken) {
  const items = [];
  for (let page = 1; ; page += 1) {
    const separator = path.includes("?") ? "&" : "?";
    const payload = await request(`${path}${separator}page=${page}&pageSize=100`, accessToken);
    if (!Number.isInteger(payload.total)) throw new Error(`${key} API response is missing total`);
    const batch = normalizeCollection(key, payload);
    items.push(...batch);
    if (items.length >= payload.total || batch.length === 0) return items;
  }
}

export async function loadWorkspaceData({ accessToken } = {}) {
  if (mode !== "api") {
    return { data: mockData, source: "mock", connectedResources: [] };
  }
  if (!baseUrl) throw new Error("未配置业务 API 地址");

  const connectedEntries = await Promise.all(
    Object.entries(businessResources).map(async ([key, path]) => [
      key,
      await loadBusinessCollection(key, path, accessToken),
    ]),
  );

  return {
    data: { ...mockData, ...Object.fromEntries(connectedEntries), trendData: [], deviceProfiles: {}, evidence: [], auditRows: [] },
    source: "api",
    connectedResources: connectedEntries.map(([key]) => key),
  };
}


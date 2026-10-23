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

export async function loadWorkspaceData({ accessToken } = {}) {
  if (mode !== "api" || !baseUrl) {
    return { data: mockData, source: "mock", connectedResources: [] };
  }

  const results = await Promise.allSettled(
    Object.entries(businessResources).map(async ([key, path]) => [
      key,
      normalizeCollection(key, await request(path, accessToken)),
    ]),
  );
  const connectedEntries = results
    .filter((result) => result.status === "fulfilled")
    .map((result) => result.value);
  const failedResults = results.filter((result) => result.status === "rejected");

  const authFailure = failedResults.find(({ reason }) => reason?.status === 401 || reason?.status === 403);
  if (authFailure) throw authFailure.reason;

  if (failedResults.length) {
    console.warn(
      "Some ForgePilot business APIs are unavailable; keeping demo data for those resources.",
      failedResults.map((result) => result.reason),
    );
  }

  if (!connectedEntries.length) {
    return { data: mockData, source: "fallback", connectedResources: [] };
  }

  return {
    data: { ...mockData, ...Object.fromEntries(connectedEntries) },
    source: "hybrid",
    connectedResources: connectedEntries.map(([key]) => key),
  };
}


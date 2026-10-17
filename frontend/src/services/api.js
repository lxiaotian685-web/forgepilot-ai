import * as mockData from "../data";

const mode = import.meta.env.VITE_DATA_MODE || "mock";
const baseUrl = (import.meta.env.VITE_API_BASE_URL || "").replace(/\/$/, "");
const organizationId = import.meta.env.VITE_API_ORGANIZATION_ID || "";
const userId = import.meta.env.VITE_API_USER_ID || "";

const businessResources = {
  devices: "/api/v1/devices",
  alerts: "/api/v1/alerts",
  workOrders: "/api/v1/work-orders",
};

async function request(path) {
  const headers = { Accept: "application/json" };
  if (organizationId) headers["X-Organization-Id"] = organizationId;
  if (userId) headers["X-User-Id"] = userId;

  const response = await fetch(`${baseUrl}${path}`, {
    headers,
  });

  if (!response.ok) {
    throw new Error(`API request failed: ${response.status}`);
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

export async function loadWorkspaceData() {
  if (mode !== "api" || !baseUrl) {
    return { data: mockData, source: "mock", connectedResources: [] };
  }

  const results = await Promise.allSettled(
    Object.entries(businessResources).map(async ([key, path]) => [
      key,
      normalizeCollection(key, await request(path)),
    ]),
  );
  const connectedEntries = results
    .filter((result) => result.status === "fulfilled")
    .map((result) => result.value);
  const failedResults = results.filter((result) => result.status === "rejected");

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


import * as mockData from "../data";

const mode = import.meta.env.VITE_DATA_MODE || "mock";
const baseUrl = (import.meta.env.VITE_API_BASE_URL || "").replace(/\/$/, "");

const resources = {
  devices: "/api/v1/devices",
  alerts: "/api/v1/alerts",
  workOrders: "/api/v1/work-orders",
  evidence: "/api/v1/evidence",
  auditRows: "/api/v1/audit-events",
  trendData: "/api/v1/devices/AC-07/trends",
};

async function request(path) {
  const response = await fetch(`${baseUrl}${path}`, {
    headers: { Accept: "application/json" },
  });

  if (!response.ok) {
    throw new Error(`API request failed: ${response.status}`);
  }

  return response.json();
}

export async function loadWorkspaceData() {
  if (mode !== "api" || !baseUrl) {
    return { data: mockData, source: "mock" };
  }

  try {
    const entries = await Promise.all(
      Object.entries(resources).map(async ([key, path]) => [key, await request(path)]),
    );
    return { data: Object.fromEntries(entries), source: "api" };
  } catch (error) {
    console.warn("ForgePilot API unavailable; using demo data.", error);
    return { data: mockData, source: "fallback" };
  }
}


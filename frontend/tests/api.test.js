import { test } from "node:test";
import assert from "node:assert/strict";
import { ApiRequestError, buildRequestHeaders, createDeviceParameter, importDevices } from "../src/services/api.js";

test("api mode requires bearer authentication and never sends demo identity headers", () => {
  assert.throws(() => buildRequestHeaders({ dataMode: "api", demoOrganizationId: "demo-org", demoUserId: "demo@example.com" }), (error) => error instanceof ApiRequestError && error.status === 401);
  assert.deepEqual(buildRequestHeaders({ dataMode: "api", accessToken: "token", demoOrganizationId: "demo-org", demoUserId: "demo@example.com" }), { Accept: "application/json", Authorization: "Bearer token" });
});

test("manual inspection writes one timestamped device parameter", async () => {
  let sent;
  await createDeviceParameter("AC-07", { name: "vibration", value: 4.2, unit: "mm/s", source: "manual", sourceRef: "人工巡检：驱动端", recordedAt: "2026-11-04T02:00:00.000Z" }, "token", async (url, options) => {
    sent = { url, options };
    return new Response(JSON.stringify({ id: "parameter-id" }), { status: 201 });
  }, "https://api.example.test");
  assert.equal(sent.url, "https://api.example.test/api/v1/devices/AC-07/parameters");
  assert.equal(sent.options.method, "POST");
  assert.equal(sent.options.headers.Authorization, "Bearer token");
  assert.equal(JSON.parse(sent.options.body).source, "manual");
});

test("mock mode may use explicitly configured demo headers", () => {
  assert.deepEqual(buildRequestHeaders({ dataMode: "mock", demoOrganizationId: "demo-org", demoUserId: "demo@example.com" }), { Accept: "application/json", "X-Organization-Id": "demo-org", "X-User-Id": "demo@example.com" });
});

test("device import sends only validated business fields with bearer token", async () => {
  let sent;
  const fetchImpl = async (url, options) => {
    sent = { url, options };
    return new Response(JSON.stringify({ created: 1, items: [] }), { status: 201 });
  };
  const result = await importDevices([{ id: "M-001", name: "电机", type: "电机", plant: "上海演示工厂", location: "动力站", importRow: 2, errors: [] }], "token", fetchImpl, "https://api.example.test");
  assert.equal(result.created, 1);
  assert.equal(sent.options.headers.Authorization, "Bearer token");
  assert.deepEqual(JSON.parse(sent.options.body), { items: [{ id: "M-001", name: "电机", type: "电机", plant: "上海演示工厂", location: "动力站" }] });
});

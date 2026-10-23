import { test } from "node:test";
import assert from "node:assert/strict";
import { ApiRequestError, buildRequestHeaders } from "../src/services/api.js";

test("api mode requires bearer authentication and never sends demo identity headers", () => {
  assert.throws(() => buildRequestHeaders({ dataMode: "api", demoOrganizationId: "demo-org", demoUserId: "demo@example.com" }), (error) => error instanceof ApiRequestError && error.status === 401);
  assert.deepEqual(buildRequestHeaders({ dataMode: "api", accessToken: "token", demoOrganizationId: "demo-org", demoUserId: "demo@example.com" }), { Accept: "application/json", Authorization: "Bearer token" });
});

test("mock mode may use explicitly configured demo headers", () => {
  assert.deepEqual(buildRequestHeaders({ dataMode: "mock", demoOrganizationId: "demo-org", demoUserId: "demo@example.com" }), { Accept: "application/json", "X-Organization-Id": "demo-org", "X-User-Id": "demo@example.com" });
});

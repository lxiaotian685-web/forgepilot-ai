import test from "node:test";
import assert from "node:assert/strict";
import { createAlert, listAlerts, patchAlert } from "../src/services/alertsApi.js";

const base = "https://api.example.test";

test("alert list paginates with bearer token", async () => {
  const calls = [];
  const fetchImpl = async (url, options) => {
    calls.push({ url, options });
    return new Response(JSON.stringify({ items: [{ id: `ALT-${calls.length}` }], total: 2 }), { status: 200 });
  };
  assert.equal((await listAlerts("token", fetchImpl, base)).length, 2);
  assert.match(calls[1].url, /page=2/);
  assert.equal(calls[0].options.headers.Authorization, "Bearer token");
});

test("alert create and update retain owner UUID and status", async () => {
  const calls = [];
  const fetchImpl = async (url, options) => {
    calls.push({ url, options });
    return new Response(JSON.stringify({ id: "ALT-1" }), { status: 200 });
  };
  await createAlert("token", { deviceId: "AC-07", ownerId: "user-1", level: "一级紧急", title: "高温" }, fetchImpl, base);
  await patchAlert("token", "ALT-1", { status: "处理中" }, fetchImpl, base);
  assert.equal(calls[0].options.method, "POST");
  assert.equal(JSON.parse(calls[0].options.body).ownerId, "user-1");
  assert.equal(calls[1].options.method, "PATCH");
  assert.equal(JSON.parse(calls[1].options.body).status, "处理中");
});

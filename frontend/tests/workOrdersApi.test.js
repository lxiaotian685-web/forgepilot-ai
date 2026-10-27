import assert from "node:assert/strict";
import test from "node:test";
import { createWorkOrder, listWorkOrders, patchWorkOrder } from "../src/services/workOrdersApi.js";

test("work orders list loads every server page with bearer identity", async () => {
  const calls = [];
  const fetchImpl = async (url, options) => {
    calls.push({ url, options });
    const page = Number(new URL(url).searchParams.get("page"));
    return { ok: true, json: async () => ({ items: [{ id: `WO-${page}` }], total: 2 }) };
  };
  const orders = await listWorkOrders("token", fetchImpl, "https://api.example.com");
  assert.deepEqual(orders.map((order) => order.id), ["WO-1", "WO-2"]);
  assert.equal(calls.length, 2);
  assert.equal(calls[0].options.headers.Authorization, "Bearer token");
});

test("work order create and cancellation forward the business payload", async () => {
  const calls = [];
  const fetchImpl = async (url, options) => {
    calls.push({ url, options });
    return { ok: true, json: async () => ({ id: "WO-1" }) };
  };
  await createWorkOrder("token", { title: "检修", deviceId: "AC-07", ownerId: "user-id" }, fetchImpl, "https://api.example.com");
  await patchWorkOrder("token", "WO-1", { status: "已取消", cancelReason: "误报" }, fetchImpl, "https://api.example.com");
  assert.equal(calls[0].options.method, "POST");
  assert.equal(JSON.parse(calls[0].options.body).ownerId, "user-id");
  assert.equal(calls[1].options.method, "PATCH");
  assert.equal(JSON.parse(calls[1].options.body).cancelReason, "误报");
});

import test from "node:test";
import assert from "node:assert/strict";
import { canDeleteWorkOrder, filterWorkOrders, transitionWorkOrder, validateWorkOrder } from "../src/services/workOrderLifecycle.js";

const orders = [
  { id: "WO-1", title: "更换轴承", deviceId: "AC-07", priority: "P1 紧急", owner: "张工", status: "处理中" },
  { id: "WO-2", title: "密封检查", deviceId: "P-102", priority: "P2 高", owner: "王强", status: "待验收" },
];

test("filters work orders by combined business fields", () => {
  assert.deepEqual(filterWorkOrders(orders, { status: "处理中", owner: "张工", query: "AC-07" }).map((item) => item.id), ["WO-1"]);
});

test("enforces lifecycle transitions and cancellation reason", () => {
  assert.equal(transitionWorkOrder(orders[0], "待验收").status, "待验收");
  assert.throws(() => transitionWorkOrder(orders[0], "已完成"), /不能/);
  assert.throws(() => transitionWorkOrder(orders[0], "已取消"), /原因/);
});

test("only local drafts can be deleted", () => {
  assert.equal(canDeleteWorkOrder({ draft: true }), true);
  assert.equal(canDeleteWorkOrder({ draft: false }), false);
});

test("requires title device owner and schedule", () => {
  assert.deepEqual(Object.keys(validateWorkOrder({})).sort(), ["deviceId", "dueDate", "owner", "title"]);
  assert.deepEqual(validateWorkOrder({ title: "检查", deviceId: "AC-07", owner: "张工", dueDate: "2026-10-25" }), {});
});

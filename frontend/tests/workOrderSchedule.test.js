import { test } from "node:test";
import assert from "node:assert/strict";
import { formatWorkOrderSchedule, normalizeWorkOrder, validateWorkOrder } from "../src/services/workOrderLifecycle.js";

test("planned interval normalizes from API and appears in work order views", () => {
  const order = normalizeWorkOrder({ plannedStartAt: "2026-10-28T04:00:00Z", dueAt: "2026-10-30T04:00:00Z" });
  assert.equal(order.startDate, "2026-10-28");
  assert.equal(formatWorkOrderSchedule(order), "2026-10-28 至 2026-10-30");
  assert.equal(formatWorkOrderSchedule(normalizeWorkOrder({ dueAt: "2026-10-30T04:00:00Z" })), "截至 2026-10-30");
});

test("planned end must not precede planned start", () => {
  const base = { title: "轴承复检", deviceId: "AC-07", owner: "张工", startDate: "2026-10-30", dueDate: "2026-10-28" };
  assert.equal(validateWorkOrder(base).dueDate, "结束日期不能早于开始日期");
  assert.deepEqual(validateWorkOrder({ ...base, dueDate: "2026-10-30" }), {});
});

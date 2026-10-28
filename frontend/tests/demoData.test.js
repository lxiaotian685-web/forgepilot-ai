import test from "node:test";
import assert from "node:assert/strict";
import { alerts, deviceProfiles, devices, evidence, workOrders } from "../src/data.js";

test("demo screens have enough distinct, connected records", () => {
  for (const rows of [devices, alerts, workOrders, evidence]) assert.ok(rows.length >= 10);
  assert.equal(new Set(devices.map((device) => device.id)).size, devices.length);
  assert.equal(new Set(workOrders.map((order) => order.id)).size, workOrders.length);
  assert.equal(new Set(evidence.map((item) => item.name)).size, evidence.length);
  const deviceIds = new Set(devices.map((device) => device.id));
  assert.deepEqual(Object.keys(deviceProfiles).sort(), [...deviceIds].sort());
  for (const order of workOrders) {
    assert.ok(deviceIds.has(order.deviceId), `${order.id} references an unknown device`);
    assert.ok(order.startDate && order.dueDate && order.startDate <= order.dueDate);
  }
  for (const device of devices) {
    const openAlerts = alerts.filter((alert) => alert.status !== "已关闭" && alert.device.startsWith(`${device.id} `));
    assert.equal(device.alert, openAlerts.length, `${device.id} alert count is inconsistent`);
  }
});

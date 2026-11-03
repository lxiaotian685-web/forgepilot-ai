import { test } from "node:test";
import assert from "node:assert/strict";
import { buildDeviceProfile, formatRecordedAt } from "../src/services/deviceProfile.js";

test("separates sensor readings from nameplate facts", () => {
  const profile = buildDeviceProfile([
    { name: "temperature", value: 91, unit: "°C", source: "sensor", recordedAt: "2026-05-18T09:44:00Z" },
    { name: "rated_power", value: 55, unit: "kW", source: "nameplate", recordedAt: "2026-04-18T09:44:00Z" },
  ]);
  assert.equal(profile.sensors[0].label, "轴承温度");
  assert.equal(profile.sensors[0].note, "未配置判定阈值");
  assert.equal(profile.nameplate[0].label, "额定功率");
  assert.equal(profile.latest, "2026-05-18T09:44:00Z");
});

test("formats valid collection time and preserves invalid source text", () => {
  assert.match(formatRecordedAt("2026-05-18T09:44:00Z"), /2026/);
  assert.equal(formatRecordedAt("legacy-time"), "legacy-time");
});

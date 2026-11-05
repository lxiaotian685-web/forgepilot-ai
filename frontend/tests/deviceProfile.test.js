import { test } from "node:test";
import assert from "node:assert/strict";
import { buildDeviceProfile, formatRecordedAt } from "../src/services/deviceProfile.js";

test("separates sensor readings from nameplate facts", () => {
  const profile = buildDeviceProfile([
    { name: "temperature", value: 91, unit: "°C", source: "sensor", recordedAt: "2026-05-18T09:44:00Z" },
    { name: "rated_power", value: 55, unit: "kW", source: "nameplate", recordedAt: "2026-04-18T09:44:00Z" },
  ]);
  assert.equal(profile.sensors[0].label, "轴承温度");
  assert.equal(profile.sensors[0].note, "传感器采集 · 未配置判定阈值");
  assert.equal(profile.nameplate[0].label, "额定功率");
  assert.equal(profile.latest, "2026-05-18T09:44:00Z");
});

test("formats valid collection time and preserves invalid source text", () => {
  assert.match(formatRecordedAt("2026-05-18T09:44:00Z"), /2026/);
  assert.equal(formatRecordedAt("legacy-time"), "legacy-time");
});

test("shows manual inspection as a recent operating reading", () => {
  const profile = buildDeviceProfile([{ name: "vibration", value: 4.2, unit: "mm/s", source: "manual", recordedAt: "2026-11-04T02:00:00Z" }]);
  assert.equal(profile.sensors.length, 1);
  assert.equal(profile.sensors[0].value, 4.2);
  assert.match(profile.sensors[0].note, /人工巡检/);
});

test("builds chronological trend points from sensor and manual history", () => {
  const profile = buildDeviceProfile([
    { name: "vibration", value: 3.1, unit: "mm/s", source: "sensor", recordedAt: "2026-11-05T01:00:00Z" },
    { name: "vibration", value: 4.2, unit: "mm/s", source: "manual", recordedAt: "2026-11-05T02:00:00Z" },
    { name: "temperature", value: 68, unit: "°C", source: "manual", recordedAt: "2026-11-05T02:00:00Z" },
  ]);
  assert.equal(profile.trend.length, 2);
  assert.deepEqual(profile.trend.map((point) => point.vibration), [3.1, 4.2]);
  assert.equal(profile.trend[1].temperature, 68);
  assert.deepEqual(profile.sources.sort(), ["人工巡检", "传感器采集"]);
});

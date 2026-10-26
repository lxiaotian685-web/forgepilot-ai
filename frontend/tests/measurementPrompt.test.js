import assert from "node:assert/strict";
import test from "node:test";
import { buildMeasurementQuestion } from "../src/services/measurementPrompt.js";

test("current measurements form a grounded question without assuming a threshold", () => {
  const question = buildMeasurementQuestion("AC-07", [{ name: "排气温度", value: 92, unit: "°C", recordedAt: "2026-10-26T12:00:00Z", source: "sensor" }]);
  assert.match(question, /排气温度：92°C/);
  assert.match(question, /没有阈值或工况依据时不要断言超限/);
});

test("empty or invalid measurements cannot start automatic questioning", () => {
  assert.throws(() => buildMeasurementQuestion("AC-07", []), /没有可用测点/);
  assert.throws(() => buildMeasurementQuestion("AC-07", [{ name: "温度", value: "bad" }]), /缺少名称或数值/);
});

import test from "node:test";
import assert from "node:assert/strict";
import { buildInspectionPayloads, defaultInspectionRows, localDateTimeValue } from "../src/services/inspectionForm.js";

test("builds multiple manual inspection payloads from one field visit", () => {
  const rows = defaultInspectionRows();
  rows[0].value = "4.2";
  rows[1].value = "68";
  const payloads = buildInspectionPayloads({ rows, point: "驱动端轴承", recordedAt: "2026-11-05T10:30" });
  assert.equal(payloads.length, 2);
  assert.equal(payloads[0].source, "manual");
  assert.equal(payloads[0].sourceRef, "人工巡检：驱动端轴承");
  assert.equal(payloads[1].unit, "°C");
});

test("inspection form defaults time and rejects empty or duplicate metrics", () => {
  assert.match(localDateTimeValue(new Date("2026-11-05T02:30:00Z")), /^2026-11-05T/);
  assert.throws(() => buildInspectionPayloads({ rows: defaultInspectionRows(), point: "驱动端", recordedAt: "2026-11-05T10:30" }), /至少填写/);
  assert.throws(() => buildInspectionPayloads({ rows: [{ name: "vibration", unit: "mm\/s", value: "1" }, { name: "vibration", unit: "mm\/s", value: "2" }], point: "驱动端", recordedAt: "2026-11-05T10:30" }), /重复/);
});

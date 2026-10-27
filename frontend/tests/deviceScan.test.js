import assert from "node:assert/strict";
import test from "node:test";
import { parseDeviceQr } from "../src/services/deviceScan.js";

test("device QR accepts structured device JSON and forgepilot link", () => {
  assert.deepEqual(parseDeviceQr('{"id":"M-001","name":"电机","type":"电机","plant":"一厂","location":"动力站"}'), { id: "M-001", name: "电机", type: "电机", plant: "一厂", location: "动力站" });
  assert.equal(parseDeviceQr("forgepilot://device?id=M-002&name=Pump").id, "M-002");
});

test("device QR rejects arbitrary links and malformed content", () => {
  assert.throws(() => parseDeviceQr("https://example.com/device?id=M-001"), /不是 ForgePilot/);
  assert.throws(() => parseDeviceQr("{broken"), /JSON 格式/);
});

import { test } from "node:test";
import assert from "node:assert/strict";
import { createDeviceImportTemplate, filterDevices, parseDeviceImport } from "../src/services/deviceCenter.js";

const devices = [
  { id: "AC-07", name: "空压机", type: "动力设备", plant: "一号装配厂", location: "压缩站", state: "需关注" },
  { id: "P-102", name: "离心泵", type: "流体设备", plant: "二号装配厂", location: "水站", state: "运行正常" },
];

test("device filters combine search, type, state and plant", () => {
  assert.deepEqual(filterDevices(devices, { query: "水站" }).map((item) => item.id), ["P-102"]);
  assert.deepEqual(filterDevices(devices, { type: "动力设备", state: "需关注", plant: "一号装配厂" }).map((item) => item.id), ["AC-07"]);
  assert.deepEqual(filterDevices(devices, { type: "动力设备", plant: "二号装配厂" }), []);
});

test("CSV import accepts quoted cells and maps the required fields", () => {
  const result = parseDeviceImport('设备编号,设备名称,设备类型,厂区,位置\nM-001,"主驱动,电机",电机,一号装配厂,动力站');
  assert.deepEqual(result.errors, []);
  assert.equal(result.rows[0].name, "主驱动,电机");
  assert.deepEqual(result.rows[0].errors, []);
});

test("CSV import reports missing headers, existing ids and duplicate rows", () => {
  assert.match(parseDeviceImport("设备编号,设备名称\nM-001,电机").errors[0], /缺少表头/);
  const result = parseDeviceImport("设备编号,设备名称,设备类型,厂区,位置\nAC-07,空压机,动力,一号装配厂,压缩站\nAC-07,另一台,动力,一号装配厂,压缩站", ["AC-07"]);
  assert.match(result.rows[0].errors.join("、"), /已存在/);
  assert.match(result.rows[1].errors.join("、"), /文件内.*重复/);
});

test("CSV import reports empty files and malformed quotes", () => {
  assert.deepEqual(parseDeviceImport(""), { rows: [], errors: ["文件为空"] });
  assert.throws(() => parseDeviceImport('设备编号,设备名称,设备类型,厂区,位置\nM-001,"坏数据,电机,一号装配厂,动力站'), /未闭合/);
});

test("template can be parsed without row errors", () => {
  const result = parseDeviceImport(createDeviceImportTemplate());
  assert.equal(result.rows.length, 1);
  assert.deepEqual(result.rows[0].errors, []);
});

import { test } from "node:test";
import assert from "node:assert/strict";
import { alertDeviceId, countAlerts, filterAlerts, transitionAlert } from "../src/services/alertCenter.js";

const alerts = [
  { id: "A-1", level: "一级紧急", title: "振动超限", device: "AC-07 空压机", owner: "未指派", status: "待确认" },
  { id: "A-2", level: "二级警告", title: "温度偏高", device: "P-102 离心泵", owner: "王强", status: "处理中" },
  { id: "A-3", level: "三级提示", title: "短时波动", device: "AC-07 空压机", owner: "张工", status: "已关闭" },
];

test("counts are derived from the current alert list", () => assert.deepEqual(countAlerts(alerts), { all: 3, 待确认: 1, 处理中: 1, 已关闭: 1 }));
test("combines status, severity, owner, device and search filters", () => {
  assert.deepEqual(filterAlerts(alerts, { status: "处理中", owner: "王强" }).map((item) => item.id), ["A-2"]);
  assert.deepEqual(filterAlerts(alerts, { query: "ac-07", level: "一级紧急" }).map((item) => item.id), ["A-1"]);
});
test("requires an owner and rejects illegal status jumps", () => {
  assert.throws(() => transitionAlert(alerts[0], "处理中", "未指派"), /负责人/);
  assert.equal(transitionAlert(alerts[0], "处理中", "赵工").owner, "赵工");
  assert.throws(() => transitionAlert(alerts[0], "已关闭", "赵工"), /不能从/);
});
test("extracts the equipment id for downstream context", () => assert.equal(alertDeviceId(alerts[1]), "P-102"));

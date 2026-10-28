import test from "node:test";
import assert from "node:assert/strict";
import { filterAuditRows, filterEvidence, validateEvidenceFile } from "../src/services/workspaceFilters.js";

test("knowledge search combines document type and actual state", () => {
  const rows = [{ name: "Pump.pdf", type: "检修规程", state: "可用", device: "P-102" }, { name: "Atlas.pdf", type: "技术说明书", state: "未解析", device: "AC-07" }];
  assert.deepEqual(filterEvidence(rows, { type: "检修规程", query: "P-102" }).map((item) => item.name), ["Pump.pdf"]);
});

test("local upload rejects duplicate, oversized, unsupported files", () => {
  assert.throws(() => validateEvidenceFile({ name: "manual.exe", size: 1 }, []), /仅支持/);
  assert.throws(() => validateEvidenceFile({ name: "manual.pdf", size: 11 * 1024 * 1024 }, []), /10 MB/);
  assert.throws(() => validateEvidenceFile({ name: "manual.pdf", size: 1 }, ["MANUAL.PDF"]), /同名/);
  assert.doesNotThrow(() => validateEvidenceFile({ name: "manual.pdf", size: 1 }, []));
});

test("audit search and filters return actual matching records", () => {
  const rows = [{ user: "李振华", action: "确认告警", object: "ALT-01" }, { user: "张工", action: "创建工单", object: "WO-01" }];
  assert.deepEqual(filterAuditRows(rows, { actor: "张工", query: "WO-01" }).map((item) => item.object), ["WO-01"]);
});

test("audit date windows include recent records and exclude older ones", () => {
  const rows = [
    { time: "2026-10-27T12:00:00Z", user: "李振华", action: "确认告警", object: "ALT-01" },
    { time: "2026-10-22T12:00:00Z", user: "张工", action: "生成工单", object: "WO-01" },
    { time: "2026-09-20T12:00:00Z", user: "赵工", action: "取消工单", object: "WO-02" },
  ];
  const now = new Date("2026-10-28T12:00:00Z");
  assert.deepEqual(filterAuditRows(rows, { days: 3 }, now).map((row) => row.object), ["ALT-01"]);
  assert.deepEqual(filterAuditRows(rows, { days: 7 }, now).map((row) => row.object), ["ALT-01", "WO-01"]);
  assert.equal(filterAuditRows(rows, { days: 30 }, now).length, 2);
});

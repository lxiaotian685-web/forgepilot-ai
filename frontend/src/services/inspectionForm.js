export const inspectionMetrics = [
  { name: "vibration", label: "振动速度", unit: "mm/s" },
  { name: "temperature", label: "轴承温度", unit: "°C" },
  { name: "pressure", label: "运行压力", unit: "MPa" },
  { name: "load_rate", label: "负载率", unit: "%" },
  { name: "operating_current", label: "运行电流", unit: "A" },
];

export const defaultInspectionRows = () => inspectionMetrics.slice(0, 2).map(({ name, unit }) => ({ name, unit, value: "" }));

export function localDateTimeValue(date = new Date()) {
  const local = new Date(date.getTime() - date.getTimezoneOffset() * 60_000);
  return local.toISOString().slice(0, 16);
}

export function buildInspectionPayloads({ rows, point, recordedAt }) {
  const completed = rows.filter((row) => String(row.value).trim() !== "");
  if (!point.trim()) throw new Error("请填写实际测点位置");
  if (!recordedAt) throw new Error("请选择采样时间");
  if (!completed.length) throw new Error("请至少填写一项巡检数值");
  if (new Set(completed.map((row) => row.name)).size !== completed.length) throw new Error("同一次巡检不能重复填写同一指标");
  return completed.map((row) => {
    if (!Number.isFinite(Number(row.value))) throw new Error("巡检数值必须是有效数字");
    return {
      name: row.name, value: Number(row.value), unit: row.unit || null, source: "manual",
      sourceRef: `人工巡检：${point.trim()}`, recordedAt: new Date(recordedAt).toISOString(),
    };
  });
}

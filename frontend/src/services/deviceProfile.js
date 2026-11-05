const labels = {
  temperature: "轴承温度",
  vibration: "振动速度",
  spindle_temperature: "主轴温度",
  spindle_vibration: "主轴振动",
  load_rate: "主轴负载率",
  coolant_temperature: "冷却液温度",
  rated_power: "额定功率",
  rated_pressure: "额定压力",
  pressure: "运行压力",
  operating_current: "运行电流",
};

const colors = ["#0f5a91", "#d45522", "#5d7f2b"];

export function buildDeviceProfile(items = []) {
  const operating = items.filter((item) => ["sensor", "manual", "imported", "corrected"].includes(item.source));
  const latestByName = new Map();
  [...operating].sort((a, b) => String(b.recordedAt).localeCompare(String(a.recordedAt))).forEach((item) => {
    if (!latestByName.has(item.name)) latestByName.set(item.name, item);
  });
  const sensors = [...latestByName.values()].map((item) => ({
    ...item, label: labels[item.name] || item.name,
    note: `${item.source === "manual" ? "人工巡检" : "传感器采集"} · 未配置判定阈值`,
  }));
  const nameplate = items.filter((item) => item.source === "nameplate").map((item) => ({
    ...item, label: labels[item.name] || item.name, note: "设备铭牌参数",
  }));
  const latest = sensors.map((item) => item.recordedAt).filter(Boolean).sort().at(-1) || null;
  const seriesNames = [...new Set(operating.map((item) => item.name))].slice(0, 3);
  const grouped = new Map();
  operating.filter((item) => seriesNames.includes(item.name)).forEach((item) => {
    const time = item.recordedAt || "未记录时间";
    const point = grouped.get(time) || { recordedAt: time, time: formatRecordedAt(time), sources: new Set() };
    point[item.name] = item.value;
    point.sources.add(item.source === "manual" ? "人工巡检" : "传感器采集");
    grouped.set(time, point);
  });
  const trend = [...grouped.values()].sort((a, b) => String(a.recordedAt).localeCompare(String(b.recordedAt))).map((point) => ({ ...point, source: [...point.sources].join("、"), sources: undefined }));
  const series = seriesNames.map((name, index) => ({ key: name, label: `${labels[name] || name} ${latestByName.get(name)?.unit || ""}`.trim(), color: colors[index] }));
  const sources = [...new Set(operating.map((item) => item.source === "manual" ? "人工巡检" : "传感器采集"))];
  return { sensors, nameplate, latest, trend, series, sources };
}

export function formatRecordedAt(value) {
  if (!value) return "尚未记录采集时间";
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? value : date.toLocaleString("zh-CN", { hour12: false });
}

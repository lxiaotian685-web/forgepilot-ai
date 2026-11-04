const labels = {
  temperature: "轴承温度",
  vibration: "振动速度",
  spindle_temperature: "主轴温度",
  spindle_vibration: "主轴振动",
  load_rate: "主轴负载率",
  coolant_temperature: "冷却液温度",
  rated_power: "额定功率",
  rated_pressure: "额定压力",
};

export function buildDeviceProfile(items = []) {
  const sensors = items.filter((item) => ["sensor", "manual", "imported", "corrected"].includes(item.source)).map((item) => ({
    ...item, label: labels[item.name] || item.name, note: "未配置判定阈值",
  }));
  const nameplate = items.filter((item) => item.source === "nameplate").map((item) => ({
    ...item, label: labels[item.name] || item.name, note: "设备铭牌参数",
  }));
  const latest = sensors.map((item) => item.recordedAt).filter(Boolean).sort().at(-1) || null;
  return { sensors, nameplate, latest };
}

export function formatRecordedAt(value) {
  if (!value) return "尚未记录采集时间";
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? value : date.toLocaleString("zh-CN", { hour12: false });
}

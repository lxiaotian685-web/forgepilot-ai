export const trendData = [
  { time: "08:00", vibration: 3.1, temperature: 67 },
  { time: "08:20", vibration: 3.2, temperature: 69 },
  { time: "08:40", vibration: 3.4, temperature: 72 },
  { time: "08:58", vibration: 4.8, temperature: 76 },
  { time: "09:12", vibration: 6.1, temperature: 81 },
  { time: "09:24", vibration: 7.82, temperature: 88.5 },
  { time: "09:42", vibration: 7.4, temperature: 91 },
];

export const alerts = [
  { id: "ALT-0941", level: "一级紧急", title: "驱动端轴承高频振动 RMS 严重突破警戒上限", device: "AC-07 螺杆空气压缩机", time: "44 分钟", owner: "张工", status: "待确认" },
  { id: "ALT-0938", level: "二级警告", title: "排气温度连续接近预警阈值", device: "P-102 高压离心注水泵", time: "1 小时", owner: "王强", status: "处理中" },
  { id: "ALT-0926", level: "二级警告", title: "主轴负载波动超过基线范围", device: "CNC-04 数控龙门铣床", time: "3 小时", owner: "未指派", status: "待确认" },
  { id: "ALT-0911", level: "三级提示", title: "润滑油压差出现短时下降", device: "AC-08 螺杆空气压缩机", time: "昨天", owner: "张工", status: "已关闭" },
];

export const devices = [
  { id: "AC-07", name: "螺杆空气压缩机", type: "动力与流体机械", plant: "一号装配厂", location: "压缩站 Bay03", health: 72.4, state: "需关注", alert: 1 },
  { id: "P-102", name: "高压离心注水泵", type: "流体动力系统", plant: "一号装配厂", location: "冷却循环水站", health: 84.2, state: "需关注", alert: 1 },
  { id: "CNC-04", name: "数控龙门铣床", type: "精密加工单元", plant: "二号装配厂", location: "重载加工岛 #3", health: 41, state: "告警异常", alert: 2 },
  { id: "WR-09", name: "自动焊接机器人", type: "工业机器人", plant: "二号装配厂", location: "车身拼装线 #2", health: 98.2, state: "运行正常", alert: 0 },
  { id: "CV-01", name: "重型板链输送线", type: "仓储物流输送", plant: "一号装配厂", location: "物流转运通道", health: 95, state: "运行正常", alert: 0 },
];

export const deviceProfiles = {
  "AC-07": { updatedAt: "2026-10-23 09:42", metrics: [{ label: "驱动端振动 RMS", value: "7.82", unit: "mm/s", limit: "警戒 4.50", tone: "danger" }, { label: "排气温度", value: "88.5", unit: "°C", limit: "预警 85.0", tone: "warning" }, { label: "润滑油压差", value: "0.28", unit: "MPa", limit: "正常 0.20–0.35", tone: "success" }], series: [{ key: "vibration", label: "振动 mm/s", color: "#0f5a91" }, { key: "temperature", label: "温度 °C", color: "#d45522" }], trend: trendData, alertSummary: "驱动端振动持续超限，1 条待确认告警", documents: ["GX11 用户手册 RevC", "ISO 10816-3 振动标准"] },
  "P-102": { updatedAt: "2026-10-23 09:40", metrics: [{ label: "入口压力", value: "0.34", unit: "MPa", limit: "正常 0.28–0.40", tone: "success" }, { label: "出口压力", value: "6.18", unit: "MPa", limit: "额定 6.30", tone: "success" }, { label: "轴承温度", value: "76.2", unit: "°C", limit: "预警 75.0", tone: "warning" }], series: [{ key: "pressure", label: "出口压力 MPa", color: "#0f5a91" }, { key: "bearingTemperature", label: "轴承温度 °C", color: "#d45522" }], trend: [{ time: "08:00", pressure: 6.31, bearingTemperature: 68 }, { time: "08:30", pressure: 6.28, bearingTemperature: 70 }, { time: "09:00", pressure: 6.24, bearingTemperature: 73 }, { time: "09:40", pressure: 6.18, bearingTemperature: 76.2 }], alertSummary: "轴承温度接近阈值，1 条处理中告警", documents: ["P-102X 离心泵操作手册", "机械密封检修规程"] },
  "CNC-04": { updatedAt: "2026-10-23 09:38", metrics: [{ label: "主轴负载", value: "91.6", unit: "%", limit: "预警 85.0", tone: "danger" }, { label: "主轴转速", value: "6,200", unit: "rpm", limit: "程序设定 6,000", tone: "warning" }, { label: "冷却液温度", value: "24.8", unit: "°C", limit: "正常 20–28", tone: "success" }], series: [{ key: "spindleLoad", label: "主轴负载 %", color: "#0f5a91" }, { key: "coolantTemperature", label: "冷却液温度 °C", color: "#d45522" }], trend: [{ time: "08:00", spindleLoad: 62, coolantTemperature: 22.1 }, { time: "08:30", spindleLoad: 74, coolantTemperature: 23.2 }, { time: "09:00", spindleLoad: 88, coolantTemperature: 24.1 }, { time: "09:38", spindleLoad: 91.6, coolantTemperature: 24.8 }], alertSummary: "主轴负载异常，2 条待处理告警", documents: ["CNC-04 主轴维护手册", "加工中心点检规程"] },
  "WR-09": { updatedAt: "2026-10-23 09:41", metrics: [{ label: "焊接电流", value: "218", unit: "A", limit: "工艺 210–225", tone: "success" }, { label: "六轴扭矩", value: "42", unit: "%", limit: "正常 < 70", tone: "success" }, { label: "循环节拍", value: "48.2", unit: "s", limit: "目标 50.0", tone: "success" }], series: [{ key: "current", label: "焊接电流 A", color: "#0f5a91" }, { key: "cycle", label: "循环节拍 s", color: "#d45522" }], trend: [{ time: "08:00", current: 214, cycle: 49.2 }, { time: "08:30", current: 220, cycle: 48.8 }, { time: "09:00", current: 216, cycle: 48.5 }, { time: "09:41", current: 218, cycle: 48.2 }], alertSummary: "当前无活动告警", documents: ["WR-09 机器人维护手册"] },
  "CV-01": { updatedAt: "2026-10-23 09:39", metrics: [{ label: "链速", value: "12.4", unit: "m/min", limit: "设定 12.5", tone: "success" }, { label: "电机电流", value: "18.6", unit: "A", limit: "正常 < 24", tone: "success" }, { label: "张紧行程", value: "63", unit: "%", limit: "正常 40–75", tone: "success" }], series: [{ key: "speed", label: "链速 m/min", color: "#0f5a91" }, { key: "current", label: "电机电流 A", color: "#d45522" }], trend: [{ time: "08:00", speed: 12.3, current: 17.8 }, { time: "08:30", speed: 12.5, current: 18.2 }, { time: "09:00", speed: 12.4, current: 18.9 }, { time: "09:39", speed: 12.4, current: 18.6 }], alertSummary: "当前无活动告警", documents: ["CV-01 输送线保养规程"] },
};

export const workOrders = [
  { id: "WO-20250518-01", title: "AC-07 驱动端深沟球轴承紧急更换与润滑脂加注", priority: "P1 紧急", owner: "张工", status: "处理中", updated: "8 分钟前" },
  { id: "WO-20250518-02", title: "P-102 机械密封泄漏检查", priority: "P2 高", owner: "王强", status: "待验收", updated: "25 分钟前" },
  { id: "WO-20250517-03", title: "CNC-04 主轴动平衡校准", priority: "P3 中", owner: "赵工", status: "待处理", updated: "2 小时前" },
  { id: "WO-20250516-04", title: "AC-08 月度定检与油分滤芯检查", priority: "P4 低", owner: "张工", status: "已完成", updated: "2 天前" },
  { id: "WO-20250515-05", title: "CNC-04 主轴巡检（重复报修）", priority: "P3 中", owner: "赵工", status: "已取消", updated: "3 天前", cancellationReason: "与 WO-20250517-03 为同一故障，已合并到该工单处理。" },
];

export const evidence = [
  { name: "Atlas_Copco_GX11_UserManual_RevC.pdf", type: "技术说明书", version: "RevC", device: "AC-07", source: "阿特拉斯官方", state: "可用", chunks: 42 },
  { name: "ISO-10816-3_VibrationStandard.pdf", type: "行业标准", version: "2018", device: "工业回转设备", source: "国家标准委", state: "可用", chunks: 18 },
  { name: "AC07_DriveAssembly_MechanicalDrawing.dwg", type: "装配 CAD", version: "v2.1", device: "AC-07", source: "厂内工程部", state: "可用", chunks: 9 },
  { name: "Pump_P102_Cavitation_Troubleshooting.pdf", type: "检修规程", version: "v1.0", device: "P-102", source: "维保专家组", state: "部分失败", chunks: 11 },
];

export const auditRows = [
  { time: "09:44:00", user: "李振华", action: "确认告警", object: "Rule #VIB-RMS-004", result: "成功" },
  { time: "09:41:14", user: "李振华", action: "采纳证据", object: "Atlas_Copco_GX11.pdf", result: "成功" },
  { time: "09:42:03", user: "李振华", action: "解决参数冲突", object: "AC-07 额定排气压力", result: "成功" },
  { time: "09:44:55", user: "李振华", action: "确认诊断结论", object: "DIAG-20250518-0941", result: "成功" },
  { time: "09:46:12", user: "张工", action: "生成工单", object: "WO-20250518-01", result: "成功" },
];

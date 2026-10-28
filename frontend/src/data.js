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
  { id: "ALT-0909", level: "二级警告", title: "主轴电流波动持续扩大", device: "CNC-04 数控龙门铣床", time: "4 小时", owner: "赵工", status: "处理中" },
  { id: "ALT-0908", level: "二级警告", title: "减速箱油温超过预警线", device: "R-03 工业减速机", time: "5 小时", owner: "黄工", status: "待确认" },
  { id: "ALT-0907", level: "一级紧急", title: "机械密封泄漏量连续上升", device: "P-103 循环冷却泵", time: "6 小时", owner: "刘工", status: "处理中" },
  { id: "ALT-0906", level: "二级警告", title: "刀库定位时间偏离基线", device: "CNC-05 立式加工中心", time: "昨天", owner: "周工", status: "待确认" },
  { id: "ALT-0905", level: "三级提示", title: "皮带张力低于巡检建议值", device: "F-12 离心鼓风机", time: "昨天", owner: "吴工", status: "待确认" },
  { id: "ALT-0904", level: "三级提示", title: "排气温度短时波动已恢复", device: "AC-08 螺杆空气压缩机", time: "2 天前", owner: "张工", status: "已关闭" },
];

export const devices = [
  { id: "AC-07", name: "螺杆空气压缩机", type: "动力与流体机械", plant: "一号装配厂", location: "压缩站 Bay03", health: 72.4, state: "需关注", alert: 1 },
  { id: "P-102", name: "高压离心注水泵", type: "流体动力系统", plant: "一号装配厂", location: "冷却循环水站", health: 84.2, state: "需关注", alert: 1 },
  { id: "CNC-04", name: "数控龙门铣床", type: "精密加工单元", plant: "二号装配厂", location: "重载加工岛 #3", health: 41, state: "告警异常", alert: 2 },
  { id: "WR-09", name: "自动焊接机器人", type: "工业机器人", plant: "二号装配厂", location: "车身拼装线 #2", health: 98.2, state: "运行正常", alert: 0 },
  { id: "CV-01", name: "重型板链输送线", type: "仓储物流输送", plant: "一号装配厂", location: "物流转运通道", health: 95, state: "运行正常", alert: 0 },
  { id: "AC-08", name: "螺杆空气压缩机", type: "动力与流体机械", plant: "一号装配厂", location: "压缩站 Bay04", health: 94.3, state: "运行正常", alert: 0 },
  { id: "R-03", name: "工业减速机", type: "传动系统", plant: "二号装配厂", location: "输送线驱动段", health: 78.6, state: "需关注", alert: 1 },
  { id: "P-103", name: "循环冷却泵", type: "流体动力系统", plant: "一号装配厂", location: "冷却循环水站 B 线", health: 58.7, state: "告警异常", alert: 1 },
  { id: "CNC-05", name: "立式加工中心", type: "精密加工单元", plant: "二号装配厂", location: "精加工岛 #5", health: 81.5, state: "需关注", alert: 1 },
  { id: "F-12", name: "离心鼓风机", type: "动力与流体机械", plant: "二号装配厂", location: "表面处理风机房", health: 83.4, state: "需关注", alert: 1 },
];

export const deviceProfiles = {
  "AC-07": { updatedAt: "2026-10-23 09:42", metrics: [{ label: "驱动端振动 RMS", value: "7.82", unit: "mm/s", limit: "警戒 4.50", tone: "danger" }, { label: "排气温度", value: "88.5", unit: "°C", limit: "预警 85.0", tone: "warning" }, { label: "润滑油压差", value: "0.28", unit: "MPa", limit: "正常 0.20–0.35", tone: "success" }], series: [{ key: "vibration", label: "振动 mm/s", color: "#0f5a91" }, { key: "temperature", label: "温度 °C", color: "#d45522" }], trend: trendData, alertSummary: "驱动端振动持续超限，1 条待确认告警", documents: ["GX11 用户手册 RevC", "ISO 10816-3 振动标准"] },
  "P-102": { updatedAt: "2026-10-23 09:40", metrics: [{ label: "入口压力", value: "0.34", unit: "MPa", limit: "正常 0.28–0.40", tone: "success" }, { label: "出口压力", value: "6.18", unit: "MPa", limit: "额定 6.30", tone: "success" }, { label: "轴承温度", value: "76.2", unit: "°C", limit: "预警 75.0", tone: "warning" }], series: [{ key: "pressure", label: "出口压力 MPa", color: "#0f5a91" }, { key: "bearingTemperature", label: "轴承温度 °C", color: "#d45522" }], trend: [{ time: "08:00", pressure: 6.31, bearingTemperature: 68 }, { time: "08:30", pressure: 6.28, bearingTemperature: 70 }, { time: "09:00", pressure: 6.24, bearingTemperature: 73 }, { time: "09:40", pressure: 6.18, bearingTemperature: 76.2 }], alertSummary: "轴承温度接近阈值，1 条处理中告警", documents: ["P-102X 离心泵操作手册", "机械密封检修规程"] },
  "CNC-04": { updatedAt: "2026-10-23 09:38", metrics: [{ label: "主轴负载", value: "91.6", unit: "%", limit: "预警 85.0", tone: "danger" }, { label: "主轴转速", value: "6,200", unit: "rpm", limit: "程序设定 6,000", tone: "warning" }, { label: "冷却液温度", value: "24.8", unit: "°C", limit: "正常 20–28", tone: "success" }], series: [{ key: "spindleLoad", label: "主轴负载 %", color: "#0f5a91" }, { key: "coolantTemperature", label: "冷却液温度 °C", color: "#d45522" }], trend: [{ time: "08:00", spindleLoad: 62, coolantTemperature: 22.1 }, { time: "08:30", spindleLoad: 74, coolantTemperature: 23.2 }, { time: "09:00", spindleLoad: 88, coolantTemperature: 24.1 }, { time: "09:38", spindleLoad: 91.6, coolantTemperature: 24.8 }], alertSummary: "主轴负载异常，2 条待处理告警", documents: ["CNC-04 主轴维护手册", "加工中心点检规程"] },
  "WR-09": { updatedAt: "2026-10-23 09:41", metrics: [{ label: "焊接电流", value: "218", unit: "A", limit: "工艺 210–225", tone: "success" }, { label: "六轴扭矩", value: "42", unit: "%", limit: "正常 < 70", tone: "success" }, { label: "循环节拍", value: "48.2", unit: "s", limit: "目标 50.0", tone: "success" }], series: [{ key: "current", label: "焊接电流 A", color: "#0f5a91" }, { key: "cycle", label: "循环节拍 s", color: "#d45522" }], trend: [{ time: "08:00", current: 214, cycle: 49.2 }, { time: "08:30", current: 220, cycle: 48.8 }, { time: "09:00", current: 216, cycle: 48.5 }, { time: "09:41", current: 218, cycle: 48.2 }], alertSummary: "当前无活动告警", documents: ["WR-09 机器人维护手册"] },
  "CV-01": { updatedAt: "2026-10-23 09:39", metrics: [{ label: "链速", value: "12.4", unit: "m/min", limit: "设定 12.5", tone: "success" }, { label: "电机电流", value: "18.6", unit: "A", limit: "正常 < 24", tone: "success" }, { label: "张紧行程", value: "63", unit: "%", limit: "正常 40–75", tone: "success" }], series: [{ key: "speed", label: "链速 m/min", color: "#0f5a91" }, { key: "current", label: "电机电流 A", color: "#d45522" }], trend: [{ time: "08:00", speed: 12.3, current: 17.8 }, { time: "08:30", speed: 12.5, current: 18.2 }, { time: "09:00", speed: 12.4, current: 18.9 }, { time: "09:39", speed: 12.4, current: 18.6 }], alertSummary: "当前无活动告警", documents: ["CV-01 输送线保养规程"] },
  "AC-08": { updatedAt: "2026-10-28 09:38", metrics: [{ label: "排气压力", value: "0.77", unit: "MPa", limit: "正常 0.70–0.82", tone: "success" }, { label: "排气温度", value: "73.2", unit: "°C", limit: "预警 85.0", tone: "success" }, { label: "油分压差", value: "0.12", unit: "MPa", limit: "正常 < 0.20", tone: "success" }], series: [{ key: "pressure", label: "排气压力 MPa", color: "#0f5a91" }, { key: "temperature", label: "排气温度 °C", color: "#d45522" }], trend: [{ time: "08:00", pressure: 0.74, temperature: 70 }, { time: "08:30", pressure: 0.76, temperature: 71 }, { time: "09:00", pressure: 0.77, temperature: 72 }, { time: "09:38", pressure: 0.77, temperature: 73.2 }], alertSummary: "异常已关闭，运行稳定", documents: ["AC-08 定期保养记录"] },
  "R-03": { updatedAt: "2026-10-28 09:36", metrics: [{ label: "减速箱油温", value: "79.4", unit: "°C", limit: "预警 75.0", tone: "warning" }, { label: "输出轴振动", value: "3.9", unit: "mm/s", limit: "警戒 4.5", tone: "warning" }, { label: "润滑油位", value: "61", unit: "%", limit: "正常 45–80", tone: "success" }], series: [{ key: "oilTemperature", label: "油温 °C", color: "#0f5a91" }, { key: "vibration", label: "振动 mm/s", color: "#d45522" }], trend: [{ time: "08:00", oilTemperature: 70, vibration: 2.6 }, { time: "08:30", oilTemperature: 73, vibration: 2.9 }, { time: "09:00", oilTemperature: 76, vibration: 3.4 }, { time: "09:36", oilTemperature: 79.4, vibration: 3.9 }], alertSummary: "油温超预警，1 条待确认告警", documents: ["R-03 减速机润滑规程"] },
  "P-103": { updatedAt: "2026-10-28 09:35", metrics: [{ label: "密封泄漏量", value: "38", unit: "mL/h", limit: "警戒 25", tone: "danger" }, { label: "出口压力", value: "5.7", unit: "MPa", limit: "正常 5.8–6.4", tone: "warning" }, { label: "轴承温度", value: "68.5", unit: "°C", limit: "预警 75", tone: "success" }], series: [{ key: "leak", label: "泄漏量 mL/h", color: "#0f5a91" }, { key: "pressure", label: "出口压力 MPa", color: "#d45522" }], trend: [{ time: "08:00", leak: 12, pressure: 6.2 }, { time: "08:30", leak: 19, pressure: 6.1 }, { time: "09:00", leak: 28, pressure: 5.9 }, { time: "09:35", leak: 38, pressure: 5.7 }], alertSummary: "密封泄漏量超限，1 条处理中告警", documents: ["P-103 机械密封检查卡"] },
  "CNC-05": { updatedAt: "2026-10-28 09:37", metrics: [{ label: "刀库定位时间", value: "2.8", unit: "s", limit: "预警 2.5", tone: "warning" }, { label: "主轴电流", value: "22.4", unit: "A", limit: "正常 < 28", tone: "success" }, { label: "冷却液流量", value: "16.2", unit: "L/min", limit: "正常 15–20", tone: "success" }], series: [{ key: "positioning", label: "定位时间 s", color: "#0f5a91" }, { key: "current", label: "主轴电流 A", color: "#d45522" }], trend: [{ time: "08:00", positioning: 2.1, current: 20 }, { time: "08:30", positioning: 2.2, current: 20.7 }, { time: "09:00", positioning: 2.5, current: 21.5 }, { time: "09:37", positioning: 2.8, current: 22.4 }], alertSummary: "刀库定位变慢，1 条待确认告警", documents: ["CNC-05 刀库维护指南"] },
  "F-12": { updatedAt: "2026-10-28 09:34", metrics: [{ label: "皮带张力", value: "42", unit: "%", limit: "建议 50–70", tone: "warning" }, { label: "轴承温度", value: "61.3", unit: "°C", limit: "预警 72", tone: "success" }, { label: "风量", value: "8,400", unit: "m³/h", limit: "目标 8,600", tone: "warning" }], series: [{ key: "tension", label: "皮带张力 %", color: "#0f5a91" }, { key: "temperature", label: "轴承温度 °C", color: "#d45522" }], trend: [{ time: "08:00", tension: 56, temperature: 58 }, { time: "08:30", tension: 52, temperature: 59 }, { time: "09:00", tension: 47, temperature: 60 }, { time: "09:34", tension: 42, temperature: 61.3 }], alertSummary: "皮带张力偏低，1 条待确认告警", documents: ["F-12 风机传动检查规程"] },
};

const demoDate = (offset) => {
  const date = new Date();
  date.setDate(date.getDate() + offset);
  return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, "0")}-${String(date.getDate()).padStart(2, "0")}`;
};

export const workOrders = [
  { id: "WO-20250518-01", title: "AC-07 驱动端深沟球轴承紧急更换与润滑脂加注", deviceId: "AC-07", priority: "P1 紧急", owner: "张工", status: "处理中", startDate: demoDate(0), dueDate: demoDate(1), updated: "8 分钟前" },
  { id: "WO-20250518-02", title: "P-102 机械密封泄漏检查", deviceId: "P-102", priority: "P2 高", owner: "王强", status: "待验收", startDate: demoDate(0), dueDate: demoDate(2), updated: "25 分钟前" },
  { id: "WO-20250517-03", title: "CNC-04 主轴动平衡校准", deviceId: "CNC-04", priority: "P3 中", owner: "赵工", status: "待处理", startDate: demoDate(1), dueDate: demoDate(3), updated: "2 小时前" },
  { id: "WO-20250516-04", title: "AC-08 月度定检与油分滤芯检查", deviceId: "AC-08", priority: "P4 低", owner: "张工", status: "已完成", startDate: demoDate(-3), dueDate: demoDate(-2), updated: "2 天前" },
  { id: "WO-20250515-05", title: "CNC-04 主轴巡检（重复报修）", deviceId: "CNC-04", priority: "P3 中", owner: "赵工", status: "已取消", startDate: demoDate(-4), dueDate: demoDate(-3), updated: "3 天前", cancellationReason: "与 WO-20250517-03 为同一故障，已合并到该工单处理。" },
  { id: "WO-20250519-06", title: "R-03 减速箱油温复测与润滑油检查", deviceId: "R-03", priority: "P2 高", owner: "黄工", status: "待处理", startDate: demoDate(0), dueDate: demoDate(2), updated: "1 小时前" },
  { id: "WO-20250519-07", title: "P-103 机械密封泄漏处置", deviceId: "P-103", priority: "P1 紧急", owner: "刘工", status: "处理中", startDate: demoDate(0), dueDate: demoDate(1), updated: "2 小时前" },
  { id: "WO-20250519-08", title: "CNC-05 刀库定位传感器检查", deviceId: "CNC-05", priority: "P3 中", owner: "周工", status: "待处理", startDate: demoDate(1), dueDate: demoDate(4), updated: "3 小时前" },
  { id: "WO-20250519-09", title: "F-12 风机传动皮带张力调整", deviceId: "F-12", priority: "P2 高", owner: "吴工", status: "待验收", startDate: demoDate(-1), dueDate: demoDate(1), updated: "4 小时前" },
  { id: "WO-20250519-10", title: "CV-01 输送链张紧与润滑巡检", deviceId: "CV-01", priority: "P4 低", owner: "张工", status: "已完成", startDate: demoDate(-2), dueDate: demoDate(-1), updated: "昨天" },
];

export const evidence = [
  { name: "Atlas_Copco_GX11_UserManual_RevC.pdf", type: "技术说明书", version: "RevC", device: "AC-07", source: "演示资料（非官方原文）", state: "可用", chunks: 42, preview: "虚构演示摘录：驱动端振动持续升高时，应核对测点、转速与轴承润滑状态。" },
  { name: "ISO-10816-3_VibrationStandard.pdf", type: "行业标准", version: "2018", device: "工业回转设备", source: "演示资料（非标准原文）", state: "可用", chunks: 18, preview: "虚构演示摘录：振动阈值仅作界面示例；正式判定需使用企业适用标准与校准记录。" },
  { name: "AC07_DriveAssembly_MechanicalDrawing.dwg", type: "装配 CAD", version: "v2.1", device: "AC-07", source: "厂内演示资料", state: "可用", chunks: 9, preview: "虚构演示摘录：驱动端轴承座与联轴器位置用于现场检查定位。" },
  { name: "Pump_P102_Cavitation_Troubleshooting.pdf", type: "检修规程", version: "v1.0", device: "P-102", source: "厂内演示资料", state: "部分失败", chunks: 11, preview: "虚构演示摘录：机械密封检查应结合入口压力、出口压力与泄漏观察。" },
  { name: "AC08_Compressor_Monthly_Checklist.pdf", type: "检修规程", version: "v2.0", device: "AC-08", source: "厂内演示资料", state: "可用", chunks: 24, preview: "虚构演示摘要：月度点检依次记录油分压差、排气温度与滤芯更换时间。" },
  { name: "R03_Gearbox_Lubrication_Guide.pdf", type: "技术说明书", version: "v1.3", device: "R-03", source: "厂内演示资料", state: "可用", chunks: 31, preview: "虚构演示摘要：减速箱油温高于 75°C 时，复核油位与润滑油状态。" },
  { name: "P103_Seal_Inspection_Card.pdf", type: "检修规程", version: "v1.1", device: "P-103", source: "厂内演示资料", state: "可用", chunks: 19, preview: "虚构演示摘要：机械密封泄漏量持续上升时，先确认运行安全边界。" },
  { name: "CNC05_Tool_Magazine_Service.pdf", type: "技术说明书", version: "v2.2", device: "CNC-05", source: "厂内演示资料", state: "可用", chunks: 27, preview: "虚构演示摘要：刀库定位时间偏离基线时，检查传感器与气路状态。" },
  { name: "F12_Blower_Belt_Procedure.pdf", type: "检修规程", version: "v1.0", device: "F-12", source: "厂内演示资料", state: "可用", chunks: 22, preview: "虚构演示摘要：风机皮带张力低于建议值时，复核张紧机构并复测风量。" },
  { name: "CV01_Conveyor_Chain_Maintenance.pdf", type: "检修规程", version: "v1.5", device: "CV-01", source: "厂内演示资料", state: "可用", chunks: 16, preview: "虚构演示摘要：输送链润滑后检查链速和张紧行程，记录复测结果。" },
  { name: "CNC04_Spindle_Inspection_Demo.pdf", type: "检修规程", version: "v1.0", device: "CNC-04", source: "厂内演示资料", state: "可用", chunks: 14, preview: "虚构演示摘录：主轴负载与电流同时升高时，先复核加工程序、刀具磨损和冷却液状态。" },
  { name: "WR09_Robot_Service_Demo.pdf", type: "技术说明书", version: "v1.0", device: "WR-09", source: "厂内演示资料", state: "可用", chunks: 12, preview: "虚构演示摘录：焊接机器人日常点检应记录电流、六轴扭矩与循环节拍。" },
];

const demoAuditTime = (daysAgo, time) => {
  const date = new Date();
  date.setDate(date.getDate() - daysAgo);
  return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, "0")}-${String(date.getDate()).padStart(2, "0")} ${time}`;
};

export const auditRows = [
  { time: demoAuditTime(0, "09:46:12"), user: "张工", action: "生成工单", object: "WO-20250518-01", result: "成功" },
  { time: demoAuditTime(0, "09:44:55"), user: "李振华", action: "确认诊断结论", object: "DIAG-20250518-0941", result: "成功" },
  { time: demoAuditTime(0, "09:44:00"), user: "李振华", action: "确认告警", object: "ALT-0941", result: "成功" },
  { time: demoAuditTime(1, "16:25:08"), user: "王强", action: "提交验收", object: "WO-20250518-02", result: "成功" },
  { time: demoAuditTime(1, "10:42:03"), user: "李振华", action: "解决参数冲突", object: "AC-07 额定排气压力", result: "成功" },
  { time: demoAuditTime(2, "14:41:14"), user: "李振华", action: "采纳证据", object: "Atlas_Copco_GX11.pdf", result: "成功" },
  { time: demoAuditTime(4, "11:08:22"), user: "赵工", action: "接收工单", object: "WO-20250517-03", result: "成功" },
  { time: demoAuditTime(5, "15:16:02"), user: "李振华", action: "指派负责人", object: "WO-20250517-03 → 赵工", result: "成功" },
  { time: demoAuditTime(6, "08:52:33"), user: "张工", action: "完成点检", object: "AC-08 月度定检", result: "成功" },
  { time: demoAuditTime(9, "13:12:41"), user: "李振华", action: "取消重复工单", object: "WO-20250515-05", result: "成功" },
  { time: demoAuditTime(12, "09:32:10"), user: "王强", action: "确认告警", object: "ALT-0938", result: "成功" },
  { time: demoAuditTime(16, "17:24:55"), user: "张工", action: "更换油分滤芯", object: "AC-08", result: "成功" },
  { time: demoAuditTime(24, "10:02:09"), user: "李振华", action: "导入设备", object: "CV-01", result: "成功" },
  { time: demoAuditTime(35, "08:31:27"), user: "李振华", action: "创建告警规则", object: "Rule #VIB-RMS-004", result: "成功" },
];

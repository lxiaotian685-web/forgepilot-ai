export function buildMeasurementQuestion(deviceId, parameters) {
  if (!deviceId || !Array.isArray(parameters) || !parameters.length) throw new Error("该设备没有可用测点数据，无法生成诊断提问");
  const lines = parameters.slice(0, 20).map((item) => {
    if (!item.name || !Number.isFinite(Number(item.value))) return null;
    return `${item.name}：${item.value}${item.unit || ""}（采集时间 ${item.recordedAt || "未知"}，来源 ${item.source || "未知"}）`;
  }).filter(Boolean);
  if (!lines.length) throw new Error("测点缺少名称或数值，无法生成诊断提问");
  return `${deviceId} 当前设备测点：\n${lines.join("\n")}\n请结合该设备档案、适用文档和测点事实，判断哪些情况需要人工复核，并给出有来源的检查建议。没有阈值或工况依据时不要断言超限或故障。`;
}

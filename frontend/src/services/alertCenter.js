export function countAlerts(alerts) {
  return alerts.reduce((counts, alert) => ({ ...counts, all: counts.all + 1, [alert.status]: (counts[alert.status] || 0) + 1 }), { all: 0 });
}

export function filterAlerts(alerts, filters = {}) {
  const query = String(filters.query || "").trim().toLowerCase();
  return alerts.filter((alert) => {
    const matchesQuery = !query || [alert.id, alert.title, alert.device, alert.owner].some((value) => String(value || "").toLowerCase().includes(query));
    return matchesQuery
      && (!filters.status || alert.status === filters.status)
      && (!filters.level || alert.level === filters.level)
      && (!filters.owner || alert.owner === filters.owner)
      && (!filters.device || alert.device === filters.device);
  });
}

const allowedTransitions = { "待确认": ["处理中"], "处理中": ["已关闭"], "已关闭": [] };

export function transitionAlert(alert, nextStatus, owner) {
  if (!allowedTransitions[alert.status]?.includes(nextStatus)) throw new Error(`不能从“${alert.status}”变更为“${nextStatus}”`);
  if (nextStatus === "处理中" && (!owner || owner === "未指派")) throw new Error("进入处理中前必须指定负责人");
  return { ...alert, status: nextStatus, owner: owner || alert.owner };
}

export function alertDeviceId(alert) {
  return String(alert?.device || "").split(/\s+/)[0] || "";
}

export function updateAlert(alert, changes) {
  const title = changes.title?.trim();
  const level = changes.level?.trim();
  const owner = changes.owner?.trim();
  if (!title) throw new Error("告警标题不能为空");
  if (!level) throw new Error("请选择告警等级");
  if (!owner) throw new Error("请选择负责人");
  return { ...alert, ...changes, title, level, owner, updated: "刚刚" };
}

export function reopenAlert(alert) {
  if (alert.status !== "已关闭") throw new Error("只有已关闭告警可以重新打开");
  return { ...alert, status: "处理中", updated: "刚刚" };
}

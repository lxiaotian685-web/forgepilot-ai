export const WORK_ORDER_TRANSITIONS = {
  待处理: ["处理中", "已取消"],
  处理中: ["待验收", "已取消"],
  待验收: ["已完成", "处理中"],
  已完成: [],
  已取消: [],
};

export function normalizeWorkOrder(order, index = 0) {
  const deviceId = order.deviceId || order.title?.match(/[A-Z]+-\d+/)?.[0] || "未关联";
  return {
    description: "",
    dueDate: `2026-10-${String(25 + (index % 5)).padStart(2, "0")}`,
    draft: false,
    checklist: [false, false, false],
    ...order,
    deviceId,
  };
}

export function filterWorkOrders(orders, filters = {}) {
  const query = filters.query?.trim().toLowerCase();
  return orders.filter((order) => {
    if (filters.status && order.status !== filters.status) return false;
    if (filters.priority && order.priority !== filters.priority) return false;
    if (filters.owner && order.owner !== filters.owner) return false;
    if (!query) return true;
    return [order.id, order.title, order.deviceId, order.owner].some((value) => String(value || "").toLowerCase().includes(query));
  });
}

export function transitionWorkOrder(order, nextStatus, reason = "") {
  if (!WORK_ORDER_TRANSITIONS[order.status]?.includes(nextStatus)) throw new Error(`工单不能从${order.status}流转到${nextStatus}`);
  if (nextStatus === "已取消" && !reason.trim()) throw new Error("取消正式工单必须填写原因");
  return { ...order, status: nextStatus, cancellationReason: nextStatus === "已取消" ? reason.trim() : order.cancellationReason, updated: "刚刚" };
}

export function canDeleteWorkOrder(order) {
  return Boolean(order?.draft);
}

export function validateWorkOrder(form) {
  const errors = {};
  if (!form.title?.trim()) errors.title = "请输入工单标题";
  if (!form.deviceId) errors.deviceId = "请选择设备";
  if (!form.owner) errors.owner = "请选择负责人";
  if (!form.dueDate) errors.dueDate = "请选择计划日期";
  return errors;
}

export const WORK_ORDER_TRANSITIONS = {
  待处理: ["处理中", "已取消"],
  处理中: ["待验收", "已取消"],
  待验收: ["已完成", "处理中"],
  已完成: [],
  已取消: [],
};

export function normalizeWorkOrder(order) {
  const deviceId = order.deviceId || order.title?.match(/[A-Z]+-\d+/)?.[0] || "未关联";
  return {
    description: "",
    dueDate: order.dueDate || order.dueAt?.slice(0, 10) || "",
    draft: false,
    checklist: [false, false, false],
    ...order,
    deviceId,
  };
}

export function openOrdersFor(orders, owner) {
  return orders.filter((order) => order.owner === owner && !["已完成", "已取消"].includes(order.status));
}

export function reassignOwner(orders, from, to) {
  if (!to || from === to) throw new Error("请选择另一位在岗接收人");
  return orders.map((order) => order.owner === from && !["已完成", "已取消"].includes(order.status)
    ? { ...order, owner: to, updated: "刚刚" }
    : order);
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
  if (nextStatus === "待验收" && order.checklist?.some((done) => !done)) throw new Error("请先完成全部现场执行步骤，再提交验收");
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

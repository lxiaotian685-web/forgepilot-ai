import { useEffect, useMemo, useState } from "react";
import { Button, Input } from "@fluentui/react-components";
import { filterWorkOrders, formatWorkOrderSchedule, normalizeWorkOrder, validateWorkOrder, WORK_ORDER_TRANSITIONS } from "./services/workOrderLifecycle.js";
import { listMembers, memberRoleLabels } from "./services/members.js";
import { createWorkOrder, listWorkOrders, patchWorkOrder } from "./services/workOrdersApi.js";

const priorities = ["P1 紧急", "P2 高", "P3 中", "P4 低"];
const roleRank = { viewer: 0, technician: 1, manager: 2, admin: 3, owner: 4 };
const blank = { title: "", description: "", deviceId: "", ownerId: "", priority: "P3 中", startDate: "", dueDate: "" };
const normalize = (order) => normalizeWorkOrder(order);

export default function ApiWorkOrdersPage({ session, devices, sourceAlert, notify, onLogout, onChanged }) {
  const [items, setItems] = useState([]);
  const [members, setMembers] = useState([]);
  const [selectedId, setSelectedId] = useState("");
  const [view, setView] = useState("list");
  const [filters, setFilters] = useState({ query: "", status: "", priority: "", owner: "" });
  const [draft, setDraft] = useState(null);
  const [cancelReason, setCancelReason] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const canManage = roleRank[session.role] >= roleRank.manager;
  const canExecute = roleRank[session.role] >= roleRank.technician;

  const refresh = async () => {
    const orders = (await listWorkOrders(session.accessToken)).map(normalize);
    setItems(orders);
    setSelectedId((current) => orders.some((order) => order.id === current) ? current : (orders[0]?.id || ""));
    setError("");
  };
  useEffect(() => {
    let active = true;
    Promise.all([listWorkOrders(session.accessToken), canManage ? listMembers(session.accessToken) : Promise.resolve([])])
      .then(([orders, people]) => {
        if (!active) return;
        const mapped = orders.map(normalize);
        setItems(mapped);
        setSelectedId(mapped[0]?.id || "");
        setMembers(people.filter((person) => person.status === "active" && roleRank[person.role] >= roleRank.technician));
      }).catch((failure) => {
        if (!active) return;
        if (failure.status === 401) onLogout("登录已失效，请重新登录");
        else setError(failure.message);
      });
    return () => { active = false; };
  }, [session.accessToken, canManage]);

  const filtered = useMemo(() => filterWorkOrders(items, filters), [items, filters]);
  const selected = filtered.find((order) => order.id === selectedId) || filtered[0];
  const owners = [...new Set(items.map((order) => order.owner).filter(Boolean))];
  const perform = async (action, success) => {
    setBusy(true);
    try { await action(); }
    catch (failure) {
      if (failure.status === 401) onLogout("登录已失效，请重新登录");
      else notify(failure.message);
      setBusy(false);
      return false;
    }
    try { await refresh(); await onChanged?.(); }
    catch (failure) { setError(`已保存，但刷新失败：${failure.message}`); }
    setBusy(false);
    notify(success);
    return true;
  };

  const save = async () => {
    const errors = validateWorkOrder({ ...draft, owner: draft.ownerId });
    if (Object.keys(errors).length) return notify(Object.values(errors)[0]);
    const plannedStartAt = new Date(`${draft.startDate}T12:00:00`).toISOString();
    const dueAt = new Date(`${draft.dueDate}T12:00:00`).toISOString();
    const payload = { title: draft.title.trim(), description: draft.description, priority: draft.priority,
      ownerId: draft.ownerId, plannedStartAt, dueAt, ...(!draft.id ? { deviceId: draft.deviceId, ...(sourceAlert ? { alertId: sourceAlert.id } : {}) } : {}) };
    const okay = await perform(() => draft.id ? patchWorkOrder(session.accessToken, draft.id, payload) : createWorkOrder(session.accessToken, payload),
      draft.id ? "工单修改已保存到服务器" : "工单已创建并写入服务器审计");
    if (okay) setDraft(null);
  };
  const move = async (status) => {
    if (!selected) return;
    if (!canManage && selected.ownerId !== session.user?.id && selected.ownerId !== session.userId) return notify("只能处理指派给自己的工单");
    if (!canManage && ["已完成", "已取消"].includes(status)) return notify("验收和取消工单需要主管权限");
    if (status === "已取消" && !cancelReason.trim()) return notify("取消工单必须填写原因");
    if (status === "已完成" && !window.confirm(`确认 ${selected.id} 已完成并通过验收？`)) return;
    const okay = await perform(() => patchWorkOrder(session.accessToken, selected.id,
      { status, ...(status === "已取消" ? { cancelReason: cancelReason.trim() } : {}) }), `${selected.id} 已更新为${status}`);
    if (okay) setCancelReason("");
  };

  return <>
    <div className="page-heading"><div><h1>维护工单</h1><p>创建、指派、执行与验收当前组织的维修任务</p></div><div><span className="tone-badge tone-success">服务器数据</span>{canManage && <Button appearance="primary" onClick={() => setDraft({ ...blank, deviceId: sourceAlert?.deviceId || "", title: sourceAlert?.title || "" })}>创建工单</Button>}</div></div>
    {sourceAlert && <div className="context-note">来源告警 {sourceAlert.id} · {sourceAlert.device} · {sourceAlert.title}</div>}
    <div className="status-tabs">{[["list", "列表视图"], ["board", "看板视图"], ["calendar", "日历排程"]].map(([id, label]) => <button key={id} className={view === id ? "active" : ""} onClick={() => setView(id)}>{label}</button>)}</div>
    <div className="toolbar"><Input className="search-input" placeholder="搜索工单、设备或负责人" value={filters.query} onChange={(_, data) => setFilters((current) => ({ ...current, query: data.value }))} /><select aria-label="状态" value={filters.status} onChange={(event) => setFilters((current) => ({ ...current, status: event.target.value }))}><option value="">全部状态</option>{Object.keys(WORK_ORDER_TRANSITIONS).map((status) => <option key={status}>{status}</option>)}</select><select aria-label="优先级" value={filters.priority} onChange={(event) => setFilters((current) => ({ ...current, priority: event.target.value }))}><option value="">全部优先级</option>{priorities.map((priority) => <option key={priority}>{priority}</option>)}</select><select aria-label="负责人" value={filters.owner} onChange={(event) => setFilters((current) => ({ ...current, owner: event.target.value }))}><option value="">全部负责人</option>{owners.map((owner) => <option key={owner}>{owner}</option>)}</select><Button onClick={() => setFilters({ query: "", status: "", priority: "", owner: "" })}>重置</Button><Button disabled={busy} onClick={() => refresh().catch((failure) => setError(failure.message))}>刷新</Button></div>
    {error && <p role="alert">{error}</p>}
    {view === "board" && <div className="work-board">{Object.keys(WORK_ORDER_TRANSITIONS).map((status) => <section className="panel" key={status}><h3>{status}<small>{filtered.filter((order) => order.status === status).length}</small></h3>{filtered.filter((order) => order.status === status).map((order) => <button key={order.id} onClick={() => { setSelectedId(order.id); setView("list"); }}><strong>{order.title}</strong><span>{order.deviceId} · {order.owner || "未指派"}</span><small>{order.priority} · {formatWorkOrderSchedule(order)}</small></button>)}</section>)}</div>}
    {view === "calendar" && <div className="panel schedule-view">{[...filtered].sort((a, b) => (a.dueDate || "9999").localeCompare(b.dueDate || "9999")).map((order) => <button key={order.id} onClick={() => { setSelectedId(order.id); setView("list"); }}><time>{formatWorkOrderSchedule(order)}</time><span><strong>{order.title}</strong><small>{order.deviceId} · {order.owner || "未指派"} · {order.status}</small></span></button>)}</div>}
    {view === "list" && <div className="split-layout orders-layout"><section className="panel order-list">{filtered.map((order) => <button key={order.id} className={`order-card ${selected?.id === order.id ? "selected" : ""}`} onClick={() => setSelectedId(order.id)}><span><strong>{order.id}</strong><em>{order.priority}</em></span><h3>{order.title}</h3><small>{order.deviceId} · {order.owner || "未指派"} · {order.status} · {formatWorkOrderSchedule(order)}</small></button>)}{!filtered.length && <div className="alert-empty">没有符合条件的工单</div>}</section>
      {selected && <section className="panel order-detail"><div className="drawer-heading"><div><small>{selected.id}</small><h2>{selected.title}</h2></div>{canManage && !["已完成", "已取消"].includes(selected.status) && <Button onClick={() => setDraft({ ...selected })}>编辑</Button>}</div><div className="order-meta"><div><span>负责人</span><strong>{selected.owner || "未指派"}</strong></div><div><span>目标设备</span><strong>{selected.deviceId}</strong></div><div><span>计划日期</span><strong>{formatWorkOrderSchedule(selected)}</strong></div></div><p>{selected.description || "暂无作业说明"}</p><div className="lifecycle-actions">{canExecute && (canManage || selected.ownerId === (session.user?.id || session.userId)) && (WORK_ORDER_TRANSITIONS[selected.status] || []).filter((status) => canManage || !["已取消", "已完成"].includes(status)).map((status) => <Button key={status} appearance="primary" disabled={busy} onClick={() => move(status)}>{status === "处理中" ? "开始或退回处理" : status === "待验收" ? "提交验收" : "验收完成"}</Button>)}{canManage && (WORK_ORDER_TRANSITIONS[selected.status] || []).includes("已取消") && <><Input placeholder="填写取消原因" value={cancelReason} onChange={(_, data) => setCancelReason(data.value)} /><Button disabled={busy} onClick={() => move("已取消")}>取消工单</Button></>}</div><p className="boundary-note">正式工单不删除；状态和取消原因保存到服务器审计。</p></section>}</div>}
    {draft && <div className="modal-backdrop" role="presentation"><section className="panel work-order-form"><div className="form-heading"><h2>{draft.id ? `编辑 ${draft.id}` : "创建维修工单"}</h2><Button onClick={() => setDraft(null)}>关闭</Button></div><label>标题<Input value={draft.title} onChange={(_, data) => setDraft((current) => ({ ...current, title: data.value }))} /></label><div className="form-grid"><label>设备<select value={draft.deviceId} disabled={Boolean(draft.id)} onChange={(event) => setDraft((current) => ({ ...current, deviceId: event.target.value }))}><option value="">请选择</option>{devices.map((device) => <option key={device.id} value={device.id}>{device.id} · {device.name}</option>)}</select></label><label>负责人<select value={draft.ownerId || ""} onChange={(event) => setDraft((current) => ({ ...current, ownerId: event.target.value }))}><option value="">请选择</option>{members.map((person) => <option key={person.id} value={person.id}>{person.displayName} · {memberRoleLabels[person.role]}</option>)}</select></label></div><label>优先级<select value={draft.priority} onChange={(event) => setDraft((current) => ({ ...current, priority: event.target.value }))}>{priorities.map((priority) => <option key={priority}>{priority}</option>)}</select></label><div className="form-grid schedule-range"><label>计划开始日期<input type="date" value={draft.startDate || ""} max={draft.dueDate || undefined} onChange={(event) => setDraft((current) => ({ ...current, startDate: event.target.value }))} /></label><label>计划结束日期<input type="date" value={draft.dueDate || ""} min={draft.startDate || undefined} onChange={(event) => setDraft((current) => ({ ...current, dueDate: event.target.value }))} /></label></div><label>问题与作业说明<textarea value={draft.description || ""} onChange={(event) => setDraft((current) => ({ ...current, description: event.target.value }))} /></label><div className="form-actions"><Button onClick={() => setDraft(null)}>取消</Button><Button appearance="primary" disabled={busy} onClick={save}>保存到服务器</Button></div></section></div>}
  </>;
}

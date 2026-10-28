import { useMemo, useState } from "react";
import { Button, Input } from "@fluentui/react-components";
import { Add24Regular, Delete24Regular, Edit24Regular } from "@fluentui/react-icons";
import BelowSelect from "./BelowSelect.jsx";
import { canDeleteWorkOrder, filterWorkOrders, formatWorkOrderSchedule, normalizeWorkOrder, transitionWorkOrder, validateWorkOrder, WORK_ORDER_TRANSITIONS } from "./services/workOrderLifecycle.js";

const priorities = ["P1 紧急", "P2 高", "P3 中", "P4 低"];
const blankForm = { title: "", description: "", deviceId: "", owner: "", priority: "P3 中", startDate: "", dueDate: "" };

function WorkOrderForm({ initial, devices, owners, onSave, onClose }) {
  const [form, setForm] = useState(initial || blankForm);
  const [errors, setErrors] = useState({});
  const change = (key, value) => setForm((current) => ({ ...current, [key]: value }));
  const submit = (event) => {
    event.preventDefault();
    const nextErrors = validateWorkOrder(form);
    setErrors(nextErrors);
    if (!Object.keys(nextErrors).length) onSave(form);
  };
  return <div className="modal-backdrop" role="presentation"><form className="panel work-order-form" onSubmit={submit} aria-label={initial ? "编辑工单" : "创建工单"}>
    <div className="form-heading"><div><small>{initial?.id ? "EDIT WORK ORDER" : "NEW WORK ORDER"}</small><h2>{initial?.id ? `编辑 ${initial.id}` : "创建维修工单"}</h2></div><Button type="button" appearance="subtle" onClick={onClose}>关闭</Button></div>
    <label>工单标题<Input value={form.title} onChange={(_, data) => change("title", data.value)} />{errors.title && <em>{errors.title}</em>}</label>
    <div className="form-grid"><label>目标设备<BelowSelect value={form.deviceId} onChange={(value) => change("deviceId", value)} options={[{ value: "", label: "请选择" }, ...devices.map((d) => ({ value: d.id, label: `${d.id} · ${d.name}` }))]} />{errors.deviceId && <em>{errors.deviceId}</em>}</label><label>负责人<BelowSelect value={form.owner} onChange={(value) => change("owner", value)} options={[{ value: "", label: "请选择" }, ...owners.map((name) => ({ value: name, label: name }))]} />{errors.owner && <em>{errors.owner}</em>}</label></div>
    <label>优先级<BelowSelect value={form.priority} onChange={(value) => change("priority", value)} options={priorities.map((priority) => ({ value: priority, label: priority }))} /></label>
    <div className="form-grid schedule-range"><label>计划开始日期<input type="date" value={form.startDate || ""} max={form.dueDate || undefined} onChange={(e) => change("startDate", e.target.value)} />{errors.startDate && <em>{errors.startDate}</em>}</label><label>计划结束日期<input type="date" value={form.dueDate || ""} min={form.startDate || undefined} onChange={(e) => change("dueDate", e.target.value)} />{errors.dueDate && <em>{errors.dueDate}</em>}</label></div>
    <label>问题与作业说明<textarea value={form.description} onChange={(e) => change("description", e.target.value)} placeholder="记录故障现象、作业要求和安全注意事项" /></label>
    <div className="form-actions"><Button type="button" onClick={onClose}>取消</Button><Button type="submit" appearance="primary">保存工单</Button></div>
  </form></div>;
}

export default function WorkOrdersPage({ notify, orders, onOrdersChange, devices, people, sourceAlert }) {
  const items = orders;
  const setItems = (updater) => onOrdersChange(typeof updater === "function" ? updater(items) : updater);
  const owners = people.filter((person) => person.status === "在岗").map((person) => person.name);
  const [selectedId, setSelectedId] = useState(items[0]?.id);
  const [view, setView] = useState("list");
  const [filters, setFilters] = useState({ query: "", status: "", priority: "", owner: "" });
  const [editing, setEditing] = useState(null);
  const [cancelReason, setCancelReason] = useState("");
  const filtered = useMemo(() => filterWorkOrders(items, filters), [items, filters]);
  const selected = filtered.find((item) => item.id === selectedId) || filtered[0];
  const save = (form) => {
    if (editing?.id) setItems((current) => current.map((item) => item.id === editing.id ? { ...item, ...form, updated: "刚刚" } : item));
    else {
      const order = normalizeWorkOrder({ ...form, id: `DRAFT-${String(Date.now()).slice(-6)}`, status: "待处理", updated: "刚刚", draft: true });
      setItems((current) => [order, ...current]); setSelectedId(order.id);
    }
    setEditing(null); notify(editing?.id ? "工单修改已保留在本次会话" : "本地草稿已创建，尚未提交服务器");
  };
  const move = (status) => { try { const next = transitionWorkOrder(selected, status, cancelReason); setItems((current) => current.map((item) => item.id === next.id ? next : item)); setCancelReason(""); notify(`${selected.id} 在本次会话中已更新为${status}`); } catch (error) { notify(error.message); } };
  const removeDraft = () => { if (!canDeleteWorkOrder(selected)) return notify("正式工单不可删除，请使用取消并保留审计记录"); if (window.confirm(`确认删除草稿 ${selected.id}？此操作不可撤销。`)) { setItems((current) => current.filter((item) => item.id !== selected.id)); setSelectedId(""); notify("草稿已删除"); } };
  const toggleStep = (index) => setItems((current) => current.map((item) => item.id === selected.id ? { ...item, checklist: item.checklist.map((done, i) => i === index ? !done : done) } : item));
  const showDetail = (id) => { setSelectedId(id); setView("list"); };

  return <>
    <div className="page-heading"><div><h1>维护工单</h1><p>创建、指派、执行、验收并保留完整维修轨迹</p></div><Button appearance="primary" icon={<Add24Regular />} onClick={() => setEditing(blankForm)}>创建工单</Button></div>
    {sourceAlert && <div className="context-note"><strong>由告警中心带入：{sourceAlert.id}</strong><span>{sourceAlert.device} · {sourceAlert.title}</span></div>}
    <div className="status-tabs">{[["list","列表视图"],["board","看板视图"],["calendar","日历排程"]].map(([id,label]) => <button key={id} className={view === id ? "active" : ""} onClick={() => setView(id)}>{label}</button>)}</div>
    <div className="toolbar"><Input className="search-input" placeholder="搜索工单号、标题、设备或负责人" value={filters.query} onChange={(_, d) => setFilters((f) => ({...f, query:d.value}))}/><BelowSelect value={filters.status} onChange={(status) => setFilters((f) => ({ ...f, status }))} options={[{ value: "", label: "全部状态" }, ...Object.keys(WORK_ORDER_TRANSITIONS).map((value) => ({ value, label: value }))]} /><BelowSelect value={filters.priority} onChange={(priority) => setFilters((f) => ({ ...f, priority }))} options={[{ value: "", label: "全部优先级" }, ...priorities.map((value) => ({ value, label: value }))]} /><BelowSelect value={filters.owner} onChange={(owner) => setFilters((f) => ({ ...f, owner }))} options={[{ value: "", label: "全部负责人" }, ...owners.map((value) => ({ value, label: value }))]} /><Button onClick={()=>setFilters({query:"",status:"",priority:"",owner:""})}>重置</Button></div>
    {view === "board" && <div className="work-board">{Object.keys(WORK_ORDER_TRANSITIONS).map((status)=><section className="panel" key={status}><h3>{status}<small>{filtered.filter((o)=>o.status===status).length}</small></h3>{filtered.filter((o)=>o.status===status).map((o)=><button key={o.id} onClick={()=>showDetail(o.id)}><strong>{o.title}</strong><span>{o.deviceId} · {o.owner}</span><small>{o.priority} · {formatWorkOrderSchedule(o)} · 点击查看详情</small></button>)}</section>)}</div>}
    {view === "calendar" && <div className="panel schedule-view">{[...filtered].sort((a,b)=>(a.dueDate || "9999").localeCompare(b.dueDate || "9999")).map((o)=><button key={o.id} onClick={()=>showDetail(o.id)}><time>{formatWorkOrderSchedule(o)}</time><span><strong>{o.title}</strong><small>{o.deviceId} · {o.owner} · {o.status} · 点击查看详情</small></span></button>)}</div>}
    {view === "list" && <div className="split-layout orders-layout"><section className="panel order-list">{filtered.map((order)=><button key={order.id} className={`order-card ${selected?.id===order.id?"selected":""}`} onClick={()=>setSelectedId(order.id)}><span><strong>{order.id}</strong><em>{order.priority}</em></span><h3>{order.title}</h3><small>{order.deviceId} · {order.owner} · {order.status} · {formatWorkOrderSchedule(order)}</small></button>)}{!filtered.length&&<div className="alert-empty">没有符合条件的工单</div>}</section>{selected&&<section className="panel order-detail"><div className="drawer-heading"><div><small>{selected.id}{selected.draft?" · 本地草稿":""}</small><h2>{selected.title}</h2></div><div className="detail-actions"><Button icon={<Edit24Regular/>} onClick={()=>setEditing(selected)} disabled={["已完成","已取消"].includes(selected.status)}>编辑</Button>{selected.draft&&<Button icon={<Delete24Regular/>} onClick={removeDraft}>删除草稿</Button>}</div></div><div className="order-meta"><div><span>负责人</span><strong>{selected.owner}</strong></div><div><span>目标设备</span><strong>{selected.deviceId}</strong></div><div><span>计划日期</span><strong>{formatWorkOrderSchedule(selected)}</strong></div></div><p className="order-description">{selected.description||"暂未填写作业说明。"}</p>{selected.status === "已取消" && selected.cancellationReason && <p className="boundary-note">取消原因：{selected.cancellationReason}</p>}<h3>现场执行清单</h3><div className="checklist">{["落实停机与上锁挂牌","完成故障检修并留存照片","复测指标并填写维修结论"].map((step,index)=><label key={step} className={selected.checklist[index]?"checked":""}><input type="checkbox" checked={selected.checklist[index]} disabled={selected.draft || ["已完成","已取消"].includes(selected.status)} onChange={()=>toggleStep(index)}/><span><strong>步骤 {index+1}：{step}</strong><small>{selected.checklist[index]?"已完成":"等待执行"}</small></span></label>)}</div><div className="lifecycle-actions">{!selected.draft&&WORK_ORDER_TRANSITIONS[selected.status].filter((s)=>s!=="已取消").map((status)=><Button key={status} appearance="primary" onClick={()=>move(status)}>{status==="处理中"?"开始处理":status==="待验收"?"提交验收":status==="已完成"?"验收通过":"退回处理中"}</Button>)}{!selected.draft&&WORK_ORDER_TRANSITIONS[selected.status].includes("已取消")&&<><Input placeholder="填写取消原因" value={cancelReason} onChange={(_,d)=>setCancelReason(d.value)}/><Button onClick={()=>move("已取消")}>取消工单</Button></>}</div><p className="boundary-note">{selected.draft?"本地草稿尚未下发，不能开始现场处理。":"正式工单保留历史记录；本页更改仅在当前会话中生效。"}</p></section>}</div>}
    {editing&&<WorkOrderForm initial={editing===blankForm?{...blankForm,deviceId:sourceAlert?.device?.split(" ")[0]||"",title:sourceAlert?.title||""}:editing} devices={devices} owners={owners} onSave={save} onClose={()=>setEditing(null)}/>}
  </>;
}

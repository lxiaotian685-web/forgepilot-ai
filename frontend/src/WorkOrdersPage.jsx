import { useMemo, useState } from "react";
import { Button, Input } from "@fluentui/react-components";
import { Add24Regular, Delete24Regular, Edit24Regular } from "@fluentui/react-icons";
import { canDeleteWorkOrder, filterWorkOrders, normalizeWorkOrder, transitionWorkOrder, validateWorkOrder, WORK_ORDER_TRANSITIONS } from "./services/workOrderLifecycle.js";

const owners = ["张工", "王强", "赵工"];
const priorities = ["P1 紧急", "P2 高", "P3 中", "P4 低"];
const blankForm = { title: "", description: "", deviceId: "", owner: "", priority: "P3 中", dueDate: "" };

function WorkOrderForm({ initial, devices, onSave, onClose }) {
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
    <div className="form-heading"><div><small>{initial ? "EDIT WORK ORDER" : "NEW WORK ORDER"}</small><h2>{initial ? `编辑 ${initial.id}` : "创建维修工单"}</h2></div><Button type="button" appearance="subtle" onClick={onClose}>关闭</Button></div>
    <label>工单标题<Input value={form.title} onChange={(_, data) => change("title", data.value)} />{errors.title && <em>{errors.title}</em>}</label>
    <div className="form-grid"><label>目标设备<select value={form.deviceId} onChange={(e) => change("deviceId", e.target.value)}><option value="">请选择</option>{devices.map((d) => <option key={d.id} value={d.id}>{d.id} · {d.name}</option>)}</select>{errors.deviceId && <em>{errors.deviceId}</em>}</label><label>负责人<select value={form.owner} onChange={(e) => change("owner", e.target.value)}><option value="">请选择</option>{owners.map((v) => <option key={v}>{v}</option>)}</select>{errors.owner && <em>{errors.owner}</em>}</label></div>
    <div className="form-grid"><label>优先级<select value={form.priority} onChange={(e) => change("priority", e.target.value)}>{priorities.map((v) => <option key={v}>{v}</option>)}</select></label><label>计划日期<input type="date" value={form.dueDate} onChange={(e) => change("dueDate", e.target.value)} />{errors.dueDate && <em>{errors.dueDate}</em>}</label></div>
    <label>问题与作业说明<textarea value={form.description} onChange={(e) => change("description", e.target.value)} placeholder="记录故障现象、作业要求和安全注意事项" /></label>
    <div className="form-actions"><Button type="button" onClick={onClose}>取消</Button><Button type="submit" appearance="primary">保存工单</Button></div>
  </form></div>;
}

export default function WorkOrdersPage({ notify, workOrders, devices, sourceAlert }) {
  const [items, setItems] = useState(() => workOrders.map(normalizeWorkOrder));
  const [selectedId, setSelectedId] = useState(items[0]?.id);
  const [view, setView] = useState("list");
  const [filters, setFilters] = useState({ query: "", status: "", priority: "", owner: "" });
  const [editing, setEditing] = useState(null);
  const [cancelReason, setCancelReason] = useState("");
  const filtered = useMemo(() => filterWorkOrders(items, filters), [items, filters]);
  const selected = items.find((item) => item.id === selectedId) || filtered[0];
  const save = (form) => {
    if (editing?.id) setItems((current) => current.map((item) => item.id === editing.id ? { ...item, ...form, updated: "刚刚" } : item));
    else {
      const order = normalizeWorkOrder({ ...form, id: `DRAFT-${String(Date.now()).slice(-6)}`, status: "待处理", updated: "刚刚", draft: true });
      setItems((current) => [order, ...current]); setSelectedId(order.id);
    }
    setEditing(null); notify(editing?.id ? "工单修改已保存" : "本地草稿已创建；提交服务器等待正式创建接口联调");
  };
  const move = (status) => { try { const next = transitionWorkOrder(selected, status, cancelReason); setItems((current) => current.map((item) => item.id === next.id ? next : item)); setCancelReason(""); notify(`${selected.id} 已更新为${status}`); } catch (error) { notify(error.message); } };
  const removeDraft = () => { if (!canDeleteWorkOrder(selected)) return notify("正式工单不可删除，请使用取消并保留审计记录"); if (window.confirm(`确认删除草稿 ${selected.id}？此操作不可撤销。`)) { setItems((current) => current.filter((item) => item.id !== selected.id)); setSelectedId(""); notify("草稿已删除"); } };
  const toggleStep = (index) => setItems((current) => current.map((item) => item.id === selected.id ? { ...item, checklist: item.checklist.map((done, i) => i === index ? !done : done) } : item));

  return <>
    <div className="page-heading"><div><h1>维护工单</h1><p>创建、指派、执行、验收并保留完整维修轨迹</p></div><Button appearance="primary" icon={<Add24Regular />} onClick={() => setEditing(blankForm)}>创建工单</Button></div>
    {sourceAlert && <div className="context-note"><strong>由告警中心带入：{sourceAlert.id}</strong><span>{sourceAlert.device} · {sourceAlert.title}</span></div>}
    <div className="status-tabs">{[["list","列表视图"],["board","看板视图"],["calendar","日历排程"]].map(([id,label]) => <button key={id} className={view === id ? "active" : ""} onClick={() => setView(id)}>{label}</button>)}</div>
    <div className="toolbar"><Input className="search-input" placeholder="搜索工单号、标题、设备或负责人" value={filters.query} onChange={(_, d) => setFilters((f) => ({...f, query:d.value}))}/><select value={filters.status} onChange={(e) => setFilters((f) => ({...f,status:e.target.value}))}><option value="">全部状态</option>{Object.keys(WORK_ORDER_TRANSITIONS).map((v)=><option key={v}>{v}</option>)}</select><select value={filters.priority} onChange={(e)=>setFilters((f)=>({...f,priority:e.target.value}))}><option value="">全部优先级</option>{priorities.map((v)=><option key={v}>{v}</option>)}</select><select value={filters.owner} onChange={(e)=>setFilters((f)=>({...f,owner:e.target.value}))}><option value="">全部负责人</option>{owners.map((v)=><option key={v}>{v}</option>)}</select><Button onClick={()=>setFilters({query:"",status:"",priority:"",owner:""})}>重置</Button></div>
    {view === "board" && <div className="work-board">{Object.keys(WORK_ORDER_TRANSITIONS).map((status)=><section className="panel" key={status}><h3>{status}<small>{filtered.filter((o)=>o.status===status).length}</small></h3>{filtered.filter((o)=>o.status===status).map((o)=><button key={o.id} onClick={()=>setSelectedId(o.id)}><strong>{o.title}</strong><span>{o.deviceId} · {o.owner}</span><small>{o.priority} · {o.dueDate}</small></button>)}</section>)}</div>}
    {view === "calendar" && <div className="panel schedule-view">{[...filtered].sort((a,b)=>a.dueDate.localeCompare(b.dueDate)).map((o)=><button key={o.id} onClick={()=>setSelectedId(o.id)}><time>{o.dueDate}</time><span><strong>{o.title}</strong><small>{o.deviceId} · {o.owner} · {o.status}</small></span></button>)}</div>}
    {view === "list" && <div className="split-layout orders-layout"><section className="panel order-list">{filtered.map((order)=><button key={order.id} className={`order-card ${selected?.id===order.id?"selected":""}`} onClick={()=>setSelectedId(order.id)}><span><strong>{order.id}</strong><em>{order.priority}</em></span><h3>{order.title}</h3><small>{order.deviceId} · {order.owner} · {order.status} · {order.dueDate}</small></button>)}{!filtered.length&&<div className="alert-empty">没有符合条件的工单</div>}</section>{selected&&<section className="panel order-detail"><div className="drawer-heading"><div><small>{selected.id}{selected.draft?" · 本地草稿":""}</small><h2>{selected.title}</h2></div><div className="detail-actions"><Button icon={<Edit24Regular/>} onClick={()=>setEditing(selected)}>编辑</Button><Button icon={<Delete24Regular/>} onClick={removeDraft}>{selected.draft?"删除草稿":"删除"}</Button></div></div><div className="order-meta"><div><span>负责人</span><strong>{selected.owner}</strong></div><div><span>目标设备</span><strong>{selected.deviceId}</strong></div><div><span>计划日期</span><strong>{selected.dueDate}</strong></div></div><p className="order-description">{selected.description||"暂未填写作业说明。"}</p><h3>现场执行清单</h3><div className="checklist">{["落实停机与上锁挂牌","完成故障检修并留存照片","复测指标并填写维修结论"].map((step,index)=><label key={step} className={selected.checklist[index]?"checked":""}><input type="checkbox" checked={selected.checklist[index]} onChange={()=>toggleStep(index)}/><span><strong>步骤 {index+1}：{step}</strong><small>{selected.checklist[index]?"已完成":"等待执行"}</small></span></label>)}</div><div className="lifecycle-actions">{WORK_ORDER_TRANSITIONS[selected.status].filter((s)=>s!=="已取消").map((status)=><Button key={status} appearance="primary" onClick={()=>move(status)}>{status==="处理中"?"开始处理":status==="待验收"?"提交验收":status==="已完成"?"验收通过":"退回处理中"}</Button>)}{WORK_ORDER_TRANSITIONS[selected.status].includes("已取消")&&<><Input placeholder="填写取消原因" value={cancelReason} onChange={(_,d)=>setCancelReason(d.value)}/><Button onClick={()=>move("已取消")}>取消工单</Button></>}</div>{!selected.draft&&<p className="boundary-note">正式工单不可硬删除；取消后仍保留在审计和统计中。</p>}</section>}</div>}
    {editing&&<WorkOrderForm initial={editing===blankForm?{...blankForm,deviceId:sourceAlert?.device?.split(" ")[0]||"",title:sourceAlert?.title||""}:editing} devices={devices} onSave={save} onClose={()=>setEditing(null)}/>} 
  </>;
}

import { useMemo, useState } from "react";
import { Button, Input } from "@fluentui/react-components";
import { changePersonStatus, filterPeople, updatePerson } from "./services/peopleManagement.js";
import { openOrdersFor, reassignOwner } from "./services/workOrderLifecycle.js";
import BelowSelect from "./BelowSelect.jsx";

export const demoPeople = [
  { id: "1", code: "EMP-001", name: "李振华", role: "维护主管", team: "设备管理组", status: "在岗", phone: "138****1024" },
  { id: "6", code: "EMP-006", name: "周工", role: "维修技师", team: "设备管理组", status: "在岗", phone: "138****3506" },
  { id: "2", code: "EMP-014", name: "张工", role: "维修技师", team: "机械一班", status: "在岗", phone: "136****8812" },
  { id: "3", code: "EMP-021", name: "王强", role: "诊断工程师", team: "可靠性组", status: "在岗", phone: "139****4506" },
  { id: "4", code: "EMP-028", name: "赵工", role: "维修技师", team: "电气二班", status: "在岗", phone: "137****6630" },
  { id: "5", code: "EMP-032", name: "陈敏", role: "生产观察员", team: "生产运行组", status: "停用", phone: "135****2701" },
  { id: "7", code: "EMP-036", name: "刘工", role: "维修技师", team: "机械一班", status: "在岗", phone: "136****4107" },
  { id: "8", code: "EMP-041", name: "黄工", role: "维修技师", team: "机械一班", status: "在岗", phone: "139****7208" },
  { id: "9", code: "EMP-047", name: "吴工", role: "维修技师", team: "电气二班", status: "在岗", phone: "137****5904" },
  { id: "10", code: "EMP-052", name: "何工", role: "诊断工程师", team: "可靠性组", status: "在岗", phone: "138****2609" },
];
const roles = ["超级管理员", "维护主管", "诊断工程师", "维修技师", "生产观察员"];
const teams = ["设备管理组", "可靠性组", "机械一班", "电气二班", "生产运行组"];

export default function PeoplePage({ notify, orders, onOrdersChange, people, onPeopleChange }) {
  const [filters, setFilters] = useState({ query: "", role: "", status: "", team: "" });
  const [selectedId, setSelectedId] = useState("1");
  const [draft, setDraft] = useState(null);
  const [recipient, setRecipient] = useState("");
  const countedPeople = useMemo(() => people.map((person) => ({ ...person, openOrders: openOrdersFor(orders, person.name).length })), [people, orders]);
  const rows = useMemo(() => filterPeople(countedPeople, filters), [countedPeople, filters]);
  const selected = rows.find((person) => person.id === selectedId) || rows[0];
  const changeFilter = (key, value) => setFilters((current) => ({ ...current, [key]: value }));

  const save = () => {
    try {
      const next = updatePerson(people, selected.id, draft);
      if (draft.name.trim() !== selected.name) onOrdersChange(orders.map((order) => order.owner === selected.name ? { ...order, owner: draft.name.trim() } : order));
      onPeopleChange(next);
      setDraft(null);
      notify("人员资料与相关工单已在本次演示会话中更新");
    } catch (error) { notify(error.message); }
  };

  const toggleStatus = () => {
    const nextStatus = selected.status === "在岗" ? "停用" : "在岗";
    try {
      const next = changePersonStatus(countedPeople, selected.id, nextStatus, recipient);
      if (nextStatus === "停用" && !window.confirm(`确认停用 ${selected.name}？${selected.openOrders ? `${selected.openOrders} 张未完成工单将转给 ${recipient}。` : ""}`)) return;
      if (nextStatus === "停用" && selected.openOrders) onOrdersChange(reassignOwner(orders, selected.name, recipient));
      onPeopleChange(next.map(({ openOrders: _count, ...person }) => person));
      setRecipient("");
      notify(nextStatus === "停用" ? `${selected.name} 已停用${selected.openOrders ? `，${selected.openOrders} 张工单已转给 ${recipient}` : ""}（本次会话）` : `${selected.name} 已恢复（本次会话）`);
    } catch (error) { notify(error.message); }
  };

  return <>
    <div className="page-heading"><div><h1>人员管理</h1><p>按岗位、班组和状态管理厂内人员及任务责任</p></div><span className="tone-badge tone-warning">本次会话演示 · 刷新后重置</span></div>
    <div className="toolbar">
      <Input className="search-input" placeholder="搜索姓名、工号、岗位或班组" value={filters.query} onChange={(_, data) => changeFilter("query", data.value)} />
      <BelowSelect value={filters.role} onChange={(value) => changeFilter("role", value)} options={[{ value: "", label: "全部岗位" }, ...roles.map((value) => ({ value, label: value }))]} />
      <BelowSelect value={filters.team} onChange={(value) => changeFilter("team", value)} options={[{ value: "", label: "全部班组" }, ...teams.map((value) => ({ value, label: value }))]} />
      <BelowSelect value={filters.status} onChange={(value) => changeFilter("status", value)} options={[{ value: "", label: "全部状态" }, { value: "在岗", label: "在岗" }, { value: "停用", label: "停用" }]} />
      <Button onClick={() => setFilters({ query: "", role: "", status: "", team: "" })}>重置</Button>
    </div>
    <div className="split-layout people-layout">
      <section className="panel table-panel grow"><table className="data-table"><thead><tr><th>人员</th><th>岗位</th><th>班组</th><th>未完成工单</th><th>状态</th></tr></thead><tbody>{rows.map((person) => <tr key={person.id} className={selected?.id === person.id ? "selected" : ""} onClick={() => { setSelectedId(person.id); setDraft(null); setRecipient(""); }}><td><strong>{person.name}</strong><small>{person.code}</small></td><td>{person.role}</td><td>{person.team}</td><td>{person.openOrders}</td><td>{person.status}</td></tr>)}</tbody></table>{!rows.length && <div className="alert-empty">没有符合条件的人员</div>}</section>
      {selected && <aside className="panel person-detail">
        <div className="drawer-heading"><div><small>{selected.code}</small><h2>{selected.name}</h2></div><Button onClick={() => setDraft({ ...selected })}>编辑资料</Button></div>
        {draft ? <div className="person-form">
          <label>姓名<Input value={draft.name} onChange={(_, data) => setDraft((current) => ({ ...current, name: data.value }))} /></label>
          <label>岗位<BelowSelect value={draft.role} onChange={(role) => setDraft((current) => ({ ...current, role }))} options={roles.map((role) => ({ value: role, label: role }))} /></label>
          <label>班组<BelowSelect value={draft.team} onChange={(team) => setDraft((current) => ({ ...current, team }))} options={teams.map((team) => ({ value: team, label: team }))} /></label>
          <div><Button onClick={() => setDraft(null)}>取消</Button><Button appearance="primary" onClick={save}>保存修改</Button></div>
        </div> : <div className="person-summary"><span>岗位<strong>{selected.role}</strong></span><span>班组<strong>{selected.team}</strong></span><span>联系电话<strong>{selected.phone}</strong></span><span>未完成工单<strong>{selected.openOrders}</strong></span></div>}
        {selected.status === "在岗" && selected.openOrders > 0 && <label className="reassign-field">停用前转派 {selected.openOrders} 张未完成工单<BelowSelect value={recipient} onChange={setRecipient} options={[{ value: "", label: "选择接收人" }, ...people.filter((person) => person.id !== selected.id && person.status === "在岗").map((person) => ({ value: person.name, label: person.name }))]} /></label>}
        <Button appearance={selected.status === "在岗" ? "secondary" : "primary"} onClick={toggleStatus}>{selected.status === "在岗" ? "停用账号" : "恢复账号"}</Button>
        <p className="boundary-note">本页操作只保留在当前浏览器会话；正式人员接口接入后才能保存到服务器。</p>
      </aside>}
    </div>
  </>;
}

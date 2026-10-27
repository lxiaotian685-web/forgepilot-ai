import { useEffect, useMemo, useState } from "react";
import { Button, Input } from "@fluentui/react-components";
import { createMember, listMembers, memberRoleLabels, patchMember } from "./services/members.js";

const editableRoles = Object.entries(memberRoleLabels);
const roleRank = { viewer: 0, technician: 1, manager: 2, admin: 3, owner: 4 };

export default function ApiPeoplePage({ session, notify, onLogout, onChanged }) {
  const [people, setPeople] = useState([]);
  const [selectedId, setSelectedId] = useState("");
  const [filters, setFilters] = useState({ query: "", role: "", status: "" });
  const [draft, setDraft] = useState(null);
  const [newPerson, setNewPerson] = useState(null);
  const [recipientId, setRecipientId] = useState("");
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  const refresh = async () => {
    const items = await listMembers(session.accessToken);
    setPeople(items);
    setSelectedId((current) => items.some((item) => item.id === current) ? current : (items[0]?.id || ""));
    setError("");
  };

  useEffect(() => {
    let active = true;
    listMembers(session.accessToken).then((items) => {
      if (!active) return;
      setPeople(items);
      setSelectedId(items[0]?.id || "");
      setError("");
    }).catch((failure) => {
      if (!active) return;
      if (failure.status === 401 || failure.status === 403) onLogout("人员管理权限已失效，请重新登录");
      else setError(failure.message);
    }).finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, [session.accessToken]);

  const rows = useMemo(() => people.filter((person) => {
    const query = filters.query.trim().toLowerCase();
    return (!filters.role || person.role === filters.role)
      && (!filters.status || person.status === filters.status)
      && (!query || [person.displayName, person.email, memberRoleLabels[person.role]].some((value) => value?.toLowerCase().includes(query)));
  }), [people, filters]);
  const selected = rows.find((person) => person.id === selectedId) || rows[0];
  const recipients = people.filter((person) => person.id !== selected?.id && person.status === "active" && roleRank[person.role] >= roleRank.technician);
  const assignableRoles = editableRoles.filter(([value]) => session.role === "owner" || !["owner", "admin"].includes(value));
  const canManageSelected = selected && (session.role === "owner" || !["owner", "admin"].includes(selected.role));

  const perform = async (action, success) => {
    setBusy(true);
    try {
      await action();
    } catch (failure) {
      if (failure.status === 401 || failure.status === 403) onLogout("人员管理权限已失效，请重新登录");
      else notify(failure.message);
      setBusy(false);
      return false;
    }
    try {
      await refresh();
      await onChanged?.();
    } catch (failure) {
      setError(`操作已保存，但列表刷新失败：${failure.message}`);
    }
    setBusy(false);
    notify(success);
    return true;
  };

  const save = async () => {
    if (!draft?.displayName.trim()) return notify("姓名不能为空");
    if (await perform(() => patchMember(session.accessToken, selected.id, { displayName: draft.displayName.trim(), role: draft.role }), "人员资料已保存到服务器")) setDraft(null);
  };

  const changeStatus = async () => {
    const disabling = selected.status === "active";
    if (disabling && selected.openWorkOrderCount && !recipientId) return notify("请先选择未完成工单的接收人");
    const text = disabling ? `停用 ${selected.displayName}${selected.openWorkOrderCount ? `并转派 ${selected.openWorkOrderCount} 张工单` : ""}` : `恢复 ${selected.displayName}`;
    if (!window.confirm(`确认${text}？`)) return;
    if (await perform(() => patchMember(session.accessToken, selected.id, {
      status: disabling ? "disabled" : "active",
      ...(disabling && selected.openWorkOrderCount ? { reassignToUserId: recipientId } : {}),
    }), disabling ? "人员已停用，工单转派已写入服务器审计" : "人员已恢复")) setRecipientId("");
  };

  const add = async () => {
    if (!newPerson.email.trim() || !newPerson.displayName.trim() || newPerson.initialPassword.length < 8) return notify("请填写邮箱、姓名和至少 8 位初始密码");
    if (await perform(() => createMember(session.accessToken, {
      email: newPerson.email.trim(), displayName: newPerson.displayName.trim(), role: newPerson.role, initialPassword: newPerson.initialPassword,
    }), "新成员已保存到服务器")) setNewPerson(null);
  };

  return <>
    <div className="page-heading"><div><h1>人员管理</h1><p>管理当前组织成员、岗位及未完成工单转派</p></div><span className="tone-badge tone-success">服务器数据</span></div>
    <div className="toolbar">
      <Input className="search-input" placeholder="搜索姓名、邮箱或岗位" value={filters.query} onChange={(_, data) => setFilters((current) => ({ ...current, query: data.value }))} />
      <select aria-label="岗位" value={filters.role} onChange={(event) => setFilters((current) => ({ ...current, role: event.target.value }))}><option value="">全部岗位</option>{editableRoles.map(([value, label]) => <option key={value} value={value}>{label}</option>)}</select>
      <select aria-label="在岗状态" value={filters.status} onChange={(event) => setFilters((current) => ({ ...current, status: event.target.value }))}><option value="">全部状态</option><option value="active">在岗</option><option value="disabled">停用</option></select>
      <Button onClick={() => setFilters({ query: "", role: "", status: "" })}>重置</Button>
      <Button onClick={() => refresh().catch((failure) => setError(failure.message))} disabled={busy}>刷新</Button>
      <Button appearance="primary" onClick={() => setNewPerson({ email: "", displayName: "", role: "technician", initialPassword: "" })}>新增成员</Button>
    </div>
    {loading && <p role="status">正在读取当前组织成员…</p>}
    {error && <p role="alert">{error}</p>}
    {newPerson && <section className="panel person-form"><h2>新增成员</h2><label>邮箱<Input value={newPerson.email} onChange={(_, data) => setNewPerson((current) => ({ ...current, email: data.value }))} /></label><label>姓名<Input value={newPerson.displayName} onChange={(_, data) => setNewPerson((current) => ({ ...current, displayName: data.value }))} /></label><label>岗位<select value={newPerson.role} onChange={(event) => setNewPerson((current) => ({ ...current, role: event.target.value }))}>{assignableRoles.map(([value, label]) => <option key={value} value={value}>{label}</option>)}</select></label><label>初始密码<Input type="password" value={newPerson.initialPassword} onChange={(_, data) => setNewPerson((current) => ({ ...current, initialPassword: data.value }))} /></label><div><Button onClick={() => setNewPerson(null)}>取消</Button><Button appearance="primary" disabled={busy} onClick={add}>创建成员</Button></div></section>}
    <div className="split-layout people-layout">
      <section className="panel table-panel grow"><table className="data-table"><thead><tr><th>人员</th><th>岗位</th><th>未完成工单</th><th>状态</th></tr></thead><tbody>{rows.map((person) => <tr key={person.id} className={selected?.id === person.id ? "selected" : ""} onClick={() => { setSelectedId(person.id); setDraft(null); setRecipientId(""); }}><td><strong>{person.displayName}</strong><small>{person.email}</small></td><td>{memberRoleLabels[person.role]}</td><td>{person.openWorkOrderCount}</td><td>{person.status === "active" ? "在岗" : "停用"}</td></tr>)}</tbody></table>{!loading && !rows.length && <div className="alert-empty">没有符合条件的成员</div>}</section>
      {selected && <aside className="panel person-detail"><div className="drawer-heading"><div><small>{selected.email}</small><h2>{selected.displayName}</h2></div><Button disabled={busy || !canManageSelected} onClick={() => setDraft({ displayName: selected.displayName, role: selected.role })}>编辑资料</Button></div>
        {draft ? <div className="person-form"><label>姓名<Input value={draft.displayName} onChange={(_, data) => setDraft((current) => ({ ...current, displayName: data.value }))} /></label><label>岗位<select value={draft.role} onChange={(event) => setDraft((current) => ({ ...current, role: event.target.value }))}>{assignableRoles.some(([value]) => value === draft.role) ? assignableRoles.map(([value, label]) => <option key={value} value={value}>{label}</option>) : <option value={draft.role}>{memberRoleLabels[draft.role]}</option>}</select></label><div><Button onClick={() => setDraft(null)}>取消</Button><Button appearance="primary" disabled={busy} onClick={save}>保存修改</Button></div></div>
          : <div className="person-summary"><span>岗位<strong>{memberRoleLabels[selected.role]}</strong></span><span>邮箱<strong>{selected.email}</strong></span><span>未完成工单<strong>{selected.openWorkOrderCount}</strong></span></div>}
        {selected.status === "active" && selected.openWorkOrderCount > 0 && <label className="reassign-field">停用前转派 {selected.openWorkOrderCount} 张未完成工单<select value={recipientId} onChange={(event) => setRecipientId(event.target.value)}><option value="">选择接收人</option>{recipients.map((person) => <option key={person.id} value={person.id}>{person.displayName} · {memberRoleLabels[person.role]}</option>)}</select></label>}
        <Button disabled={busy || !canManageSelected || selected.id === session.user.id} onClick={changeStatus}>{selected.status === "active" ? "停用账号" : "恢复账号"}</Button>
        {selected.id === session.user.id && <p className="boundary-note">不能停用当前登录账号。</p>}
        <p className="boundary-note">成员变更由服务器保存并记录审计；停用有未完成工单的成员需先转派。</p>
      </aside>}
    </div>
  </>;
}

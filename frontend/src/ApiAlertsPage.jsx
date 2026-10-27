import { useEffect, useMemo, useState } from "react";
import { Button, Input } from "@fluentui/react-components";
import { createAlert, listAlerts, patchAlert } from "./services/alertsApi.js";
import { listMembers, memberRoleLabels } from "./services/members.js";

const levels = ["一级紧急", "二级警告", "三级提示"];
const roleRank = { viewer: 0, technician: 1, manager: 2, admin: 3, owner: 4 };
const emptyForm = { deviceId: "", title: "", level: "二级警告", description: "", ownerId: "" };

export default function ApiAlertsPage({ session, devices, navigate, notify, onLogout, onChanged }) {
  const [items, setItems] = useState([]);
  const [members, setMembers] = useState([]);
  const [selectedId, setSelectedId] = useState("");
  const [filters, setFilters] = useState({ query: "", status: "", level: "" });
  const [draft, setDraft] = useState(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const canManage = roleRank[session.role] >= roleRank.manager;

  const refresh = async () => {
    const alerts = await listAlerts(session.accessToken);
    setItems(alerts);
    setSelectedId((current) => alerts.some((alert) => alert.id === current) ? current : (alerts[0]?.id || ""));
    setError("");
  };
  useEffect(() => {
    let active = true;
    Promise.all([listAlerts(session.accessToken), canManage ? listMembers(session.accessToken) : Promise.resolve([])])
      .then(([alerts, people]) => {
        if (!active) return;
        setItems(alerts);
        setMembers(people.filter((person) => person.status === "active" && roleRank[person.role] >= roleRank.technician));
        setSelectedId(alerts[0]?.id || "");
      }).catch((failure) => {
        if (!active) return;
        if (failure.status === 401) onLogout("登录已失效，请重新登录");
        else setError(failure.message);
      });
    return () => { active = false; };
  }, [session.accessToken, canManage]);

  const filtered = useMemo(() => items.filter((alert) => {
    const query = filters.query.trim().toLowerCase();
    return (!filters.status || alert.status === filters.status)
      && (!filters.level || alert.level === filters.level)
      && (!query || [alert.id, alert.title, alert.device, alert.owner].some((value) => value?.toLowerCase().includes(query)));
  }), [items, filters]);
  const selected = filtered.find((alert) => alert.id === selectedId) || filtered[0];
  const counts = { all: items.length, pending: items.filter((item) => item.status === "待确认").length,
    processing: items.filter((item) => item.status === "处理中").length, closed: items.filter((item) => item.status === "已关闭").length };

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
    if (!draft.title.trim()) return notify("告警标题不能为空");
    if (!draft.id && !draft.deviceId) return notify("请选择目标设备");
    const payload = { title: draft.title.trim(), level: draft.level, description: draft.description,
      ownerId: draft.ownerId || null, ...(!draft.id ? { deviceId: draft.deviceId } : {}) };
    const okay = await perform(() => draft.id ? patchAlert(session.accessToken, draft.id, payload) : createAlert(session.accessToken, payload),
      draft.id ? "告警修改已保存到服务器" : "告警已创建并写入服务器审计");
    if (okay) setDraft(null);
  };

  const changeStatus = async (status) => {
    if (!selected) return;
    if (status === "已关闭" && !window.confirm(`确认关闭告警 ${selected.id}？`)) return;
    await perform(() => patchAlert(session.accessToken, selected.id, { status }), `告警 ${selected.id} 已更新为${status}`);
  };

  return <>
    <div className="page-heading"><div><h1>告警中心</h1><p>创建、指派并追踪当前组织的设备异常</p></div><div><span className="tone-badge tone-success">服务器数据</span>{canManage && <Button appearance="primary" onClick={() => setDraft({ ...emptyForm })}>创建告警</Button>}</div></div>
    <div className="status-tabs">{[["", "全部", counts.all], ["待确认", "待确认", counts.pending], ["处理中", "处理中", counts.processing], ["已关闭", "已关闭", counts.closed]].map(([value, label, count]) => <button key={label} className={filters.status === value ? "active" : ""} onClick={() => setFilters((current) => ({ ...current, status: value }))}>{label} {count}</button>)}</div>
    <div className="toolbar"><Input className="search-input" placeholder="搜索告警、设备或负责人" value={filters.query} onChange={(_, data) => setFilters((current) => ({ ...current, query: data.value }))} /><select aria-label="严重程度" value={filters.level} onChange={(event) => setFilters((current) => ({ ...current, level: event.target.value }))}><option value="">全部等级</option>{levels.map((level) => <option key={level}>{level}</option>)}</select><Button onClick={() => setFilters({ query: "", status: "", level: "" })}>重置</Button><Button disabled={busy} onClick={() => refresh().catch((failure) => setError(failure.message))}>刷新</Button></div>
    {error && <p role="alert">{error}</p>}
    {draft && <section className="panel person-form"><h2>{draft.id ? `编辑 ${draft.id}` : "创建告警"}</h2>{!draft.id && <label>设备<select value={draft.deviceId} onChange={(event) => setDraft((current) => ({ ...current, deviceId: event.target.value }))}><option value="">请选择设备</option>{devices.map((device) => <option key={device.id} value={device.id}>{device.id} · {device.name}</option>)}</select></label>}<label>标题<Input value={draft.title} onChange={(_, data) => setDraft((current) => ({ ...current, title: data.value }))} /></label><label>严重程度<select value={draft.level} onChange={(event) => setDraft((current) => ({ ...current, level: event.target.value }))}>{levels.map((level) => <option key={level}>{level}</option>)}</select></label><label>负责人<select value={draft.ownerId || ""} onChange={(event) => setDraft((current) => ({ ...current, ownerId: event.target.value }))}><option value="">未指派</option>{members.map((person) => <option key={person.id} value={person.id}>{person.displayName} · {memberRoleLabels[person.role]}</option>)}</select></label><label>问题描述<textarea value={draft.description || ""} onChange={(event) => setDraft((current) => ({ ...current, description: event.target.value }))} /></label><div><Button onClick={() => setDraft(null)}>取消</Button><Button appearance="primary" disabled={busy} onClick={save}>保存</Button></div></section>}
    <div className="split-layout alerts-layout"><section className="panel alert-list">{filtered.map((alert) => <button key={alert.id} className={`alert-item ${selected?.id === alert.id ? "selected" : ""}`} onClick={() => setSelectedId(alert.id)}><span className={alert.level === "一级紧急" ? "alert-bar critical" : "alert-bar warning"} /><span className="alert-copy"><span><strong>{alert.id}</strong><small>{alert.time?.slice(0, 16).replace("T", " ")}</small></span><strong>{alert.title}</strong><em>{alert.device}</em><span><small>负责人：{alert.owner || "未指派"}</small><small>{alert.status}</small></span></span></button>)}{!filtered.length && <div className="alert-empty">没有符合条件的告警</div>}</section>
      {selected && <aside className="panel alert-detail"><div className="drawer-heading"><div><small>{selected.id} · {selected.level}</small><h2>{selected.title}</h2></div>{canManage && <Button onClick={() => setDraft({ ...selected })}>编辑</Button>}</div><p>{selected.description || "暂无问题描述"}</p><p>设备：{selected.device}　负责人：{selected.owner || "未指派"}</p><p>状态：{selected.status}</p><div className="action-row">{selected.status === "待确认" && canManage && <Button appearance="primary" disabled={busy || !selected.ownerId} onClick={() => changeStatus("处理中")}>确认并处理</Button>}{selected.status === "处理中" && canManage && <Button disabled={busy} onClick={() => changeStatus("已关闭")}>解决并关闭</Button>}{selected.status === "已关闭" && canManage && <Button disabled={busy} onClick={() => changeStatus("处理中")}>重新打开</Button>}<Button onClick={() => navigate("diagnosis", { deviceId: selected.deviceId, alert: selected })}>带入诊断</Button><Button onClick={() => navigate("orders", { alert: selected })}>关联工单</Button></div><p className="boundary-note">操作由服务器保存并记录审计；关闭与重新打开由维护主管及以上岗位执行。</p></aside>}
    </div>
  </>;
}

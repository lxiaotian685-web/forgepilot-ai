import { useMemo, useState } from "react";
import { Button, Input } from "@fluentui/react-components";
import { filterAuditRows } from "./services/workspaceFilters.js";

const labels = { code: "业务编号", status: "状态", priority: "优先级", deviceId: "设备编号", diagnosisId: "诊断编号", ownerId: "维修人员编号", owner: "维修人员", title: "工单标题", description: "作业说明", dueDate: "计划结束", startDate: "计划开始", note: "备注", displayName: "姓名", role: "岗位" };
const values = { pending: "待处理", in_progress: "处理中", completed: "已完成", cancelled: "已取消", p1: "紧急", p2: "高", p3: "中", p4: "低" };
const format = value => value == null ? "未记录" : typeof value === "object" ? Object.entries(value).map(([key, item]) => `${labels[key] || key}：${format(item)}`).join("；") : values[value] || String(value);
const localTime = value => Number.isNaN(Date.parse(value)) ? value : new Date(value).toLocaleString("zh-CN", { timeZone: "Asia/Shanghai", hour12: false });
const actionLabel = value => ({ "work_order.create": "创建工单", "work_order.update": "修改工单", "diagnosis.confirm": "确认诊断", "diagnosis.create": "保存诊断", "agent.assist": "Agent 辅助分析", "auth.login": "登录", "member.create": "新增人员", "alert.update": "更新告警", "audit.archive": "删除审计记录" }[value] || value);
export default function AuditWorkspace({ auditRows, isServer = false, onRefresh, onDelete, onEdit, busy, error }) {
  const [draft, setDraft] = useState(null);
  const [deletingId, setDeletingId] = useState(null);
  const [filters, setFilters] = useState({ query: "", actor: "", action: "", days: 0 });
  const [selectedIndex, setSelectedIndex] = useState(0);
  const rows = useMemo(() => filterAuditRows(auditRows, filters), [auditRows, filters]);
  const selected = rows[selectedIndex] || rows[0];
  const updateFilter = (key, value) => { setFilters((current) => ({ ...current, [key]: value })); setSelectedIndex(0); };

  return <>
    <div className="page-heading"><div><h1>审计记录</h1><p>{isServer ? "查看当前组织的业务操作和字段变更" : "查看业务操作示例及其关联对象"}</p></div><span className={`tone-badge ${isServer ? "tone-success" : "tone-warning"}`}>{isServer ? "服务器数据" : "演示数据 · 无法验证签名"}</span></div>
    <div className="metric-strip audit-metrics"><div><span>当前记录</span><strong>{auditRows.length}</strong><small>条</small></div><div><span>操作者</span><strong>{new Set(auditRows.map((row) => row.user)).size}</strong><small>人</small></div><div><span>筛选结果</span><strong>{rows.length}</strong><small>条</small></div></div>
    <div className="toolbar"><Input className="search-input" placeholder="搜索时间、业务对象或操作者" value={filters.query} onChange={(_, data) => updateFilter("query", data.value)} /><select aria-label="日期范围" value={filters.days} onChange={(event) => updateFilter("days", Number(event.target.value))}><option value={0}>全部日期</option><option value={3}>近 3 天</option><option value={7}>近 7 天</option><option value={30}>近 30 天</option></select><select aria-label="操作者" value={filters.actor} onChange={(event) => updateFilter("actor", event.target.value)}><option value="">全部操作者</option>{[...new Set(auditRows.map((row) => row.user))].map((value) => <option key={value}>{value}</option>)}</select><select aria-label="动作" value={filters.action} onChange={(event) => updateFilter("action", event.target.value)}><option value="">全部动作</option>{[...new Set(auditRows.map((row) => row.action))].map((value) => <option key={value}>{value}</option>)}</select><Button onClick={() => { setFilters({ query: "", actor: "", action: "", days: 0 }); setSelectedIndex(0); }}>重置</Button>{onRefresh && <Button onClick={onRefresh}>刷新</Button>}</div>
    {error && <p role="alert">{error}</p>}
    <div className="split-layout"><section className="panel table-panel grow"><table className="data-table"><thead><tr><th>时间</th><th>操作者</th><th>动作</th><th>业务对象</th><th>结果</th><th>详情</th></tr></thead><tbody>{rows.map((row, index) => <tr key={`${localTime(row.time)}-${actionLabel(row.action)}-${row.after?.code || row.before?.code || row.object}`} className={selected === row ? "selected" : ""} onClick={() => setSelectedIndex(index)}><td>{localTime(row.time)}</td><td>{row.user}</td><td>{actionLabel(row.action)}</td><td>{row.after?.code || row.before?.code || row.object}</td><td>{row.result}</td><td><Button onClick={() => { setSelectedIndex(index); document.querySelector('.audit-detail')?.scrollIntoView({ block: 'nearest' }); }}>查看详情</Button></td></tr>)}</tbody></table>{!rows.length && <div className="alert-empty">没有符合条件的审计记录</div>}</section>
      {selected && <aside className="panel audit-detail"><div className="drawer-heading"><div><small>操作详情</small><h2>{actionLabel(selected.action)}</h2></div><span className="tone-badge">{selected.result}</span></div>
        <div className="audit-section"><span>操作人</span><strong>{selected.user}</strong><span>操作时间（北京时间）</span><strong>{localTime(selected.time)}</strong></div>
        <div className="audit-section"><span>业务编号</span><strong>{selected.after?.code || selected.before?.code || selected.object}</strong><span>设备</span><strong>{selected.after?.deviceId || selected.before?.deviceId || "此记录未涉及设备"}</strong><span>维修人员（操作时记录）</span><strong>{selected.after?.ownerName || selected.after?.owner || selected.before?.ownerName || "此记录未记录维修人员"}</strong></div>
        <div className="audit-section"><span>改动明细</span>{[...new Set([...Object.keys(selected.before || {}), ...Object.keys(selected.after || {})])].length ? <dl className="audit-changes">{[...new Set([...Object.keys(selected.before || {}), ...Object.keys(selected.after || {})])].map(key => <div key={key}><dt>{labels[key] || key}</dt><dd><small>改动前</small><p>{format(selected.before?.[key])}</p><small>改动后</small><p>{format(selected.after?.[key])}</p></dd></div>)}</dl> : <p>本次操作没有记录字段变更。</p>}</div>
        <div className="audit-section"><span>补充维修人员</span><strong>{selected.annotation?.ownerName || "未填写"}</strong><span>补充备注</span><p>{selected.annotation?.note || "暂无备注"}</p></div>
        {onEdit && <div className="audit-section">{draft?.id === selected.id ? <form onSubmit={async event => { event.preventDefault(); if (await onEdit(selected, { ownerName: draft.ownerName, note: draft.note })) setDraft(null); }}>
          <label>维修人员<Input value={draft.ownerName} maxLength={100} onChange={(_, data) => setDraft({ ...draft, ownerName: data.value })} /></label>
          <label>备注与更正说明<textarea value={draft.note} maxLength={2000} onChange={event => setDraft({ ...draft, note: event.target.value })} /></label>
          <p>此处补充审计信息；实际工单指派请在维护工单页修改。</p>
          <Button type="submit" disabled={busy}>保存修改</Button><Button disabled={busy} onClick={() => setDraft(null)}>取消</Button>
        </form> : <Button disabled={busy} onClick={() => setDraft({ id: selected.id, ownerName: selected.annotation?.ownerName || selected.after?.ownerName || selected.after?.owner || "", note: selected.annotation?.note || "" })}>编辑记录</Button>}</div>}
        {onDelete && !["audit.archive", "audit.annotate"].includes(selected.action) && <div className="audit-section">{deletingId === selected.id ? <><p>确定从列表删除这条记录？原始记录及删除留痕会保留。</p><Button disabled={busy} onClick={async () => { await onDelete(selected); setDeletingId(null); }}>确认删除</Button><Button disabled={busy} onClick={() => setDeletingId(null)}>取消</Button></> : <Button disabled={busy} onClick={() => setDeletingId(selected.id)}>删除此记录</Button>}</div>}
      </aside>}
    </div>
  </>;
}

import { useMemo, useState } from "react";
import { Button, Input } from "@fluentui/react-components";
import { filterAuditRows } from "./services/workspaceFilters.js";

export default function AuditWorkspace({ auditRows }) {
  const [filters, setFilters] = useState({ query: "", actor: "", action: "" });
  const [selectedIndex, setSelectedIndex] = useState(0);
  const rows = useMemo(() => filterAuditRows(auditRows, filters), [auditRows, filters]);
  const selected = rows[selectedIndex] || rows[0];
  const updateFilter = (key, value) => { setFilters((current) => ({ ...current, [key]: value })); setSelectedIndex(0); };

  return <>
    <div className="page-heading"><div><h1>审计记录</h1><p>查看业务操作示例及其关联对象</p></div><span className="tone-badge tone-warning">演示数据 · 无法验证签名</span></div>
    <div className="metric-strip audit-metrics"><div><span>当前记录</span><strong>{auditRows.length}</strong><small>条</small></div><div><span>操作者</span><strong>{new Set(auditRows.map((row) => row.user)).size}</strong><small>人</small></div><div><span>筛选结果</span><strong>{rows.length}</strong><small>条</small></div></div>
    <div className="toolbar"><Input className="search-input" placeholder="搜索时间、业务对象或操作者" value={filters.query} onChange={(_, data) => updateFilter("query", data.value)} /><select aria-label="操作者" value={filters.actor} onChange={(event) => updateFilter("actor", event.target.value)}><option value="">全部操作者</option>{[...new Set(auditRows.map((row) => row.user))].map((value) => <option key={value}>{value}</option>)}</select><select aria-label="动作" value={filters.action} onChange={(event) => updateFilter("action", event.target.value)}><option value="">全部动作</option>{[...new Set(auditRows.map((row) => row.action))].map((value) => <option key={value}>{value}</option>)}</select><Button onClick={() => { setFilters({ query: "", actor: "", action: "" }); setSelectedIndex(0); }}>重置</Button></div>
    <div className="split-layout"><section className="panel table-panel grow"><table className="data-table"><thead><tr><th>时间</th><th>操作者</th><th>动作</th><th>业务对象</th><th>结果</th></tr></thead><tbody>{rows.map((row, index) => <tr key={`${row.time}-${row.action}-${row.object}`} className={selected === row ? "selected" : ""} onClick={() => setSelectedIndex(index)}><td>{row.time}</td><td>{row.user}</td><td>{row.action}</td><td>{row.object}</td><td>{row.result}</td></tr>)}</tbody></table>{!rows.length && <div className="alert-empty">没有符合条件的审计记录</div>}</section>
      {selected && <aside className="panel audit-detail"><div className="drawer-heading"><div><small>操作详情</small><h2>{selected.action}</h2></div><span className="tone-badge">{selected.result}</span></div><div className="audit-section"><span>操作人</span><strong>{selected.user}</strong></div><div className="audit-section"><span>业务对象</span><strong>{selected.object}</strong></div><div className="audit-section"><span>记录时间</span><strong>{selected.time}</strong></div><p className="boundary-note">此演示记录没有请求编号、变更前后字段或签名。接入服务器审计接口后才能验证完整操作链。</p></aside>}
    </div>
  </>;
}

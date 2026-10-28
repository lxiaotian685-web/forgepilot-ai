import { useEffect, useMemo, useRef, useState } from "react";
import { Button, Input } from "@fluentui/react-components";
import { filterEvidence, validateEvidenceFile } from "./services/workspaceFilters.js";

export default function KnowledgeWorkspace({ evidence, notify }) {
  const [items, setItems] = useState(evidence);
  const [selectedName, setSelectedName] = useState(evidence[0]?.name || "");
  const [filters, setFilters] = useState({ query: "", type: "", state: "" });
  const [showReader, setShowReader] = useState(false);
  const [showReferences, setShowReferences] = useState(false);
  const input = useRef(null);
  const objectUrls = useRef([]);

  useEffect(() => setItems(evidence), [evidence]);
  useEffect(() => () => objectUrls.current.forEach((url) => URL.revokeObjectURL(url)), []);

  const rows = useMemo(() => filterEvidence(items, filters), [items, filters]);
  const selected = rows.find((item) => item.name === selectedName) || rows[0];
  const updateFilter = (key, value) => setFilters((current) => ({ ...current, [key]: value }));
  const upload = async (file) => {
    try {
      validateEvidenceFile(file, items.map((item) => item.name));
      const preview = /\.(txt|md)$/i.test(file.name) ? (await file.text()).slice(0, 600) : "";
      const localUrl = URL.createObjectURL(file);
      objectUrls.current.push(localUrl);
      const record = { name: file.name, type: "本地文件", version: "本次会话", device: "未关联", source: "本地选择", state: "未解析", chunks: 0, localUrl, preview };
      setItems((current) => [record, ...current]);
      setFilters({ query: "", type: "", state: "" });
      setSelectedName(file.name);
      notify("文件已加入本次会话，可打开原文；尚未上传或解析到服务器");
    } catch (error) { notify(error.message); }
    if (input.current) input.current.value = "";
  };

  return <>
    <div className="page-heading"><div><h1>知识证据</h1><p>查找设备资料，核对来源和解析状态</p></div><Button appearance="primary" onClick={() => input.current?.click()}>选择本地文件</Button></div>
    <input ref={input} type="file" accept=".pdf,.txt,.md,application/pdf,text/plain,text/markdown" className="visually-hidden" aria-label="选择知识文档" onChange={(event) => upload(event.target.files?.[0])} />
    <div className="context-note"><strong>资料边界</strong><span>本地选择仅用于预览；上传、解析、版本管理及引用记录需接入知识库接口。请勿选择未获授权的企业文件。</span></div>
    <div className="toolbar"><Input className="search-input" placeholder="搜索文档、设备或来源" value={filters.query} onChange={(_, data) => updateFilter("query", data.value)} /><select aria-label="文档类型" value={filters.type} onChange={(event) => updateFilter("type", event.target.value)}><option value="">全部类型</option>{[...new Set(items.map((item) => item.type))].map((value) => <option key={value}>{value}</option>)}</select><select aria-label="解析状态" value={filters.state} onChange={(event) => updateFilter("state", event.target.value)}><option value="">全部状态</option>{[...new Set(items.map((item) => item.state))].map((value) => <option key={value}>{value}</option>)}</select><Button onClick={() => setFilters({ query: "", type: "", state: "" })}>重置</Button></div>
    <div className="split-layout"><section className="panel table-panel grow"><table className="data-table"><thead><tr><th>文档标题</th><th>类型</th><th>版本</th><th>适用设备</th><th>来源</th><th>解析状态</th></tr></thead><tbody>{rows.map((item) => <tr key={item.name} className={selected?.name === item.name ? "selected" : ""} onClick={() => setSelectedName(item.name)}><td><strong>{item.name}</strong></td><td>{item.type}</td><td>{item.version}</td><td>{item.device}</td><td>{item.source}</td><td>{item.state}</td></tr>)}</tbody></table>{!rows.length && <div className="alert-empty">没有符合条件的资料</div>}</section>
      {selected && <aside className="panel document-preview"><div className="drawer-heading"><div><small>当前资料</small><h2>{selected.name}</h2></div><span className="tone-badge">{selected.state}</span></div><div className="document-meta"><div><span>版本</span><strong>{selected.version}</strong></div><div><span>切片数量</span><strong>{selected.chunks || "未解析"}</strong></div><div><span>适用设备</span><strong>{selected.device}</strong></div></div><h3>内容预览</h3><p className="knowledge-preview">{selected.preview || (selected.localUrl ? "PDF 已选择，可使用下方按钮打开原文。" : "当前列表只有资料元数据；原文及引用尚未接入。")}</p><div className="action-row"><Button appearance="primary" onClick={() => selected.localUrl ? window.open(selected.localUrl, "_blank", "noopener,noreferrer") : setShowReader((value) => !value)}>{selected.localUrl ? "打开本地原文" : showReader ? "收起演示摘录" : "阅读演示摘录"}</Button><Button onClick={() => setShowReferences((value) => !value)}>{showReferences ? "收起引用说明" : "查看引用说明"}</Button></div>{showReader && !selected.localUrl && <section className="demo-document-reader"><small>演示资料 · 第 1 页 · 非原始文件</small><h3>{selected.name}</h3><p>{selected.preview || "仅有资料元数据，暂无可阅读的演示摘录。"}</p><p>正式使用时应对照授权原文、文档版本及设备型号核实。</p></section>}{showReferences && <section className="demo-document-reader"><small>引用说明</small><p>{selected.localUrl ? "本地文件尚未解析，不会进入诊断引用。" : `该演示摘录可在诊断工作台选择 ${selected.device} 时作为本地示例证据查看；未连接企业知识库，暂无真实引用记录。`}</p></section>}{!selected.localUrl && <p className="boundary-note">原始文件尚未连接；上方只能阅读虚构演示摘录。</p>}</aside>}
    </div>
  </>;
}

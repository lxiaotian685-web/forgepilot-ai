import { useEffect, useMemo, useRef, useState } from "react";
import { Button, Input } from "@fluentui/react-components";
import { listKnowledgeDocuments, uploadKnowledgeDocument } from "./services/knowledgeApi.js";

const roleRank = { viewer: 0, technician: 1, manager: 2, admin: 3, owner: 4 };

export default function ApiKnowledgePage({ session, notify, onLogout }) {
  const [documents, setDocuments] = useState([]);
  const [selectedId, setSelectedId] = useState("");
  const [query, setQuery] = useState("");
  const [file, setFile] = useState(null);
  const [fields, setFields] = useState({ title: "", equipmentModel: "", version: "1.0", source: "" });
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const fileInput = useRef(null);
  const canUpload = roleRank[session.role] >= roleRank.manager;
  const handleFailure = (failure) => {
    if (failure.status === 401) onLogout("登录已失效，请重新登录");
    else setError(failure.message);
  };
  const refresh = async () => {
    const next = await listKnowledgeDocuments(session);
    setDocuments(next);
    setSelectedId((current) => next.some((item) => item.id === current) ? current : (next[0]?.id || ""));
    setError("");
  };
  useEffect(() => {
    let active = true;
    listKnowledgeDocuments(session).then((next) => {
      if (!active) return;
      setDocuments(next);
      setSelectedId(next[0]?.id || "");
    }).catch((failure) => { if (active) handleFailure(failure); });
    return () => { active = false; };
  }, [session.accessToken, session.organization.id]);

  const rows = useMemo(() => documents.filter((item) =>
    [item.title, item.equipment_model, item.source].some((value) => String(value || "").toLowerCase().includes(query.toLowerCase().trim()))), [documents, query]);
  const selected = rows.find((item) => item.id === selectedId) || rows[0];
  const upload = async () => {
    if (!file || !fields.title.trim() || !fields.equipmentModel.trim()) return notify("请选择文件并填写标题和设备型号");
    setBusy(true);
    try {
      const result = await uploadKnowledgeDocument(session, file, fields);
      await refresh();
      setSelectedId(result.document_id);
      setFile(null);
      setFields({ title: "", equipmentModel: "", version: "1.0", source: "" });
      if (fileInput.current) fileInput.current.value = "";
      notify(`已入库并解析 ${result.chunk_count} 个切片`);
    } catch (failure) { handleFailure(failure); }
    finally { setBusy(false); }
  };

  return <>
    <div className="page-heading"><div><h1>知识证据</h1><p>当前组织的知识库文档与设备型号</p></div><span className="tone-badge tone-success">服务器数据</span></div>
    {canUpload && <section className="panel work-order-form"><h2>上传并解析文档</h2><div className="form-grid"><label>选择文件<input ref={fileInput} type="file" accept=".pdf,.txt,.md" onChange={(event) => { const next = event.target.files?.[0] || null; setFile(next); setFields((current) => ({ ...current, title: next?.name.replace(/\.[^.]+$/, "") || "" })); }} /></label><label>标题<Input value={fields.title} onChange={(_, data) => setFields((current) => ({ ...current, title: data.value }))} /></label><label>设备型号<Input value={fields.equipmentModel} onChange={(_, data) => setFields((current) => ({ ...current, equipmentModel: data.value }))} /></label><label>版本<Input value={fields.version} onChange={(_, data) => setFields((current) => ({ ...current, version: data.value }))} /></label></div><label>来源<Input value={fields.source} onChange={(_, data) => setFields((current) => ({ ...current, source: data.value }))} placeholder="留空则使用文件名" /></label><Button appearance="primary" disabled={busy || !file} onClick={upload}>{busy ? "解析中…" : "上传到知识库"}</Button></section>}
    <div className="toolbar"><Input className="search-input" placeholder="搜索标题、型号或来源" value={query} onChange={(_, data) => setQuery(data.value)} /><Button onClick={() => refresh().catch(handleFailure)}>刷新</Button></div>
    {error && <p role="alert">{error}</p>}
    <div className="split-layout"><section className="panel table-panel grow"><table className="data-table"><thead><tr><th>文档标题</th><th>设备型号</th><th>版本</th><th>页数</th><th>来源</th></tr></thead><tbody>{rows.map((item) => <tr key={item.id} className={selected?.id === item.id ? "selected" : ""} onClick={() => setSelectedId(item.id)}><td><strong>{item.title}</strong></td><td>{item.equipment_model}</td><td>{item.version}</td><td>{item.page_count}</td><td>{item.source}</td></tr>)}</tbody></table>{!rows.length && <div className="alert-empty">暂无符合条件的文档</div>}</section>{selected && <aside className="panel document-preview"><div className="drawer-heading"><div><small>{selected.id}</small><h2>{selected.title}</h2></div></div><div className="document-meta"><div><span>设备型号</span><strong>{selected.equipment_model}</strong></div><div><span>版本</span><strong>{selected.version}</strong></div><div><span>页数</span><strong>{selected.page_count}</strong></div></div><p>来源：{selected.source}</p><p className="boundary-note">知识库接口仅返回元数据；原文下载与引用记录尚无服务接口。</p></aside>}</div>
  </>;
}

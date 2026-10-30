import { useEffect, useState } from "react";
import AuditWorkspace from "./AuditWorkspace.jsx";
import { listAuditEvents } from "./services/auditApi.js";

export default function ApiAuditPage({ session, onLogout }) {
  const [rows, setRows] = useState([]);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const [busy, setBusy] = useState(false);
  const refresh = async () => {
    try {
      const next = await listAuditEvents(session.accessToken);
      setRows(next);
      setError("");
    } catch (failure) {
      if (failure.status === 401) onLogout("登录已失效，请重新登录");
      else setError(failure.message);
    }
  };
  useEffect(() => { refresh(); }, [session.accessToken]);
  const remove = async (row) => {
    setBusy(true);
    setError("");
    try {
      const base = (import.meta.env.VITE_API_BASE_URL || "").replace(/\/$/, "");
      const response = await fetch(`${base}/api/v1/audit-events/${encodeURIComponent(row.id)}`, { method: "DELETE", headers: { Authorization: `Bearer ${session.accessToken}` } });
      if (!response.ok) throw new Error(`删除失败（${response.status}），请检查权限或服务状态`);
      setRows(current => current.filter(item => item.id !== row.id));
      setMessage("记录已删除");
      await refresh();
    } catch (failure) { setError(failure.message); }
    finally { setBusy(false); }
  };
  const edit = async (row, annotation) => {
    setBusy(true);
    setError("");
    try {
      const base = (import.meta.env.VITE_API_BASE_URL || "").replace(/\/$/, "");
      const response = await fetch(`${base}/api/v1/audit-events/${encodeURIComponent(row.id)}`, {
        method: "PATCH", headers: { Authorization: `Bearer ${session.accessToken}`, "Content-Type": "application/json" },
        body: JSON.stringify(annotation),
      });
      if (!response.ok) throw new Error(`保存失败（${response.status}）`);
      const result = await response.json();
      setRows(current => current.map(item => item.id === row.id ? { ...item, annotation: result.annotation } : item));
      setMessage("维修人员及备注已保存");
      return true;
    } catch (failure) { setError(failure.message); return false; }
    finally { setBusy(false); }
  };
  const editable = ["owner", "admin"].includes(session.role);
  return <><p role="status">{message}</p><AuditWorkspace auditRows={rows} isServer onRefresh={refresh} onDelete={editable ? remove : undefined} onEdit={editable ? edit : undefined} busy={busy} error={error} /></>;
}

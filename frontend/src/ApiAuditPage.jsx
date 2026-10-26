import { useEffect, useState } from "react";
import AuditWorkspace from "./AuditWorkspace.jsx";
import { listAuditEvents } from "./services/auditApi.js";

export default function ApiAuditPage({ session, onLogout }) {
  const [rows, setRows] = useState([]);
  const [error, setError] = useState("");
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
  return <AuditWorkspace auditRows={rows} isServer onRefresh={refresh} error={error} />;
}

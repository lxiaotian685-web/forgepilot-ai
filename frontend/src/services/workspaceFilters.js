export function filterEvidence(items, { query = "", type = "", state = "" } = {}) {
  const term = query.trim().toLowerCase();
  return items.filter((item) => (!type || item.type === type)
    && (!state || item.state === state)
    && (!term || [item.name, item.device, item.source].some((value) => String(value || "").toLowerCase().includes(term))));
}

export function validateEvidenceFile(file, existingNames) {
  if (!file) throw new Error("请选择文件");
  if (!/\.(pdf|txt|md)$/i.test(file.name)) throw new Error("仅支持 PDF、TXT 或 Markdown 文件");
  if (file.size > 10 * 1024 * 1024) throw new Error("文件不能超过 10 MB");
  if (existingNames.some((name) => name.toLowerCase() === file.name.toLowerCase())) throw new Error("同名资料已存在");
}

export function filterAuditRows(rows, { query = "", actor = "", action = "", days = 0 } = {}, now = new Date()) {
  const term = query.trim().toLowerCase();
  const cutoff = days ? new Date(now.getTime() - Number(days) * 24 * 60 * 60 * 1000) : null;
  return rows.filter((row) => (!actor || row.user === actor)
    && (!action || row.action === action)
    && (!cutoff || (Number.isFinite(Date.parse(row.time)) && new Date(row.time) >= cutoff))
    && (!term || [row.id, row.entityId, row.time, row.user, row.action, row.object, row.result, JSON.stringify(row.before || {}), JSON.stringify(row.after || {})].some((value) => String(value || "").toLowerCase().includes(term))));
}

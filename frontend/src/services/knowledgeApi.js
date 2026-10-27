const runtimeEnv = import.meta.env || {};
const baseUrl = (runtimeEnv.VITE_DIAGNOSIS_API_BASE_URL || "").replace(/\/$/, "");

function headers(session, apiBaseUrl) {
  if (!apiBaseUrl || !session?.accessToken || !session?.organization?.id) throw new Error("知识库服务或登录信息未配置");
  return { Authorization: `Bearer ${session.accessToken}`, "X-Organization-Id": session.organization.id, "X-User-Id": session.user.id };
}

async function checked(response) {
  if (response.ok) return response.json();
  let message = `知识库请求失败（${response.status}）`;
  try { const body = await response.json(); message = body.detail || body.error?.message || message; } catch { /* use status */ }
  const error = new Error(message);
  error.status = response.status;
  throw error;
}

export async function listKnowledgeDocuments(session, fetchImpl = globalThis.fetch, apiBaseUrl = baseUrl) {
  const results = [];
  for (let offset = 0; ; offset += 100) {
    const response = await fetchImpl(`${apiBaseUrl}/api/v1/documents?limit=100&offset=${offset}`, { headers: headers(session, apiBaseUrl) });
    const page = await checked(response);
    if (!Array.isArray(page)) throw new Error("知识库文档列表格式不正确");
    results.push(...page);
    if (page.length < 100) return results;
  }
}

export async function uploadKnowledgeDocument(session, file, fields, fetchImpl = globalThis.fetch, apiBaseUrl = baseUrl) {
  const body = new FormData();
  body.append("file", file);
  body.append("title", fields.title.trim());
  body.append("equipment_model", fields.equipmentModel.trim());
  body.append("version", fields.version.trim() || "1.0");
  body.append("source", fields.source.trim() || file.name);
  return checked(await fetchImpl(`${apiBaseUrl}/api/v1/documents/upload`, { method: "POST", headers: headers(session, apiBaseUrl), body }));
}

export async function getKnowledgeDocument(session, documentId, fetchImpl = globalThis.fetch, apiBaseUrl = baseUrl) {
  if (!documentId) throw new Error("缺少文档编号");
  return checked(await fetchImpl(`${apiBaseUrl}/api/v1/documents/${encodeURIComponent(documentId)}`, { headers: headers(session, apiBaseUrl) }));
}

export async function deleteKnowledgeDocument(session, documentId, fetchImpl = globalThis.fetch, apiBaseUrl = baseUrl) {
  if (!documentId) throw new Error("缺少文档编号");
  const response = await fetchImpl(`${apiBaseUrl}/api/v1/documents/${encodeURIComponent(documentId)}`, { method: "DELETE", headers: headers(session, apiBaseUrl) });
  if (!response.ok) await checked(response);
}

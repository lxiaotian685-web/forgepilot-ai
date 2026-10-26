import assert from "node:assert/strict";
import test from "node:test";
import { listAuditEvents } from "../src/services/auditApi.js";

test("audit list reads all pages with bearer authorization", async () => {
  const urls = [];
  const fetchImpl = async (url, options) => {
    urls.push(url);
    assert.equal(options.headers.Authorization, "Bearer token");
    const page = Number(new URL(url).searchParams.get("page"));
    return { ok: true, json: async () => ({ items: [{ id: `event-${page}` }], total: 2 }) };
  };
  const items = await listAuditEvents("token", fetchImpl, "https://api.example.com");
  assert.deepEqual(items.map((item) => item.id), ["event-1", "event-2"]);
  assert.equal(urls.length, 2);
});

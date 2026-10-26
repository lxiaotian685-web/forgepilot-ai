import test from "node:test";
import assert from "node:assert/strict";
import { listMembers, patchMember } from "../src/services/members.js";

const apiBaseUrl = "https://api.example.test";

test("members list loads every server page with bearer identity", async () => {
  const calls = [];
  const fetchImpl = async (url, options) => {
    calls.push({ url, options });
    return new Response(JSON.stringify({ items: [{ id: String(calls.length) }], total: 2 }), { status: 200 });
  };
  const members = await listMembers("session-token", fetchImpl, apiBaseUrl);
  assert.deepEqual(members.map((item) => item.id), ["1", "2"]);
  assert.match(calls[1].url, /page=2/);
  assert.equal(calls[0].options.headers.Authorization, "Bearer session-token");
  assert.equal(calls[0].options.headers["X-Organization-Id"], undefined);
});

test("member status update sends recipient id to the server", async () => {
  let sent;
  const fetchImpl = async (url, options) => {
    sent = { url, options };
    return new Response(JSON.stringify({ id: "target", status: "disabled" }), { status: 200 });
  };
  await patchMember("session-token", "target", { status: "disabled", reassignToUserId: "recipient" }, fetchImpl, apiBaseUrl);
  assert.equal(sent.options.method, "PATCH");
  assert.deepEqual(JSON.parse(sent.options.body), { status: "disabled", reassignToUserId: "recipient" });
});

test("member API error preserves server message and status", async () => {
  const fetchImpl = async () => new Response(JSON.stringify({ error: { message: "工单仍未转派" } }), { status: 409 });
  await assert.rejects(
    patchMember("session-token", "target", { status: "disabled" }, fetchImpl, apiBaseUrl),
    (error) => error.status === 409 && error.message === "工单仍未转派",
  );
});

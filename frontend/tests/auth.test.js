import { test } from "node:test";
import assert from "node:assert/strict";
import { AuthError, canAccessPage, createAuthService, getAllowedPageIds, SESSION_KEY } from "../src/services/auth.js";

function memoryStorage() {
  const values = new Map();
  return {
    getItem: (key) => values.get(key) ?? null,
    setItem: (key, value) => values.set(key, value),
    removeItem: (key) => values.delete(key),
  };
}

const session = {
  accessToken: "signed-token",
  tokenType: "Bearer",
  expiresIn: 3600,
  user: { id: "user-1", email: "owner@example.com", displayName: "王主管" },
  organization: { id: "org-1", code: "plant-1", name: "一号装配厂" },
  role: "owner",
};

test("login follows the backend contract and persists only the returned session", async () => {
  const storage = memoryStorage();
  const service = createAuthService({ baseUrl: "https://api.example.test/", storage, fetchImpl: async (url, options) => {
    assert.equal(url, "https://api.example.test/api/v1/auth/login");
    assert.deepEqual(JSON.parse(options.body), { email: "owner@example.com", password: "secret", organizationCode: "plant-1" });
    return { ok: true, json: async () => session };
  } });
  assert.deepEqual(await service.login({ email: " owner@example.com ", password: "secret", organizationCode: " plant-1 " }), session);
  assert.deepEqual(JSON.parse(storage.getItem(SESSION_KEY)), session);
});

test("server auth errors remain errors instead of becoming demo sessions", async () => {
  const service = createAuthService({ baseUrl: "https://api.example.test", storage: memoryStorage(), fetchImpl: async () => ({
    ok: false,
    status: 401,
    json: async () => ({ error: { code: "INVALID_CREDENTIALS", message: "邮箱或密码错误" } }),
  }) });
  await assert.rejects(service.login({ email: "x@y.test", password: "bad", organizationCode: "" }), (error) => {
    assert.ok(error instanceof AuthError);
    assert.equal(error.status, 401);
    assert.equal(error.message, "邮箱或密码错误");
    return true;
  });
});

test("refresh sends bearer token and clears an expired session", async () => {
  const storage = memoryStorage();
  storage.setItem(SESSION_KEY, JSON.stringify(session));
  const service = createAuthService({ baseUrl: "https://api.example.test", storage, fetchImpl: async (_, options) => {
    assert.equal(options.headers.Authorization, "Bearer signed-token");
    return { ok: false, status: 401, json: async () => ({ error: { message: "登录已过期" } }) };
  } });
  await assert.rejects(service.refresh(session), /登录已过期/);
  assert.equal(storage.getItem(SESSION_KEY), null);
});

test("role navigation is deny-by-default", () => {
  assert.equal(canAccessPage("owner", "people"), true);
  assert.equal(canAccessPage("technician", "orders"), true);
  assert.equal(canAccessPage("technician", "audit"), false);
  assert.equal(canAccessPage("viewer", "diagnosis"), false);
  assert.deepEqual(getAllowedPageIds("unknown"), []);
});

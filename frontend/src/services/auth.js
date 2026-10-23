const runtimeEnv = import.meta.env || {};

export const roleLabels = {
  owner: "企业负责人",
  admin: "系统管理员",
  manager: "维护主管",
  technician: "维修人员",
  viewer: "只读访客",
};

const rolePages = {
  owner: ["overview", "devices", "alerts", "diagnosis", "knowledge", "orders", "audit", "people"],
  admin: ["overview", "devices", "alerts", "diagnosis", "knowledge", "orders", "audit", "people"],
  manager: ["overview", "devices", "alerts", "diagnosis", "knowledge", "orders", "audit"],
  technician: ["overview", "devices", "alerts", "diagnosis", "knowledge", "orders"],
  viewer: ["overview", "devices", "alerts", "orders"],
};

export const SESSION_KEY = "forgepilot.session.v1";

export class AuthError extends Error {
  constructor(message, status = 0, code = "AUTH_FAILED") {
    super(message);
    this.name = "AuthError";
    this.status = status;
    this.code = code;
  }
}

export function canAccessPage(role, pageId) {
  return (rolePages[role] || []).includes(pageId);
}

export function getAllowedPageIds(role) {
  return [...(rolePages[role] || [])];
}

function parseSession(value) {
  if (!value || typeof value !== "object") throw new AuthError("登录响应格式不完整");
  if (!value.accessToken || !value.user?.id || !value.organization?.id || !roleLabels[value.role]) {
    throw new AuthError("登录响应缺少令牌、用户、组织或有效角色");
  }
  return value;
}

async function parseError(response) {
  try {
    const payload = await response.json();
    return new AuthError(payload?.error?.message || `登录请求失败（${response.status}）`, response.status, payload?.error?.code);
  } catch {
    return new AuthError(`登录请求失败（${response.status}）`, response.status);
  }
}

export function createAuthService({
  baseUrl = runtimeEnv.VITE_API_BASE_URL || "",
  fetchImpl = globalThis.fetch,
  storage = globalThis.sessionStorage,
} = {}) {
  const apiBaseUrl = baseUrl.replace(/\/$/, "");

  const save = (session) => storage?.setItem(SESSION_KEY, JSON.stringify(session));
  const clear = () => storage?.removeItem(SESSION_KEY);

  return {
    getStoredSession() {
      try {
        const raw = storage?.getItem(SESSION_KEY);
        return raw ? parseSession(JSON.parse(raw)) : null;
      } catch {
        clear();
        return null;
      }
    },
    clear,
    async login({ email, password, organizationCode }) {
      if (!apiBaseUrl) throw new AuthError("尚未配置后端地址，无法进行真实登录");
      const response = await fetchImpl(`${apiBaseUrl}/api/v1/auth/login`, {
        method: "POST",
        headers: { Accept: "application/json", "Content-Type": "application/json" },
        body: JSON.stringify({
          email: email.trim(),
          password,
          ...(organizationCode.trim() ? { organizationCode: organizationCode.trim() } : {}),
        }),
      });
      if (!response.ok) throw await parseError(response);
      const session = parseSession(await response.json());
      save(session);
      return session;
    },
    async refresh(session) {
      const current = parseSession(session);
      if (!apiBaseUrl) return current;
      const response = await fetchImpl(`${apiBaseUrl}/api/v1/auth/me`, {
        headers: { Accept: "application/json", Authorization: `Bearer ${current.accessToken}` },
      });
      if (!response.ok) {
        if (response.status === 401 || response.status === 403) clear();
        throw await parseError(response);
      }
      const identity = await response.json();
      const refreshed = parseSession({ ...current, ...identity });
      save(refreshed);
      return refreshed;
    },
  };
}

export function selectStoredSession(service, dataMode) {
  const session = service.getStoredSession();
  if (dataMode === "api" && session?.isPreview) {
    service.clear();
    return null;
  }
  return session;
}

export const authService = createAuthService();

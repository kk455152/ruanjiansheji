const LOCAL_HOSTS = new Set(["localhost", "127.0.0.1", "0.0.0.0"])

export const API_BASE =
  import.meta.env.VITE_API_BASE_URL ||
  (LOCAL_HOSTS.has(window.location.hostname) ? "http://8.137.165.220" : "")

export class ApiError extends Error {
  constructor(message, status, payload) {
    super(message)
    this.name = "ApiError"
    this.status = status
    this.payload = payload
  }
}

function buildUrl(path, params) {
  const url = new URL(`${API_BASE}${path}`, window.location.origin)
  Object.entries(params || {}).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== "") {
      url.searchParams.set(key, value)
    }
  })
  return url.toString()
}

export async function request(path, options = {}) {
  const token = options.token ?? localStorage.getItem("admin_token")
  const headers = {
    Accept: "application/json",
    ...(options.body ? { "Content-Type": "application/json" } : {}),
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
    ...options.headers,
  }

  const response = await fetch(buildUrl(path, options.params), {
    method: options.method || "GET",
    headers,
    body: options.body ? JSON.stringify(options.body) : undefined,
  })

  const text = await response.text()
  let payload = null
  try {
    payload = text ? JSON.parse(text) : null
  } catch {
    payload = { message: text }
  }

  if (!response.ok || (payload && payload.code && payload.code >= 400)) {
    throw new ApiError(
      payload?.message || payload?.msg || payload?.error_details || `请求失败：${response.status}`,
      response.status,
      payload,
    )
  }

  return payload?.data ?? payload
}

export function login(username, password, captcha = {}, sms = {}) {
  return request("/api/admin/login", {
    method: "POST",
    token: "",
    body: {
      username,
      password,
      loginType: "password",
      captchaToken: captcha.captchaToken,
      captchaAnswer: captcha.captchaAnswer,
      smsPhone: sms.smsPhone,
      smsCode: sms.smsCode,
      smsToken: sms.smsToken,
    },
  })
}

export function sendLoginSmsCode(phone) {
  return request("/api/admin/sms-code", {
    method: "POST",
    token: "",
    body: { phone },
  })
}

export function logout() {
  return request("/api/admin/logout", { method: "POST" })
}

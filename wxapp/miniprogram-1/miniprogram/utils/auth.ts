export const AUTH_STORAGE_KEY = 'login_session_v1'

export type LoginSession = {
  nickname: string
  avatarUrl: string
  loginAt: number
  code?: string
}

export function getLoginSession(): LoginSession | null {
  try {
    const raw = wx.getStorageSync(AUTH_STORAGE_KEY) as LoginSession | ''
    if (raw && typeof raw === 'object' && raw.nickname) {
      return raw
    }
  } catch (error) {
    // ignore
  }
  return null
}

export function setLoginSession(session: LoginSession) {
  try {
    wx.setStorageSync(AUTH_STORAGE_KEY, session)
  } catch (error) {
    // ignore
  }
}

export function clearLoginSession() {
  try {
    wx.removeStorageSync(AUTH_STORAGE_KEY)
  } catch (error) {
    // ignore
  }
}

export function isLoggedIn() {
  return Boolean(getLoginSession())
}

export function ensureAuthenticated(currentRoute: string) {
  if (isLoggedIn()) return true
  const target = '/pages/login/index'
  if (currentRoute && currentRoute.replace(/^\//, '') === 'pages/login/index') {
    return false
  }
  wx.reLaunch({ url: target })
  return false
}

<script setup>
import { computed, nextTick, onMounted, onUnmounted, reactive } from "vue"
import { ElMessage, ElMessageBox } from "element-plus"
import { ApiError, API_BASE, login as loginApi, logout as logoutApi, request } from "./api"

const roleNames = {
  super_admin: "超级管理员",
  market_admin: "市场分析管理员",
  operator_admin: "普通管理员",
  boss: "老板",
}

const menus = [
  { key: "overview", label: "数据总览", icon: "fa-chart-pie", section: "核心看板", roles: ["super_admin", "market_admin", "operator_admin", "boss"] },
  { key: "decision", label: "决策驾驶舱", icon: "fa-gauge-high", section: "核心看板", roles: ["super_admin", "market_admin"] },
  { key: "trend", label: "趋势分析", icon: "fa-arrow-trend-up", section: "核心看板", roles: ["super_admin", "market_admin", "operator_admin", "boss"] },
  { key: "region", label: "区域热力图", icon: "fa-map-location-dot", section: "分析洞察", roles: ["super_admin", "market_admin", "boss"] },
  { key: "profile", label: "用户画像", icon: "fa-user-tag", section: "分析洞察", roles: ["super_admin", "market_admin", "boss"] },
  { key: "value", label: "用户价值", icon: "fa-star", section: "分析洞察", roles: ["super_admin", "market_admin", "boss"] },
  { key: "segments", label: "用户分群", icon: "fa-users-rays", section: "分析洞察", roles: ["super_admin", "market_admin"] },
  { key: "insights", label: "营销洞察", icon: "fa-lightbulb", section: "分析洞察", roles: ["super_admin", "market_admin"] },
  { key: "songs", label: "热歌排行", icon: "fa-music", section: "分析洞察", roles: ["super_admin", "market_admin", "boss"] },
  { key: "feedback", label: "用户反馈", icon: "fa-comment-dots", section: "运营管理", roles: ["super_admin", "operator_admin", "boss"] },
  { key: "devices", label: "设备管理", icon: "fa-sliders", section: "运营管理", roles: ["super_admin", "operator_admin"] },
  { key: "groups", label: "设备分组", icon: "fa-layer-group", section: "运营管理", roles: ["super_admin", "operator_admin"] },
  { key: "alerts", label: "告警中心", icon: "fa-triangle-exclamation", section: "运营管理", roles: ["super_admin", "operator_admin"] },
  { key: "logs", label: "设备日志", icon: "fa-clipboard-list", section: "运营管理", roles: ["super_admin", "operator_admin"] },
  { key: "users", label: "用户管理", icon: "fa-user-gear", section: "系统管理", roles: ["super_admin"] },
  { key: "roles", label: "角色权限", icon: "fa-user-shield", section: "系统管理", roles: ["super_admin"] },
  { key: "system", label: "系统配置", icon: "fa-gear", section: "系统管理", roles: ["super_admin"] },
  { key: "notices", label: "系统公告", icon: "fa-bullhorn", section: "系统管理", roles: ["super_admin"] },
  { key: "audit", label: "审计日志", icon: "fa-shield-halved", section: "系统管理", roles: ["super_admin"] },
  { key: "account", label: "个人信息", icon: "fa-circle-user", section: "账户", roles: ["super_admin", "market_admin", "operator_admin", "boss"] },
]

const MENU_KEYS = new Set(menus.map((item) => item.key))
const PROFILE_REFRESH_INTERVAL_MS = 30000
let profileRefreshTimer = null

const state = reactive({
  loginForm: {
    username: localStorage.getItem("admin_username") || "",
    password: "",
    captchaAnswer: "",
    captchaToken: "",
    captchaVerified: false,
    captchaLoading: false,
    remember: true,
  },
  token: localStorage.getItem("admin_token") || "",
  admin: JSON.parse(localStorage.getItem("admin_info") || "null"),
  active: "overview",
  loading: false,
  booting: true,
  keyword: "",
  lastUpdated: "",
  overview: {},
  decision: { cards: [], trend: [], risks: [] },
  trend: { type: "user", dimension: "day", list: [] },
  region: { sales: [], users: [] },
  profile: { age: [], region: [], activity: [], service: [] },
  value: {},
  songs: [],
  retention: [],
  insights: { funnels: [], recommendations: [] },
  segments: { total: 0, list: [] },
  feedback: { total: 0, list: [] },
  feedbackLoading: false,
  devices: { total: 0, list: [] },
  selectedDeviceId: "",
  groups: { total: 0, list: [] },
  alerts: { total: 0, list: [] },
  runtime: null,
  logs: { total: 0, list: [] },
  users: { total: 0, list: [] },
  roles: { total: 0, list: [], catalog: [] },
  roleEditor: { open: false, role: "", roleName: "", selected: [], saving: false },
  userEditor: { open: false, mode: "create", saving: false, original: "", form: { username: "", password: "", role: "operator_admin", realName: "", phone: "", email: "", jobNo: "" } },
  settings: {},
  notices: { total: 0, list: [] },
  audit: { total: 0, list: [] },
  detail: null,
  deviceUser: { open: false, loading: false, info: null, deviceName: "" },
  passwordForm: { currentPassword: "", newPassword: "", confirmPassword: "" },
  passwordSaving: false,
})

const LOCAL_HOSTS = new Set(["localhost", "127.0.0.1", "0.0.0.0"])
const isLoggedIn = computed(() => Boolean(state.token && state.admin))
const currentRole = computed(() => state.admin?.role || "")
const currentRoleName = computed(() => state.admin?.roleName || roleNames[currentRole.value] || "未登录")
const currentPermissions = computed(() => permissionsForRole(currentRole.value, state.admin?.permissions))
const currentPermissionSet = computed(() => new Set(currentPermissions.value))
const visibleMenus = computed(() => menus.filter((item) => currentPermissionSet.value.has(item.key)))
const activeMenu = computed(() => menus.find((item) => item.key === state.active) || visibleMenus.value[0] || menus[0])
const apiLabel = computed(() => API_BASE || (LOCAL_HOSTS.has(window.location.hostname) ? "服务器接口" : "当前站点"))

const groupedMenus = computed(() => {
  const groups = []
  visibleMenus.value.forEach((item) => {
    let group = groups.find((entry) => entry.section === item.section)
    if (!group) {
      group = { section: item.section, items: [] }
      groups.push(group)
    }
    group.items.push(item)
  })
  return groups
})

const metricCards = computed(() => {
  if (currentRole.value === "operator_admin") {
    const devices = state.devices.list || []
    const online = devices.filter((item) => item.online).length
    const pending = (state.feedback.list || []).filter((item) => item.status === "pending").length
    return [
      { label: "设备总数", value: formatNumber(state.devices.total || devices.length), hint: `${online} 台在线`, tone: "green", icon: "fa-speaker-deck" },
      { label: "在线率", value: percent(devices.length ? online / devices.length : 0), hint: "来自设备列表", tone: "blue", icon: "fa-wifi" },
      { label: "待处理反馈", value: formatNumber(pending), hint: `共 ${state.feedback.total || 0} 条`, tone: "red", icon: "fa-comment-dots" },
    ]
  }

  if (currentRole.value === "market_admin") {
    const totalPlays = state.songs.reduce((sum, item) => sum + Number(item.playCount || 0), 0)
    const avgRetention = average(state.retention.map((item) => item.day7RetentionRate))
    return [
      { label: "热歌播放", value: formatNumber(totalPlays), hint: `${state.songs.length} 首上榜歌曲`, tone: "green", icon: "fa-music" },
      { label: "高活用户", value: formatNumber(state.value.highActiveUserCount || 0), hint: "近周期活跃", tone: "blue", icon: "fa-bolt" },
      { label: "普通用户", value: formatNumber(state.value.normalUserCount || 0), hint: "用户价值分层", tone: "orange", icon: "fa-users" },
      { label: "7 日留存", value: percent(avgRetention), hint: "购买设备后持续使用", tone: "red", icon: "fa-clock-rotate-left" },
    ]
  }

  const deviceTotal = state.overview.device?.deviceCount || 0
  const onlineRate = deviceTotal ? (state.overview.device?.onlineDeviceCount || 0) / deviceTotal : 0
  return [
    { label: "总用户", value: formatNumber(state.overview.user?.userCount || 0), hint: `新增 ${formatNumber(state.overview.user?.newUserCount || 0)}`, tone: "green", icon: "fa-users" },
    { label: "设备数", value: formatNumber(deviceTotal), hint: `在线率 ${percent(onlineRate)}`, tone: "blue", icon: "fa-speaker-deck" },
    { label: "销售额", value: money(state.overview.sales?.salesAmount || 0), hint: `${formatNumber(state.overview.sales?.orderCount || 0)} 笔订单`, tone: "orange", icon: "fa-wallet" },
    { label: "活跃度", value: percent(state.overview.activity?.activityRate || 0), hint: `${formatNumber(state.overview.activity?.activeUserCount || 0)} 活跃用户`, tone: "red", icon: "fa-bolt" },
  ]
})

const filteredDevices = computed(() => {
  const word = state.keyword.trim().toLowerCase()
  if (!word) return state.devices.list || []
  return (state.devices.list || []).filter((item) =>
    [item.deviceId, item.deviceName, item.ownerName, item.modelName, item.firmwareVersion].some((value) =>
      String(value || "").toLowerCase().includes(word),
    ),
  )
})

const filteredFeedback = computed(() => {
  const word = state.keyword.trim().toLowerCase()
  if (!word) return state.feedback.list || []
  return (state.feedback.list || []).filter((item) =>
    [item.feedbackId, item.nickname, item.content, item.statusText, item.feedbackTypeText].some((value) =>
      String(value || "").toLowerCase().includes(word),
    ),
  )
})

function average(values) {
  const usable = values.map(Number).filter((item) => Number.isFinite(item))
  return usable.length ? usable.reduce((sum, item) => sum + item, 0) / usable.length : 0
}

function formatNumber(value) {
  return Number(value || 0).toLocaleString("zh-CN")
}

function money(value) {
  const number = Number(value || 0)
  if (number >= 10000) return `${(number / 10000).toFixed(1)} 万`
  return number.toLocaleString("zh-CN")
}

function percent(value) {
  const number = Number(value || 0)
  return `${Math.round(number * 100)}%`
}

function labelDate(value) {
  const text = String(value || "")
  return text.includes("-") ? text.slice(5) : text
}

function maxOf(list, key = "value") {
  return Math.max(1, ...list.map((item) => Number(item[key] || 0)))
}

function barHeight(value, max, min = 16, scale = 160) {
  return `${Math.max(min, Math.round((Number(value || 0) / Math.max(max, 1)) * scale))}px`
}

// 把一个数向上取整到「好看」的刻度值（1/2/5 × 10^n）
function niceNum(n) {
  if (n <= 0) return 1
  const exp = Math.floor(Math.log10(n))
  const base = Math.pow(10, exp)
  const frac = n / base
  let nice
  if (frac <= 1) nice = 1
  else if (frac <= 2) nice = 2
  else if (frac <= 5) nice = 5
  else nice = 10
  return nice * base
}

// 格式化 Y 轴刻度标签，大数转「万」
function formatAxis(value) {
  const n = Number(value || 0)
  if (n >= 10000) return `${Number((n / 10000).toFixed(1))}万`
  return n.toLocaleString("zh-CN")
}

// 趋势图 Y 轴单位（按当前查看的指标类型变化）
const trendUnit = computed(
  () => ({ user: "人", device: "台", sales: "元", retention: "%" }[state.trend.type] || "次"),
)

// 趋势图指标名称（按当前查看的指标类型变化）
const trendMetricName = computed(
  () =>
    ({ user: "用户增长数", device: "设备增长数", sales: "销售额", retention: "用户留存率" }[
      state.trend.type
    ] || "核心指标"),
)

// 趋势图 Y 轴刻度：根据数据最大值生成好看的等距刻度
const trendAxis = computed(() => {
  const values = (state.trend.list || []).map((item) => Number(item.value || 0))
  const rawMax = Math.max(1, ...values)
  const step = niceNum(rawMax / 4)
  const tickCount = Math.max(1, Math.ceil(rawMax / step))
  const niceMax = step * tickCount
  const ticks = []
  for (let i = tickCount; i >= 0; i--) ticks.push(step * i)
  return { niceMax, ticks }
})

// 用户价值环状图：普通用户 vs 高活跃用户 占比
const valueDonut = computed(() => {
  const normal = Number(state.value.normalUserCount || 0)
  const high = Number(state.value.highActiveUserCount || 0)
  const total = normal + high
  const segments = [
    { label: "普通用户", value: normal, color: "var(--accent-green)" },
    { label: "高活跃用户", value: high, color: "var(--accent-orange)" },
  ]
  const circumference = 2 * Math.PI * 52
  let offset = 0
  const arcs = segments.map((seg) => {
    const ratio = total ? seg.value / total : 0
    const dash = ratio * circumference
    const arc = { ...seg, ratio, dash, gap: circumference - dash, dashOffset: -offset }
    offset += dash
    return arc
  })
  return { total, segments: arcs, circumference }
})

// 用户分群饼图：各运营人群的规模占比
const segmentColors = ["#84a98c", "#f4a261", "#a4c3b2", "#cb997e", "#6f9a82", "#e9c46a"]
const segmentPie = computed(() => {
  const list = state.segments.list || []
  const total = list.reduce((sum, item) => sum + Number(item.count || 0), 0)
  let angle = -90 // 从正上方开始
  const cx = 60
  const cy = 60
  const r = 54
  const slices = list.map((item, index) => {
    const ratio = total ? Number(item.count || 0) / total : 0
    const sweep = ratio * 360
    const start = angle
    const end = angle + sweep
    angle = end
    const startRad = (start * Math.PI) / 180
    const endRad = (end * Math.PI) / 180
    const x1 = cx + r * Math.cos(startRad)
    const y1 = cy + r * Math.sin(startRad)
    const x2 = cx + r * Math.cos(endRad)
    const y2 = cy + r * Math.sin(endRad)
    const largeArc = sweep > 180 ? 1 : 0
    // 单个切片占满整圆时画成完整圆，避免 path 起止点重合不渲染
    const d =
      ratio >= 0.999
        ? `M ${cx} ${cy - r} A ${r} ${r} 0 1 1 ${cx - 0.01} ${cy - r} Z`
        : `M ${cx} ${cy} L ${x1} ${y1} A ${r} ${r} 0 ${largeArc} 1 ${x2} ${y2} Z`
    return { ...item, ratio, color: segmentColors[index % segmentColors.length], d }
  })
  return { total, slices }
})

// 通用饼图切片生成：给定数据列表和标签字段，返回带 SVG path 的扇区
function pieSlices(list, labelKey) {
  const items = list || []
  const total = items.reduce((sum, item) => sum + Number(item.count || 0), 0)
  let angle = -90
  const cx = 60
  const cy = 60
  const r = 54
  return items.map((item, index) => {
    const ratio = total ? Number(item.count || 0) / total : 0
    const sweep = ratio * 360
    const start = angle
    const end = angle + sweep
    angle = end
    const a1 = (start * Math.PI) / 180
    const a2 = (end * Math.PI) / 180
    const x1 = cx + r * Math.cos(a1)
    const y1 = cy + r * Math.sin(a1)
    const x2 = cx + r * Math.cos(a2)
    const y2 = cy + r * Math.sin(a2)
    const largeArc = sweep > 180 ? 1 : 0
    const d =
      ratio >= 0.999
        ? `M ${cx} ${cy - r} A ${r} ${r} 0 1 1 ${cx - 0.01} ${cy - r} Z`
        : `M ${cx} ${cy} L ${x1} ${y1} A ${r} ${r} 0 ${largeArc} 1 ${x2} ${y2} Z`
    return {
      label: item[labelKey],
      count: Number(item.count || 0),
      ratio,
      color: segmentColors[index % segmentColors.length],
      d,
    }
  })
}

function statusText(status) {
  return {
    enabled: "启用",
    readonly: "只读",
    active: "正常",
    normal: "正常",
    inactive: "停用",
    disabled: "停用",
    pending: "待处理",
    processing: "处理中",
    processed: "已处理",
    success: "成功",
    open: "待处理",
    closed: "已关闭",
    published: "已发布",
    draft: "草稿",
    gray: "灰度",
    stable: "稳定",
    rollback: "可回滚",
  }[status] || status || "-"
}

function setUpdated() {
  state.lastUpdated = new Date().toLocaleString("zh-CN", {
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  })
}

function permissionsForRole(role, permissions) {
  if (Array.isArray(permissions)) {
    return permissions.filter((key) => MENU_KEYS.has(key))
  }
  return menus.filter((item) => item.roles.includes(role)).map((item) => item.key)
}

function firstMenuForAdmin(admin) {
  const keys = permissionsForRole(admin?.role || "", admin?.permissions)
  return menus.find((item) => keys.includes(item.key))?.key || "overview"
}

function canUse(key) {
  return visibleMenus.value.some((item) => item.key === key)
}

function api(path, options) {
  return request(path, options).catch((error) => {
    if (error instanceof ApiError && (error.status === 401 || error.payload?.code === 401)) {
      clearSession()
      ElMessage.warning("登录已失效，请重新登录")
    }
    throw error
  })
}

async function silent(loader, fallback) {
  try {
    return await loader()
  } catch (error) {
    console.warn(error)
    return fallback
  }
}

function resetRobotVerification() {
  state.loginForm.captchaToken = ""
  state.loginForm.captchaAnswer = ""
  state.loginForm.captchaVerified = false
}

async function verifyRobot() {
  if (state.loginForm.captchaLoading || state.loginForm.captchaVerified) return
  state.loginForm.captchaLoading = true
  try {
    const data = await request("/api/admin/captcha", { token: "" })
    state.loginForm.captchaToken = data.captchaToken || ""
    state.loginForm.captchaAnswer = "not_robot_checked"
    state.loginForm.captchaVerified = Boolean(state.loginForm.captchaToken)
  } catch (error) {
    console.warn(error)
    resetRobotVerification()
    ElMessage.error("机器人验证失败，请重试")
  } finally {
    state.loginForm.captchaLoading = false
  }
}

async function handleLogin() {
  if (!state.loginForm.username || !state.loginForm.password) {
    ElMessage.warning("请输入用户名和密码")
    return
  }
  if (!state.loginForm.captchaToken || !state.loginForm.captchaAnswer) {
    ElMessage.warning("请完成机器人验证")
    return
  }

  state.loading = true
  try {
    const data = await loginApi(state.loginForm.username.trim(), state.loginForm.password, {
      captchaToken: state.loginForm.captchaToken,
      captchaAnswer: state.loginForm.captchaAnswer.trim(),
    })
    applySession(data)
    if (state.loginForm.remember) {
      localStorage.setItem("admin_username", state.loginForm.username.trim())
    } else {
      localStorage.removeItem("admin_username")
    }
    state.loginForm.password = ""
    state.loginForm.captchaAnswer = ""
    ElMessage.success("登录成功，正在加载后台数据")
    await loadPage(true)
  } catch (error) {
    ElMessage.error(error.message || "登录失败")
    resetRobotVerification()
  } finally {
    state.loading = false
  }
}

function applySession(data) {
  const token = data.token || data.access_token
  state.token = token
  state.admin = data.adminInfo
  localStorage.setItem("admin_token", token)
  localStorage.setItem("admin_info", JSON.stringify(data.adminInfo))
  state.active = firstMenuForAdmin(data.adminInfo)
  startProfileRefresh()
}

function clearSession() {
  state.token = ""
  state.admin = null
  stopProfileRefresh()
  resetRobotVerification()
  localStorage.removeItem("admin_token")
  localStorage.removeItem("admin_info")
}

async function handleLogout() {
  await silent(() => logoutApi(), null)
  clearSession()
  state.detail = null
  ElMessage.success("已退出登录")
  await nextTick()
  resetRobotVerification()
}

async function refreshAdminProfile() {
  const previousActive = state.active
  const admin = await api("/api/admin/profile")
  state.admin = admin
  localStorage.setItem("admin_info", JSON.stringify(admin))
  if (!canUse(state.active)) {
    state.active = firstMenuForAdmin(admin)
  }
  return { admin, activeChanged: previousActive !== state.active }
}

async function syncAdminProfile() {
  if (!isLoggedIn.value || state.loading) return
  const before = JSON.stringify(state.admin?.permissions || [])
  try {
    const { activeChanged } = await refreshAdminProfile()
    const after = JSON.stringify(state.admin?.permissions || [])
    if (before !== after) {
      ElMessage.info("当前账号权限已同步")
      if (activeChanged) await loadPage(true)
    }
  } catch (error) {
    console.warn(error)
  }
}

function startProfileRefresh() {
  stopProfileRefresh()
  profileRefreshTimer = window.setInterval(syncAdminProfile, PROFILE_REFRESH_INTERVAL_MS)
}

function stopProfileRefresh() {
  if (profileRefreshTimer) {
    window.clearInterval(profileRefreshTimer)
    profileRefreshTimer = null
  }
}

async function restoreSession() {
  if (!state.token) {
    resetRobotVerification()
    state.booting = false
    return
  }

  try {
    await refreshAdminProfile()
    await loadPage(true)
  } catch {
    clearSession()
    resetRobotVerification()
  } finally {
    state.booting = false
  }
}

async function selectPage(key) {
  if (!canUse(key)) {
    state.active = firstMenuForAdmin(state.admin)
    return
  }
  if (state.active === key) return
  state.active = key
  state.detail = null
  state.keyword = ""
  await nextTick()
  await loadPage()
}

async function loadPage(initial = false) {
  if (!isLoggedIn.value) return
  state.loading = true

  try {
    if (initial || state.active === "overview") await loadOverview()
    if (state.active === "decision") await loadDecision()
    if (state.active === "trend") await loadTrend()
    if (state.active === "region") await loadRegion()
    if (state.active === "profile") await loadProfile()
    if (state.active === "value") await loadValue()
    if (state.active === "segments") await loadSegments()
    if (state.active === "insights") await loadInsights()
    if (state.active === "songs") await loadSongs()
    if (state.active === "feedback") await loadFeedback()
    if (state.active === "devices") await loadDevices()
    if (state.active === "groups") await loadGroups()
    if (state.active === "alerts") await loadAlerts()
    if (state.active === "logs") await loadLogs()
    if (state.active === "users") await loadUsers()
    if (state.active === "roles") await loadRoles()
    if (state.active === "system") await loadSettings()
    if (state.active === "notices") await loadNotices()
    if (state.active === "audit") await loadAudit()
    if (state.active === "account") await loadAccount()
    setUpdated()
  } catch (error) {
    ElMessage.error(error.message || "数据加载失败")
  } finally {
    state.loading = false
  }
}

async function loadOverview() {
  if (currentRole.value === "super_admin" || currentRole.value === "boss") {
    const [user, device, sales, activity, trend, songs, feedback, salesRegion] = await Promise.all([
      silent(() => api("/api/admin/super/overview/user-count"), {}),
      silent(() => api("/api/admin/super/overview/device-count"), {}),
      silent(() => api("/api/admin/super/overview/sales-amount"), {}),
      silent(() => api("/api/admin/super/overview/activity-rate"), {}),
      silent(() => api("/api/admin/super/trend/growth", { params: { type: "device", dimension: "day" } }), { list: [] }),
      silent(() => api("/api/admin/market/top-songs"), { list: [] }),
      silent(() => api("/api/admin/super/feedback/list", { params: { page: 1, pageSize: 5 } }), { list: [], total: 0 }),
      silent(() => api("/api/admin/super/region/sales-heatmap"), { list: [] }),
    ])
    state.overview = { user, device, sales, activity }
    state.trend = trend
    state.songs = songs.list || []
    state.feedback = feedback
    state.region.sales = salesRegion.list || []
    return
  }

  if (currentRole.value === "market_admin") {
    await Promise.all([loadSongs(), loadValue(), loadRetention(), loadRegion(), loadProfile(), loadDecision()])
    state.trend = {
      type: "retention",
      dimension: "day",
      list: state.retention.map((item) => ({
        date: item.date,
        value: Math.round(Number(item.day7RetentionRate || 0) * 100),
      })),
    }
    return
  }

  await Promise.all([loadDevices(), loadFeedback(), loadLogs(), loadAlerts()])
}

async function loadDecision() {
  const prefix = currentRole.value === "market_admin" ? "/api/admin/market" : "/api/admin/super"
  state.decision = await api(`${prefix}/decision/summary`)
}

async function loadTrend() {
  if (currentRole.value === "super_admin" || currentRole.value === "boss") {
    state.trend = await api("/api/admin/super/trend/growth", {
      params: { type: state.trend.type || "user", dimension: state.trend.dimension || "day" },
    })
  } else if (currentRole.value === "market_admin") {
    await loadRetention()
    state.trend = {
      type: "retention",
      dimension: "day",
      list: state.retention.map((item) => ({ date: item.date, value: Math.round(Number(item.day7RetentionRate || 0) * 100) })),
    }
  } else {
    await loadLogs()
  }
}

async function loadRegion() {
  const prefix = currentRole.value === "market_admin" ? "/api/admin/market" : "/api/admin/super"
  const [sales, users] = await Promise.all([
    silent(() => api(`${prefix}/region/sales-heatmap`), { list: [] }),
    silent(() => api(`${prefix}/region/user-heatmap`), { list: [] }),
  ])
  state.region.sales = sales.list || []
  state.region.users = users.list || []
}

async function loadProfile() {
  const prefix = currentRole.value === "market_admin" ? "/api/admin/market" : "/api/admin/super"
  const [age, region, activity, service] = await Promise.all([
    silent(() => api(`${prefix}/user-profile/age-distribution`), { list: [] }),
    silent(() => api(`${prefix}/user-profile/region-distribution`), { list: [] }),
    silent(() => api(`${prefix}/user-profile/activity-distribution`), { list: [] }),
    silent(() => api(`${prefix}/user-profile/music-service-distribution`), { list: [] }),
  ])
  state.profile.age = age.list || []
  state.profile.region = region.list || []
  state.profile.activity = activity.list || []
  state.profile.service = service.list || []
}

async function loadValue() {
  const prefix = currentRole.value === "market_admin" ? "/api/admin/market" : "/api/admin/super"
  const [normal, high] = await Promise.all([
    silent(() => api(`${prefix}/user-value/normal-users`), {}),
    silent(() => api(`${prefix}/user-value/high-active-users`), {}),
  ])
  state.value = { ...normal, ...high }
}

async function loadSongs() {
  const data = await api("/api/admin/market/top-songs")
  state.songs = data.list || []
}

async function loadRetention() {
  const data = await api("/api/admin/market/retention/device-purchase")
  state.retention = data.list || []
}

async function loadSegments() {
  state.segments = await api("/api/admin/market/segments")
}

async function loadInsights() {
  state.insights = await api("/api/admin/market/insights")
}

async function loadFeedback() {
  const prefix = currentRole.value === "operator_admin" ? "/api/admin/operator" : "/api/admin/super"
  state.feedback = await api(`${prefix}/feedback/list`, { params: { page: 1, pageSize: 20 } })
}

async function refreshFeedback() {
  if (state.feedbackLoading) return
  state.feedbackLoading = true
  try {
    await loadFeedback()
    ElMessage.success(`已刷新，共 ${state.feedback.total || 0} 条反馈`)
  } catch (error) {
    ElMessage.error("刷新失败，请稍后重试")
  } finally {
    state.feedbackLoading = false
  }
}

async function loadDevices() {
  state.devices = await api("/api/admin/operator/device/list")
  const first = state.devices.list?.[0]
  if (first) {
    state.selectedDeviceId = state.selectedDeviceId || first.deviceId
    await showDeviceDetail(state.devices.list.find((item) => item.deviceId === state.selectedDeviceId) || first)
    state.runtime = await silent(
      () => api("/api/admin/operator/device/runtime-status", { params: { deviceId: state.selectedDeviceId } }),
      null,
    )
  }
}

async function loadGroups() {
  state.groups = await api("/api/admin/operator/device/groups")
}

async function loadAlerts() {
  state.alerts = await api("/api/admin/operator/device/alerts")
}

async function loadLogs() {
  state.logs = await api("/api/admin/operator/device/logs", { params: { page: 1, pageSize: 20 } })
}

async function loadUsers() {
  state.users = await api("/api/admin/super/users")
}

async function loadRoles() {
  state.roles = await api("/api/admin/super/roles")
}

function openRoleEditor(role) {
  state.roleEditor = {
    open: true,
    role: role.role,
    roleName: role.roleName,
    selected: [...(role.permissions || [])],
    saving: false,
  }
}

function closeRoleEditor() {
  state.roleEditor.open = false
}

function toggleRolePermission(key) {
  const selected = state.roleEditor.selected
  const index = selected.indexOf(key)
  if (index >= 0) selected.splice(index, 1)
  else selected.push(key)
}

async function saveRolePermissions() {
  state.roleEditor.saving = true
  try {
    const data = await api("/api/admin/super/roles/permissions", {
      method: "POST",
      body: { role: state.roleEditor.role, permissions: state.roleEditor.selected },
    })
    if (data?.list) state.roles.list = data.list
    if (Array.isArray(data?.currentPermissions) && state.admin) {
      state.admin.permissions = data.currentPermissions
      state.admin.permissionsUpdatedAt = data.updatedAt || state.admin.permissionsUpdatedAt
      localStorage.setItem("admin_info", JSON.stringify(state.admin))
    }
    ElMessage.success(`角色权限已更新，已应用到 ${data?.affectedUserCount ?? 0} 个账号`)
    state.roleEditor.open = false
  } catch (error) {
    ElMessage.error(error.message || "保存失败")
  } finally {
    state.roleEditor.saving = false
  }
}

function permissionLabel(key) {
  return state.roles.catalog?.find((item) => item.key === key)?.label || key
}

function openUserCreate() {
  state.userEditor = {
    open: true,
    mode: "create",
    saving: false,
    original: "",
    form: { username: "", password: "", role: "operator_admin", realName: "", phone: "", email: "", jobNo: "" },
  }
}

function openUserEdit(user) {
  state.userEditor = {
    open: true,
    mode: "edit",
    saving: false,
    original: user.username,
    form: {
      username: user.username,
      password: "",
      role: user.role,
      realName: user.realName || "",
      phone: user.phone || "",
      email: user.email || "",
      jobNo: user.jobNo && user.jobNo !== "-" ? user.jobNo : "",
    },
  }
}

function closeUserEditor() {
  state.userEditor.open = false
}

async function saveUserEditor() {
  const form = state.userEditor.form
  const isCreate = state.userEditor.mode === "create"
  if (!form.username.trim()) {
    ElMessage.warning("请输入用户名")
    return
  }
  if (isCreate && !form.password.trim()) {
    ElMessage.warning("请设置初始密码")
    return
  }
  state.userEditor.saving = true
  try {
    const path = isCreate ? "/api/admin/super/users/create" : "/api/admin/super/users/update"
    const body = {
      username: form.username.trim(),
      role: form.role,
      realName: form.realName.trim(),
      phone: form.phone.trim(),
      email: form.email.trim(),
      jobNo: form.jobNo.trim(),
    }
    if (form.password.trim()) body.password = form.password.trim()
    await api(path, { method: "POST", body })
    ElMessage.success(isCreate ? "账号已创建" : "账号已更新")
    state.userEditor.open = false
    await loadUsers()
  } catch (error) {
    ElMessage.error(error.message || "保存失败")
  } finally {
    state.userEditor.saving = false
  }
}

async function deleteUser(user) {
  try {
    await ElMessageBox.confirm(
      `确定删除账号「${user.realName} · ${user.username}」吗？该操作不可恢复。`,
      "删除管理员账号",
      { type: "warning", confirmButtonText: "删除", cancelButtonText: "取消" },
    )
  } catch {
    return
  }
  try {
    await api("/api/admin/super/users/delete", { method: "POST", body: { username: user.username } })
    ElMessage.success("账号已删除")
    await loadUsers()
  } catch (error) {
    ElMessage.error(error.message || "删除失败")
  }
}

async function loadSettings() {
  state.settings = await api("/api/admin/super/system/config")
}

async function loadNotices() {
  state.notices = await api("/api/admin/super/notices")
}

async function loadAudit() {
  state.audit = await api("/api/admin/super/security/logs")
}

async function loadAccount() {
  state.admin = await api("/api/admin/profile")
  localStorage.setItem("admin_info", JSON.stringify(state.admin))
}

function resetPasswordForm() {
  state.passwordForm = { currentPassword: "", newPassword: "", confirmPassword: "" }
}

async function changePassword() {
  const form = state.passwordForm
  if (!form.currentPassword || !form.newPassword || !form.confirmPassword) {
    ElMessage.warning("请完整填写密码信息")
    return
  }
  if (form.newPassword.length < 6 || form.newPassword.length > 32) {
    ElMessage.warning("新密码长度需为 6 到 32 位")
    return
  }
  if (form.newPassword !== form.confirmPassword) {
    ElMessage.warning("两次输入的新密码不一致")
    return
  }

  state.passwordSaving = true
  try {
    const profile = await api("/api/admin/password", {
      method: "POST",
      body: {
        currentPassword: form.currentPassword,
        newPassword: form.newPassword,
        confirmPassword: form.confirmPassword,
      },
    })
    state.admin = profile
    localStorage.setItem("admin_info", JSON.stringify(state.admin))
    resetPasswordForm()
    ElMessage.success("密码已更新")
  } catch (error) {
    ElMessage.error(error.message || "密码修改失败")
  } finally {
    state.passwordSaving = false
  }
}

async function showFeedbackDetail(item) {
  const prefix = currentRole.value === "operator_admin" ? "/api/admin/operator" : "/api/admin/super"
  state.detail = await api(`${prefix}/feedback/detail`, { params: { feedbackId: item.feedbackId } })
}

async function handleFeedback(item) {
  await api("/api/admin/operator/feedback/handle", {
    method: "POST",
    body: { feedbackId: item.feedbackId, status: "processed", remark: "后台已处理" },
  })
  ElMessage.success("反馈状态已更新")
  await loadFeedback()
}

async function showDeviceDetail(item) {
  state.selectedDeviceId = item.deviceId
  state.detail = await api("/api/admin/operator/device/detail", { params: { deviceId: item.deviceId } })
  state.detail.boundUser = await silent(
    () => api("/api/admin/operator/device/bound-user", { params: { deviceId: item.deviceId } }),
    null,
  )
}

async function selectDeviceById(deviceId) {
  const item = (state.devices.list || []).find((device) => device.deviceId === deviceId)
  if (item) await showDeviceDetail(item)
}

async function showDeviceUser(item) {
  state.deviceUser = { open: true, loading: true, info: null, deviceName: item.deviceName }
  state.deviceUser.info = await silent(
    () => api("/api/admin/operator/device/bound-user", { params: { deviceId: item.deviceId } }),
    null,
  )
  state.deviceUser.loading = false
}

function closeDeviceUser() {
  state.deviceUser = { open: false, loading: false, info: null, deviceName: "" }
}

async function showLogDetail(item) {
  state.detail = await api("/api/admin/operator/device/log-detail", { params: { logId: item.logId } })
}

async function renameDevice(item) {
  try {
    const { value } = await ElMessageBox.prompt("请输入新的设备名称", "重命名设备", {
      inputValue: item.deviceName,
      confirmButtonText: "保存",
      cancelButtonText: "取消",
    })
    await api("/api/admin/operator/device/rename", {
      method: "POST",
      body: { deviceId: item.deviceId, name: value },
    })
    ElMessage.success("设备名称已更新")
    await loadDevices()
  } catch (error) {
    if (!error?.action && error !== "cancel") ElMessage.error(error.message || "重命名失败")
  }
}

async function unbindDevice(item) {
  try {
    await ElMessageBox.confirm(`确定解绑「${item.deviceName}」吗？`, "解绑设备", {
      type: "warning",
      confirmButtonText: "解绑",
      cancelButtonText: "取消",
    })
    await api("/api/admin/operator/device/unbind", {
      method: "POST",
      body: { deviceId: item.deviceId },
    })
    ElMessage.success("设备已解绑")
    await loadDevices()
  } catch (error) {
    if (!error?.action && error !== "cancel") ElMessage.error(error.message || "解绑失败")
  }
}

async function saveSystemConfig() {
  state.settings = await api("/api/admin/super/system/config", {
    method: "POST",
    body: state.settings,
  })
  ElMessage.success("系统配置已保存")
}

async function createNotice() {
  try {
    const { value } = await ElMessageBox.prompt("请输入公告标题", "发布系统公告", {
      inputValue: "设备维护通知",
      confirmButtonText: "创建",
      cancelButtonText: "取消",
    })
    const notice = await api("/api/admin/super/notices", {
      method: "POST",
      body: { title: value, type: "notice", status: "draft" },
    })
    if (notice?.noticeId) {
      state.notices = {
        total: (state.notices.total || 0) + 1,
        list: [notice, ...(state.notices.list || []).filter((item) => item.noticeId !== notice.noticeId)],
      }
    }
    ElMessage.success("公告已创建")
    await loadNotices()
  } catch (error) {
    if (!error?.action && error !== "cancel") ElMessage.error(error.message || "公告创建失败")
  }
}

function exportRows(filename, rows) {
  const list = Array.isArray(rows) ? rows : []
  if (!list.length) {
    ElMessage.warning("暂无可导出数据")
    return
  }
  const keys = Array.from(new Set(list.flatMap((row) => Object.keys(row))))
  const csv = [
    keys.join(","),
    ...list.map((row) =>
      keys
        .map((key) => {
          const value = row[key]
          const text = typeof value === "object" ? JSON.stringify(value) : String(value ?? "")
          return `"${text.replaceAll('"', '""')}"`
        })
        .join(","),
    ),
  ].join("\n")
  const blob = new Blob([`\ufeff${csv}`], { type: "text/csv;charset=utf-8" })
  const url = URL.createObjectURL(blob)
  const link = document.createElement("a")
  link.href = url
  link.download = filename
  link.click()
  URL.revokeObjectURL(url)
  ElMessage.success("导出文件已生成")
}

onMounted(async () => {
  await restoreSession()
  if (isLoggedIn.value) startProfileRefresh()
})
onUnmounted(stopProfileRefresh)
</script>

<template>
  <div v-if="state.booting" class="boot-screen">
    <div class="boot-card">正在唤醒声盒后台...</div>
  </div>

  <main v-else-if="!isLoggedIn" class="login-shell">
    <section class="login-brand">
      <div class="brand-mark"><i class="fa-solid fa-leaf"></i></div>
      <p class="eyebrow">Smart Speaker Console</p>
      <h1>声盒 Mini</h1>
      <p>智能音箱设备、音乐运营、用户反馈与系统配置的统一后台。</p>
    </section>

    <section class="login-panel" @keyup.enter="handleLogin">
      <p class="eyebrow">Welcome back</p>
      <h2>登录后台</h2>
      <label class="field">
        <span>用户名</span>
        <span class="field-input">
          <i class="fa-solid fa-user"></i>
          <input v-model="state.loginForm.username" autocomplete="username" placeholder="请输入用户名" />
        </span>
      </label>
      <label class="field">
        <span>密码</span>
        <span class="field-input">
          <i class="fa-solid fa-lock"></i>
          <input v-model="state.loginForm.password" autocomplete="current-password" type="password" placeholder="请输入密码" />
        </span>
      </label>
      <div class="robot-check-wrap">
        <button
          type="button"
          :class="['robot-check-card', { verified: state.loginForm.captchaVerified }]"
          :disabled="state.loginForm.captchaLoading || state.loading"
          @click="verifyRobot"
        >
          <span class="robot-checkbox">
            <i v-if="state.loginForm.captchaVerified" class="fa-solid fa-check"></i>
            <i v-else-if="state.loginForm.captchaLoading" class="fa-solid fa-rotate-right spin"></i>
          </span>
          <span class="robot-label">{{ state.loginForm.captchaVerified ? "验证通过" : "我不是机器人" }}</span>
          <span class="robot-badge">
            <i class="fa-solid fa-shield-halved"></i>
            <strong>声盒验证</strong>
            <small>Privacy - Terms</small>
          </span>
        </button>
      </div>
      <label class="check-row">
        <input v-model="state.loginForm.remember" type="checkbox" />
        <span>记住用户名</span>
      </label>
      <button class="primary-button" :disabled="state.loading" @click="handleLogin">
        <i class="fa-solid fa-right-to-bracket"></i>
        {{ state.loading ? "登录中..." : "账号登录" }}
      </button>
      <p class="api-note"><i class="fa-solid fa-link"></i> API：{{ apiLabel }}</p>
    </section>
  </main>

  <main v-else class="app-shell">
    <aside class="sidebar">
      <div class="brand">
        <div class="logo"><i class="fa-solid fa-leaf"></i></div>
        <div>
          <strong>声盒 Mini</strong>
          <small>后台管理系统</small>
        </div>
      </div>

      <nav class="nav-groups">
        <section v-for="group in groupedMenus" :key="group.section">
          <p>{{ group.section }}</p>
          <button
            v-for="item in group.items"
            :key="item.key"
            :class="['nav-item', { active: state.active === item.key }]"
            @click="selectPage(item.key)"
          >
            <i :class="['fa-solid', item.icon]"></i>
            <span>{{ item.label }}</span>
          </button>
        </section>
      </nav>

      <div class="user-card">
        <div class="avatar">{{ state.admin?.username?.slice(0, 1).toUpperCase() }}</div>
        <div>
          <strong>{{ state.admin?.realName || state.admin?.username }}</strong>
          <small>{{ currentRoleName }}</small>
        </div>
        <button @click="handleLogout"><i class="fa-solid fa-arrow-right-from-bracket"></i></button>
      </div>
    </aside>

    <section class="content">
      <header class="topbar">
        <div>
          <p class="eyebrow">{{ currentRoleName }}</p>
          <h1><i :class="['fa-solid', activeMenu.icon]"></i> {{ activeMenu.label }}</h1>
          <p class="muted"><i class="fa-solid fa-clock-rotate-left"></i> 最近同步：{{ state.lastUpdated || "等待刷新" }}</p>
        </div>
        <div class="top-actions">
          <label class="search">
            <i class="fa-solid fa-magnifying-glass"></i>
            <input v-model="state.keyword" placeholder="设备、反馈、用户..." />
          </label>
          <button class="ghost-button" :disabled="state.loading" @click="loadPage()">
            <i :class="['fa-solid fa-rotate', { spin: state.loading }]"></i> 刷新
          </button>
        </div>
      </header>

      <section class="metrics-grid">
        <article v-for="card in metricCards" :key="card.label" :class="['metric-card', card.tone]">
          <p class="metric-title">{{ card.label }} <i :class="['fa-solid', card.icon]"></i></p>
          <strong>{{ card.value }}</strong>
          <span class="metric-trend">{{ card.hint }}</span>
        </article>
      </section>

      <section v-if="state.active === 'overview'" class="dashboard-grid">
        <article class="panel">
          <div class="panel-head">
            <div>
              <h3>{{ currentRole === 'operator_admin' ? '设备运行概览' : '增长趋势' }}</h3>
              <p>{{ currentRole === 'operator_admin' ? '点击设备名称查看绑定用户详情' : `当前指标：${trendMetricName}` }}</p>
            </div>
          </div>
          <div v-if="currentRole === 'operator_admin'" class="device-overview">
            <div
              v-for="item in (state.devices.list || [])"
              :key="item.deviceId"
              class="device-overview-row"
            >
              <button class="device-name-btn" :title="`查看「${item.deviceName}」绑定用户详情`" @click="showDeviceUser(item)">
                <i :class="['dot', { online: item.online }]"></i>
                <span class="device-name-text">
                  <strong>{{ item.deviceName }}</strong>
                  <small>编号：{{ item.deviceSn || item.deviceId }}</small>
                </span>
              </button>
              <span :class="['device-status', { online: item.online }]">{{ item.online ? "在线" : "离线" }}</span>
            </div>
            <p v-if="!(state.devices.list || []).length" class="muted">暂无设备数据。</p>
          </div>
          <div v-else class="chart-with-axis">
            <p class="axis-unit">{{ trendMetricName }}（单位：{{ trendUnit }}）</p>
            <div class="chart-row">
              <div class="y-ticks">
                <span v-for="tick in trendAxis.ticks" :key="tick" class="y-tick">{{ formatAxis(tick) }}</span>
              </div>
              <div class="plot">
                <div class="plot-area">
                  <span
                    v-for="tick in trendAxis.ticks"
                    :key="`g-${tick}`"
                    class="gridline"
                    :style="{ bottom: `${(tick / trendAxis.niceMax) * 100}%` }"
                  ></span>
                  <div v-for="item in state.trend.list" :key="item.date" class="bar-col">
                    <div
                      class="bar"
                      :style="{ height: `${(Number(item.value || 0) / trendAxis.niceMax) * 100}%` }"
                      :title="`${item.value} ${trendUnit}`"
                    ></div>
                  </div>
                </div>
                <div class="x-labels">
                  <div v-for="item in state.trend.list" :key="`x-${item.date}`" class="x-label">
                    <span>{{ labelDate(item.date) }}</span>
                    <small>{{ item.value }}</small>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </article>

        <article class="panel">
          <div class="panel-head"><div><h3>{{ currentRole === 'operator_admin' ? '待处理反馈' : '热歌排行' }}</h3><p>用于快速发现运营重点</p></div></div>
          <ul v-if="currentRole !== 'operator_admin'" class="rank-list">
            <li v-for="song in state.songs.slice(0, 6)" :key="`${song.rank}-${song.songName}`">
              <span>{{ song.rank }}</span>
              <strong>{{ song.songName }}</strong>
              <em>{{ formatNumber(song.playCount) }}</em>
            </li>
          </ul>
          <ul v-else class="rank-list">
            <li v-for="item in state.feedback.list.slice(0, 6)" :key="item.feedbackId">
              <span>{{ item.rating || 4 }}</span>
              <strong>{{ item.content }}</strong>
              <em>{{ item.statusText }}</em>
            </li>
          </ul>
        </article>
      </section>

      <section v-if="state.active === 'decision'" class="dashboard-grid">
        <article class="panel full">
          <div class="panel-head"><div><h3>管理决策指标</h3><p>播放、用户、设备与异常提醒</p></div></div>
          <div class="mini-cards">
            <div v-for="card in state.decision.cards" :key="card.label">
              <span>{{ card.label }}</span>
              <strong>{{ card.value }}</strong>
              <em>{{ card.trend }}</em>
            </div>
          </div>
        </article>
        <article class="panel">
          <div class="panel-head"><div><h3>每日播放次数趋势</h3><p>每天播放记录总次数，来自 daily_stats.total_play_count</p></div></div>
          <div class="bar-chart">
            <div v-for="item in state.decision.trend" :key="item.stat_date" class="bar-item">
              <div class="bar" :style="{ height: barHeight(item.total_play_count, maxOf(state.decision.trend, 'total_play_count')) }"></div>
              <span>{{ labelDate(item.stat_date) }}</span>
              <small>{{ item.total_play_count }}</small>
            </div>
          </div>
        </article>
        <article class="panel">
          <div class="panel-head"><div><h3>异常提醒</h3><p>销售、活跃、设备、差评</p></div></div>
          <ul class="pill-list">
            <li v-for="risk in state.decision.risks" :key="risk.name" class="pill-row">
              <strong>{{ risk.name }}</strong><span :class="['badge', risk.level]">{{ risk.value }}</span>
            </li>
          </ul>
        </article>
      </section>

      <section v-if="state.active === 'trend'" class="panel full">
        <div class="panel-head">
          <div><h3>{{ currentRole === 'operator_admin' ? '设备日志趋势' : '增长趋势分析' }}</h3><p>按用户、设备、销售或留存查看趋势</p></div>
          <div v-if="currentRole === 'super_admin' || currentRole === 'boss'" class="segmented">
            <button :class="{ active: state.trend.type === 'user' }" @click="state.trend.type = 'user'; loadTrend()">用户</button>
            <button :class="{ active: state.trend.type === 'device' }" @click="state.trend.type = 'device'; loadTrend()">设备</button>
            <button :class="{ active: state.trend.type === 'sales' }" @click="state.trend.type = 'sales'; loadTrend()">销售</button>
          </div>
        </div>
        <div v-if="currentRole === 'operator_admin'" class="data-table">
          <div v-for="log in state.logs.list" :key="log.logId" class="table-row" @click="showLogDetail(log)">
            <strong>{{ log.deviceName }}</strong><span>{{ log.content }}</span><em>{{ log.createdAt }}</em>
          </div>
        </div>
        <div v-else class="chart-with-axis">
          <p class="axis-unit">{{ trendMetricName }}（单位：{{ trendUnit }}）</p>
          <div class="chart-row">
            <div class="y-ticks">
              <span v-for="tick in trendAxis.ticks" :key="tick" class="y-tick">{{ formatAxis(tick) }}</span>
            </div>
            <div class="plot">
              <div class="plot-area">
                <span
                  v-for="tick in trendAxis.ticks"
                  :key="`g-${tick}`"
                  class="gridline"
                  :style="{ bottom: `${(tick / trendAxis.niceMax) * 100}%` }"
                ></span>
                <div v-for="item in state.trend.list" :key="item.date" class="bar-col">
                  <div
                    class="bar"
                    :style="{ height: `${(Number(item.value || 0) / trendAxis.niceMax) * 100}%` }"
                    :title="`${item.value} ${trendUnit}`"
                  ></div>
                </div>
              </div>
              <div class="x-labels">
                <div v-for="item in state.trend.list" :key="`x-${item.date}`" class="x-label">
                  <span>{{ labelDate(item.date) }}</span>
                  <small>{{ item.value }}</small>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      <section v-if="state.active === 'region'" class="two-column">
        <article class="panel">
          <div class="panel-head"><div><h3>销售额分布</h3><p>按地区查看销售热度</p></div></div>
          <div class="heat-list">
            <div v-for="item in state.region.sales" :key="item.regionCode" class="heat-row">
              <span>{{ item.regionName }}</span>
              <div><i :style="{ width: `${Math.max(10, (item.salesAmount / maxOf(state.region.sales, 'salesAmount')) * 100)}%` }"></i></div>
              <strong>{{ money(item.salesAmount) }}</strong>
            </div>
          </div>
        </article>
        <article class="panel">
          <div class="panel-head"><div><h3>用户分布</h3><p>按地区查看用户与活跃用户</p></div></div>
          <div class="heat-list">
            <div v-for="item in state.region.users" :key="item.regionCode" class="heat-row">
              <span>{{ item.regionName }}</span>
              <div><i :style="{ width: `${Math.max(10, (item.userCount / maxOf(state.region.users, 'userCount')) * 100)}%` }"></i></div>
              <strong>{{ formatNumber(item.userCount) }}</strong>
            </div>
          </div>
        </article>
      </section>

      <section v-if="state.active === 'profile'" class="profile-grid">
        <article v-for="[title, list, key] in [
          ['年龄分布', state.profile.age, 'ageRange'],
          ['地区分布', state.profile.region, 'regionName'],
          ['活跃分层', state.profile.activity, 'levelName'],
          ['绑定软件', state.profile.service, 'serviceName'],
        ]" :key="title" class="panel">
          <div class="panel-head"><div><h3>{{ title }}</h3><p>饼图占比数据</p></div></div>
          <div class="profile-pie">
            <svg viewBox="0 0 120 120">
              <path
                v-for="slice in pieSlices(list, key)"
                :key="slice.label"
                :d="slice.d"
                :fill="slice.color"
                stroke="rgba(255,255,255,0.85)"
                stroke-width="1"
              />
            </svg>
          </div>
          <ul class="pill-list">
            <li v-for="slice in pieSlices(list, key)" :key="slice.label" class="pill-row">
              <span class="legend-dot" :style="{ background: slice.color }"></span>
              <strong>{{ slice.label }}</strong>
              <span>{{ formatNumber(slice.count) }}</span>
              <b>{{ percent(slice.ratio) }}</b>
            </li>
          </ul>
        </article>
      </section>

      <section v-if="state.active === 'value'" class="value-layout">
        <article class="panel donut-panel">
          <div class="panel-head"><div><h3>用户价值构成</h3><p>普通用户与高活跃用户占比</p></div></div>
          <div class="donut-body">
            <div class="donut-chart">
              <svg viewBox="0 0 120 120">
                <circle class="donut-track" cx="60" cy="60" r="52" />
                <circle
                  v-for="seg in valueDonut.segments"
                  :key="seg.label"
                  class="donut-arc"
                  cx="60"
                  cy="60"
                  r="52"
                  :stroke="seg.color"
                  :stroke-dasharray="`${seg.dash} ${seg.gap}`"
                  :stroke-dashoffset="seg.dashOffset"
                />
              </svg>
              <div class="donut-center">
                <small>用户总量</small>
                <strong>{{ formatNumber(valueDonut.total) }}</strong>
              </div>
            </div>
            <ul class="donut-legend">
              <li v-for="seg in valueDonut.segments" :key="seg.label">
                <span class="legend-dot" :style="{ background: seg.color }"></span>
                <span class="legend-label">{{ seg.label }}</span>
                <em>{{ formatNumber(seg.value) }}</em>
                <b>{{ percent(seg.ratio) }}</b>
              </li>
            </ul>
          </div>
        </article>
        <div class="two-column">
          <article class="panel hero-number">
            <span>普通用户</span>
            <strong>{{ formatNumber(state.value.normalUserCount || 0) }}</strong>
            <p>适合基础推荐、设备使用引导和新功能教育。</p>
          </article>
          <article class="panel hero-number">
            <span>高活跃用户</span>
            <strong>{{ formatNumber(state.value.highActiveUserCount || 0) }}</strong>
            <p>适合会员权益、歌单推荐和复购活动触达。</p>
          </article>
        </div>
      </section>

      <section v-if="state.active === 'segments'" class="value-layout">
        <article class="panel">
          <div class="panel-head"><div><h3>分群规模占比</h3><p>各运营人群在总量中的分布</p></div></div>
          <div class="donut-body">
            <div class="pie-chart">
              <svg viewBox="0 0 120 120">
                <path
                  v-for="slice in segmentPie.slices"
                  :key="slice.name"
                  :d="slice.d"
                  :fill="slice.color"
                  stroke="rgba(255,255,255,0.85)"
                  stroke-width="1"
                />
              </svg>
            </div>
            <ul class="donut-legend">
              <li v-for="slice in segmentPie.slices" :key="`l-${slice.name}`">
                <span class="legend-dot" :style="{ background: slice.color }"></span>
                <span class="legend-label">{{ slice.name }}</span>
                <em>{{ formatNumber(slice.count) }}</em>
                <b>{{ percent(slice.ratio) }}</b>
              </li>
            </ul>
          </div>
        </article>
        <article class="panel full">
          <div class="panel-head"><div><h3>用户分群</h3><p>按活跃、留存、绑定与偏好建立运营人群</p></div><button class="ghost-button" @click="exportRows('segments.csv', state.segments.list)">导出</button></div>
          <div class="data-table">
            <div v-for="item in state.segments.list" :key="item.name" class="table-row">
              <strong>{{ item.name }}</strong><span>{{ item.rule }} / {{ item.action }}</span><em>{{ formatNumber(item.count) }}</em>
            </div>
          </div>
        </article>
      </section>

      <section v-if="state.active === 'insights'" class="two-column">
        <article class="panel">
          <div class="panel-head"><div><h3>转化漏斗</h3><p>新增、绑定、首播、留存</p></div></div>
          <div class="heat-list">
            <div v-for="item in state.insights.funnels" :key="item.label" class="heat-row">
              <span>{{ item.label }}</span>
              <div><i :style="{ width: `${Math.max(8, item.rate * 100)}%` }"></i></div>
              <strong>{{ formatNumber(item.value) }}</strong>
            </div>
          </div>
        </article>
        <article class="panel">
          <div class="panel-head"><div><h3>运营建议</h3><p>基于现有运营数据</p></div></div>
          <ul class="pill-list">
            <li v-for="item in state.insights.recommendations" :key="item" class="pill-row"><strong>{{ item }}</strong></li>
          </ul>
        </article>
      </section>

      <section v-if="state.active === 'songs'" class="panel full">
        <div class="panel-head"><div><h3>热歌排行</h3><p>播放量、用户数与平台来源</p></div><button class="ghost-button" @click="exportRows('songs.csv', state.songs)">导出</button></div>
        <div class="data-table scroll-list notice-scroll">
          <div v-for="song in state.songs" :key="`${song.rank}-${song.songName}`" class="table-row">
            <strong>#{{ song.rank }} {{ song.songName }}</strong>
            <span>{{ song.artist }} / {{ song.platform }}</span>
            <em>{{ formatNumber(song.playCount) }} 次</em>
          </div>
        </div>
      </section>

      <section v-if="state.active === 'feedback'" class="two-column detail-layout">
        <article class="panel">
          <div class="panel-head">
            <div><h3>用户反馈</h3><p>共 {{ state.feedback.total }} 条</p></div>
            <button class="ghost-button compact" :disabled="state.feedbackLoading" @click="refreshFeedback">
              <i :class="['fa-solid fa-rotate-right', { spinning: state.feedbackLoading }]"></i>
              {{ state.feedbackLoading ? '刷新中' : '刷新' }}
            </button>
          </div>
          <div class="data-table scroll-list feedback-scroll">
            <div v-for="item in filteredFeedback" :key="item.feedbackId" class="table-row" @click="showFeedbackDetail(item)">
              <strong>{{ item.nickname }}</strong><span>{{ item.content }}</span><em>{{ item.statusText }}</em>
            </div>
          </div>
        </article>
        <article class="panel detail-card">
          <h3>反馈详情</h3>
          <template v-if="state.detail?.feedbackInfo">
            <p>{{ state.detail.feedbackInfo.title }}</p>
            <strong>{{ state.detail.userInfo?.nickname }}</strong>
            <span>{{ state.detail.feedbackInfo.content }}</span>
            <small>状态：{{ state.detail.processInfo?.statusText }} / 评分：{{ state.detail.processInfo?.ratingText }}</small>
            <button class="primary-button compact" @click="handleFeedback(state.detail)">标记已处理</button>
          </template>
          <p v-else class="muted">选择一条反馈查看详情。</p>
        </article>
      </section>

      <section v-if="state.active === 'devices'" class="two-column detail-layout">
        <article class="panel">
          <div class="panel-head"><div><h3>设备列表</h3><p>共 {{ state.devices.total }} 台设备</p></div></div>
          <el-select
            v-model="state.selectedDeviceId"
            filterable
            class="device-select"
            placeholder="搜索并选择设备"
            @change="selectDeviceById"
          >
            <el-option
              v-for="item in state.devices.list || []"
              :key="item.deviceId"
              :label="`${item.deviceSn} · ${item.deviceName} · ${item.ownerName || '未绑定'}`"
              :value="item.deviceId"
            >
              <div class="device-option">
                <span><i :class="['dot', { online: item.online }]"></i>{{ item.deviceSn }} · {{ item.deviceName }}</span>
                <em>{{ item.modelName }} / {{ item.firmwareVersion }}</em>
              </div>
            </el-option>
          </el-select>
          <div class="data-table scroll-list device-scroll">
            <div
              v-for="item in state.devices.list || []"
              :key="`device-${item.deviceId}`"
              :class="['table-row', 'device-pick-row', { active: item.deviceId === state.selectedDeviceId }]"
              @click="showDeviceDetail(item)"
            >
              <strong><i :class="['dot', { online: item.online }]"></i>{{ item.deviceSn }}</strong>
              <span>{{ item.deviceName }} / {{ item.ownerName || '未绑定' }}</span>
              <em>{{ item.modelName }}</em>
            </div>
          </div>
          <div v-if="state.detail?.deviceId" class="device-actions">
            <button @click="renameDevice(state.detail)">改名</button>
            <button @click="unbindDevice(state.detail)">解绑</button>
          </div>
        </article>
        <article class="panel detail-card">
          <h3>设备详情</h3>
          <template v-if="state.detail?.deviceId">
            <strong>{{ state.detail.deviceName }}</strong>
            <span>型号：{{ state.detail.modelName }} / 归属：{{ state.detail.ownerName }}</span>
            <small>音量 {{ state.detail.volume }}，电量 {{ state.detail.battery }}%，网络 {{ state.detail.currentNetwork }}</small>
            <small>最近在线：{{ state.detail.lastOnlineAt }}</small>
            <small v-if="state.detail.boundUser?.userId">绑定用户：{{ state.detail.boundUser.nickname }} / {{ state.detail.boundUser.region }}</small>
            <small v-if="state.detail.unbindMeaning">{{ state.detail.unbindMeaning }}</small>
          </template>
          <p v-else class="muted">选择设备查看基础信息、绑定用户和实时状态。</p>
        </article>
      </section>

      <section v-if="state.active === 'groups'" class="panel full">
        <div class="panel-head"><div><h3>设备分组</h3><p>共 {{ state.groups.total || 0 }} 台设备 / {{ state.groups.groupTotal || state.groups.list.length }} 个分组，按型号、固件和在线状态聚合</p></div></div>
        <div class="data-table scroll-list audit-scroll">
          <div v-for="group in state.groups.list" :key="group.groupName" class="table-row">
            <strong>{{ group.groupName }}</strong><span>固件：{{ group.firmwareVersions }} / 离线 {{ group.offlineCount }}</span><em>{{ group.onlineCount }}/{{ group.deviceCount }} 在线</em>
          </div>
        </div>
      </section>

      <section v-if="state.active === 'alerts'" class="panel full">
        <div class="panel-head"><div><h3>设备告警</h3><p>离线、低电量、固件失败、网络异常</p></div></div>
        <div class="data-table">
          <div v-for="item in state.alerts.list" :key="item.alertId" class="table-row">
            <strong>{{ item.title }}</strong><span>{{ item.deviceName }} / {{ item.createdAt }}</span><em>{{ statusText(item.status) }}</em>
          </div>
        </div>
      </section>

      <section v-if="state.active === 'logs'" class="two-column detail-layout">
        <article class="panel">
          <div class="panel-head"><div><h3>设备日志</h3><p>设备上线、升级、异常事件</p></div></div>
          <div class="data-table scroll-list log-scroll">
            <div v-for="log in state.logs.list" :key="log.logId" class="table-row" @click="showLogDetail(log)">
              <strong>{{ log.deviceName }}</strong><span>{{ log.content }}</span><em>{{ log.createdAt }}</em>
            </div>
          </div>
        </article>
        <article class="panel detail-card">
          <h3>日志详情</h3>
          <template v-if="state.detail?.logId">
            <strong>{{ state.detail.title }}</strong>
            <span>{{ state.detail.content }}</span>
            <small>{{ state.detail.eventCode }} / {{ state.detail.traceId }}</small>
          </template>
          <p v-else class="muted">选择日志查看事件编码和链路信息。</p>
        </article>
      </section>

      <section v-if="state.active === 'users'" class="panel full">
        <div class="panel-head">
          <div><h3>管理员与绑定用户</h3><p>账号、角色、状态和最近登录</p></div>
          <div class="modal-buttons">
            <button class="primary-button compact" @click="openUserCreate"><i class="fa-solid fa-user-plus"></i> 新增账号</button>
            <button class="ghost-button" @click="exportRows('users.csv', state.users.list)">导出</button>
          </div>
        </div>
        <div class="data-table">
          <div v-for="user in state.users.list" :key="user.adminId" class="table-row user-row">
            <div class="user-cell">
              <strong>{{ user.realName }} · {{ user.username }}</strong>
              <span>{{ user.roleName }} / {{ user.jobNo }} / {{ user.phone || "未配置手机号" }}</span>
              <small>状态：{{ statusText(user.status) }} / 最近登录：{{ user.lastLoginAt || "-" }}</small>
            </div>
            <div v-if="user.editable" class="row-actions">
              <button class="ghost-button compact" @click="openUserEdit(user)"><i class="fa-solid fa-user-pen"></i> 编辑</button>
              <button class="ghost-button compact danger" @click="deleteUser(user)"><i class="fa-solid fa-trash"></i> 删除</button>
            </div>
            <em v-else>{{ statusText(user.status) }}</em>
          </div>
        </div>
      </section>

      <section v-if="state.active === 'roles'" class="panel full">
        <div class="panel-head"><div><h3>角色权限矩阵</h3><p>创建角色、修改权限、授权与撤权的基础视图</p></div></div>
        <div class="data-table">
          <div v-for="role in state.roles.list" :key="role.role" class="role-row">
            <div class="role-info">
              <strong>{{ role.roleName }}</strong>
              <span>{{ role.description }}</span>
              <div class="perm-tags">
                <span v-for="key in role.permissions" :key="key" class="perm-tag">{{ permissionLabel(key) }}</span>
              </div>
            </div>
            <div class="role-actions">
              <em>{{ role.userCount }} 人</em>
              <button class="ghost-button compact" @click="openRoleEditor(role)">
                <i class="fa-solid fa-user-pen"></i> 编辑权限
              </button>
            </div>
          </div>
        </div>
      </section>

      <section v-if="state.active === 'system'" class="panel full">
        <div class="panel-head"><div><h3>系统全局配置</h3><p>名称、主题、上传限制、接口超时和数据保留</p></div><button class="primary-button compact" @click="saveSystemConfig">保存配置</button></div>
        <div class="form-grid">
          <label class="field"><span>系统名称</span><input v-model="state.settings.systemName" /></label>
          <label class="field"><span>Logo 文案</span><input v-model="state.settings.logoText" /></label>
          <label class="field"><span>默认主题</span><input v-model="state.settings.defaultTheme" /></label>
          <label class="field"><span>上传限制 MB</span><input v-model.number="state.settings.uploadLimitMb" type="number" /></label>
          <label class="field"><span>接口超时 秒</span><input v-model.number="state.settings.apiTimeoutSeconds" type="number" /></label>
          <label class="field"><span>数据保留 天</span><input v-model.number="state.settings.dataRetentionDays" type="number" /></label>
        </div>
      </section>

      <section v-if="state.active === 'notices'" class="panel full">
        <div class="panel-head"><div><h3>系统公告</h3><p>后台公告、维护通知、升级通知</p></div><button class="primary-button compact" @click="createNotice">新建公告</button></div>
        <div class="data-table">
          <div v-for="notice in state.notices.list" :key="notice.noticeId" class="table-row">
            <strong>{{ notice.title }}</strong><span>{{ notice.type }} / {{ notice.createdAt }}</span><em>{{ statusText(notice.status) }}</em>
          </div>
        </div>
      </section>

      <section v-if="state.active === 'audit'" class="panel full audit-panel">
        <div class="panel-head"><div><h3>审计与安全日志</h3><p>操作日志、登录日志、安全事件</p></div><button class="ghost-button" @click="exportRows('audit.csv', state.audit.list)">导出</button></div>
        <div class="data-table">
          <div v-for="log in state.audit.list" :key="log.logId" class="table-row audit-row">
            <div class="audit-main">
              <strong>{{ log.event }}</strong>
              <span>{{ log.operation }} / {{ log.actor }} / {{ log.ip }}</span>
            </div>
            <em>{{ log.createdAt }}</em>
          </div>
        </div>
      </section>

      <section v-if="state.active === 'account'" class="account-layout">
        <article class="panel account-card">
          <div class="avatar big">{{ state.admin?.username?.slice(0, 1).toUpperCase() }}</div>
          <div>
            <h3>{{ state.admin?.realName || state.admin?.username }}</h3>
            <p>{{ state.admin?.position || currentRoleName }} / 工号 {{ state.admin?.jobNo || "-" }}</p>
            <p>{{ state.admin?.phone || "未配置手机号" }} · {{ state.admin?.email || "未配置邮箱" }}</p>
            <p>权限：{{ currentRoleName }}，可访问 {{ visibleMenus.length }} 个后台模块。</p>
          </div>
        </article>
        <article class="panel password-card">
          <div class="panel-head">
            <div>
              <h3>修改密码</h3>
              <p>{{ state.admin?.username }} · {{ currentRoleName }}</p>
            </div>
          </div>
          <form class="password-form" @submit.prevent="changePassword">
            <label>
              <span>当前密码</span>
              <input v-model="state.passwordForm.currentPassword" autocomplete="current-password" type="password" />
            </label>
            <label>
              <span>新密码</span>
              <input v-model="state.passwordForm.newPassword" autocomplete="new-password" type="password" />
            </label>
            <label>
              <span>确认新密码</span>
              <input v-model="state.passwordForm.confirmPassword" autocomplete="new-password" type="password" />
            </label>
            <div class="form-actions">
              <button class="ghost-button compact" type="button" @click="resetPasswordForm">清空</button>
              <button class="primary-button compact" type="submit" :disabled="state.passwordSaving">
                {{ state.passwordSaving ? "保存中..." : "保存新密码" }}
              </button>
            </div>
          </form>
        </article>
      </section>
    </section>

    <div v-if="state.roleEditor.open" class="modal-mask" @click.self="closeRoleEditor">
      <div class="modal-card">
        <div class="panel-head">
          <div>
            <h3>编辑权限 · {{ state.roleEditor.roleName }}</h3>
            <p>勾选该角色可访问的后台功能模块</p>
          </div>
          <button class="icon-close" @click="closeRoleEditor"><i class="fa-solid fa-xmark"></i></button>
        </div>
        <div class="perm-grid">
          <label
            v-for="item in state.roles.catalog"
            :key="item.key"
            :class="['perm-option', { checked: state.roleEditor.selected.includes(item.key) }]"
          >
            <input
              type="checkbox"
              :checked="state.roleEditor.selected.includes(item.key)"
              @change="toggleRolePermission(item.key)"
            />
            <span class="check-box"><i class="fa-solid fa-check"></i></span>
            <span>{{ item.label }}</span>
          </label>
        </div>
        <div class="modal-foot">
          <span class="muted">已选 {{ state.roleEditor.selected.length }} / {{ state.roles.catalog.length }} 项</span>
          <div class="modal-buttons">
            <button class="ghost-button compact" @click="closeRoleEditor">取消</button>
            <button class="primary-button compact" :disabled="state.roleEditor.saving" @click="saveRolePermissions">
              {{ state.roleEditor.saving ? "保存中..." : "保存权限" }}
            </button>
          </div>
        </div>
      </div>
    </div>

    <div v-if="state.userEditor.open" class="modal-mask" @click.self="closeUserEditor">
      <div class="modal-card">
        <div class="panel-head">
          <div>
            <h3>{{ state.userEditor.mode === "create" ? "新增管理员账号" : "编辑账号 · " + state.userEditor.form.username }}</h3>
            <p>{{ state.userEditor.mode === "create" ? "设置账号、初始密码与角色权限" : "可修改密码、角色及资料，留空密码则不变更" }}</p>
          </div>
          <button class="icon-close" @click="closeUserEditor"><i class="fa-solid fa-xmark"></i></button>
        </div>
        <div class="form-grid">
          <label class="field">
            <span>用户名</span>
            <input v-model="state.userEditor.form.username" :disabled="state.userEditor.mode === 'edit'" placeholder="登录用户名" />
          </label>
          <label class="field">
            <span>{{ state.userEditor.mode === "create" ? "初始密码" : "重置密码（留空不改）" }}</span>
            <input v-model="state.userEditor.form.password" type="password" placeholder="登录密码" />
          </label>
          <label class="field">
            <span>角色</span>
            <select v-model="state.userEditor.form.role">
              <option value="super_admin">超级管理员</option>
              <option value="market_admin">市场分析管理员</option>
              <option value="operator_admin">普通管理员</option>
              <option value="boss">老板</option>
            </select>
          </label>
          <label class="field"><span>姓名</span><input v-model="state.userEditor.form.realName" placeholder="真实姓名" /></label>
          <label class="field"><span>工号</span><input v-model="state.userEditor.form.jobNo" placeholder="如 A001" /></label>
          <label class="field"><span>手机号</span><input v-model="state.userEditor.form.phone" placeholder="联系电话" /></label>
          <label class="field"><span>邮箱</span><input v-model="state.userEditor.form.email" placeholder="邮箱地址" /></label>
        </div>
        <div class="modal-foot">
          <span class="muted">角色决定该账号可访问的后台模块</span>
          <div class="modal-buttons">
            <button class="ghost-button compact" @click="closeUserEditor">取消</button>
            <button class="primary-button compact" :disabled="state.userEditor.saving" @click="saveUserEditor">
              {{ state.userEditor.saving ? "保存中..." : "保存账号" }}
            </button>
          </div>
        </div>
      </div>
    </div>

    <div v-if="state.deviceUser.open" class="modal-mask" @click.self="closeDeviceUser">
      <div class="modal-card user-detail-card">
        <div class="panel-head">
          <div>
            <h3>用户详细情况</h3>
            <p>「{{ state.deviceUser.deviceName }}」当前绑定用户</p>
          </div>
          <button class="icon-close" @click="closeDeviceUser"><i class="fa-solid fa-xmark"></i></button>
        </div>
        <p v-if="state.deviceUser.loading" class="muted">加载中...</p>
        <template v-else-if="state.deviceUser.info">
          <div class="user-detail-head">
            <span class="user-avatar">{{ (state.deviceUser.info.nickname || '用户').slice(0, 1) }}</span>
            <div>
              <strong>{{ state.deviceUser.info.nickname }}</strong>
              <small>账号 {{ state.deviceUser.info.username }} · ID {{ state.deviceUser.info.userId }}</small>
            </div>
            <span :class="['user-status-tag', { warn: state.deviceUser.info.status !== '正常' }]">{{ state.deviceUser.info.status }}</span>
          </div>
          <div class="user-detail-grid">
            <div><span>手机号</span><strong>{{ state.deviceUser.info.phone }}</strong></div>
            <div><span>邮箱</span><strong>{{ state.deviceUser.info.email }}</strong></div>
            <div><span>性别</span><strong>{{ state.deviceUser.info.gender }}</strong></div>
            <div><span>年龄</span><strong>{{ state.deviceUser.info.age }}（{{ state.deviceUser.info.ageRange }}）</strong></div>
            <div><span>所在地区</span><strong>{{ state.deviceUser.info.region }}</strong></div>
            <div><span>活跃等级</span><strong>{{ state.deviceUser.info.activeLevel }}</strong></div>
            <div><span>价值分层</span><strong>{{ state.deviceUser.info.valueLevel }}</strong></div>
            <div><span>注册时间</span><strong>{{ state.deviceUser.info.registerTime }}</strong></div>
            <div><span>最近登录</span><strong>{{ state.deviceUser.info.lastLoginAt }}</strong></div>
            <div><span>设备编号</span><strong>{{ state.deviceUser.info.deviceSn }}</strong></div>
            <div><span>默认房间</span><strong>{{ state.deviceUser.info.defaultRoom }}</strong></div>
            <div><span>绑定时间</span><strong>{{ state.deviceUser.info.bindTime }}</strong></div>
          </div>
        </template>
        <p v-else class="muted">该设备暂无绑定用户信息。</p>
      </div>
    </div>
  </main>
</template>

<style scoped>
:global(:root) {
  --bg-gradient: linear-gradient(135deg, #f4f7f6 0%, #d4e1da 100%);
  --bg-glass: rgba(255, 255, 255, 0.65);
  --bg-glass-2: rgba(255, 255, 255, 0.42);
  --text-primary: #2c3e35;
  --text-secondary: #7b8f84;
  --text-muted: #a4c3b2;
  --accent-green: #84a98c;
  --accent-green-deep: #5f7d68;
  --accent-green-light: rgba(132, 169, 140, 0.2);
  --accent-orange: #f4a261;
  --border-light: rgba(255, 255, 255, 0.6);
  --shadow-soft: 0 12px 32px rgba(132, 169, 140, 0.14);
  --shadow-inner: inset 0 0 0 1px rgba(255, 255, 255, 0.7);
  --radius-lg: 28px;
  --radius-md: 18px;
  --radius-sm: 12px;
}

:global(*) {
  box-sizing: border-box;
}

:global(body) {
  margin: 0;
  min-width: 320px;
  min-height: 100vh;
  color: var(--text-primary);
  background: var(--bg-gradient);
  background-attachment: fixed;
  font-family: "Noto Sans SC", "PingFang SC", "Microsoft YaHei", sans-serif;
}

button,
input {
  font: inherit;
}

button {
  cursor: pointer;
}

.boot-screen,
.login-shell,
.app-shell {
  min-height: 100vh;
}

.boot-screen {
  display: grid;
  place-items: center;
}

.boot-card,
.login-panel,
.panel,
.metric-card,
.user-card {
  border: 1px solid var(--border-light);
  border-radius: var(--radius-lg);
  background: var(--bg-glass);
  backdrop-filter: blur(20px);
  -webkit-backdrop-filter: blur(20px);
  box-shadow: var(--shadow-soft), var(--shadow-inner);
}

.login-shell {
  display: grid;
  grid-template-columns: minmax(320px, 0.9fr) minmax(360px, 1.1fr);
}

.login-brand {
  display: flex;
  flex-direction: column;
  justify-content: center;
  gap: 18px;
  padding: clamp(40px, 8vw, 96px);
  color: white;
  background:
    linear-gradient(135deg, rgba(95, 125, 104, 0.92), rgba(132, 169, 140, 0.82)),
    url("https://images.unsplash.com/photo-1516321318423-f06f85e504b3?auto=format&fit=crop&w=1400&q=80") center/cover;
}

.brand-mark,
.logo,
.avatar {
  display: grid;
  place-items: center;
  width: 54px;
  height: 54px;
  border-radius: 18px;
  background: rgba(255, 255, 255, 0.22);
  color: white;
  font-size: 24px;
  font-weight: 500;
}

.login-brand h1 {
  margin: 0;
  font-size: clamp(42px, 7vw, 78px);
  font-weight: 300;
  line-height: 1;
  letter-spacing: 2px;
}

.login-brand p {
  max-width: 520px;
  margin: 0;
  line-height: 1.9;
  font-weight: 300;
}

.login-panel {
  align-self: center;
  width: min(440px, calc(100% - 48px));
  margin: 0 auto;
  padding: 40px;
}

.login-panel h2 {
  margin: 6px 0 28px;
  font-size: 30px;
  font-weight: 500;
}

.field {
  display: grid;
  gap: 8px;
  margin-bottom: 16px;
}

.field > input,
.field > select {
  width: 100%;
  border: 1px solid var(--border-light);
  border-radius: 12px;
  padding: 11px 14px;
  background: rgba(255, 255, 255, 0.7);
  color: var(--text-primary);
  outline: none;
  transition: box-shadow 0.3s ease, border-color 0.3s ease;
}

.field > input:focus,
.field > select:focus {
  border-color: var(--accent-green);
  box-shadow: 0 0 0 3px var(--accent-green-light);
}

.field > input:disabled {
  background: rgba(0, 0, 0, 0.04);
  color: var(--text-muted);
  cursor: not-allowed;
}

.row-actions {
  display: flex;
  gap: 8px;
  justify-content: flex-end;
}

.ghost-button.danger {
  color: #c0563f;
  border-color: rgba(192, 86, 63, 0.35);
}

.ghost-button.danger:hover {
  background: rgba(192, 86, 63, 0.08);
}

.field span,
.search span,
.muted,
.api-note,
.user-card small,
.panel-head p,
.table-row span,
.detail-card small,
.detail-card span,
.pill-row span {
  color: var(--text-secondary);
}

.field-input {
  display: flex;
  align-items: center;
  gap: 10px;
  border: 1px solid var(--border-light);
  border-radius: 99px;
  padding: 12px 18px;
  background: rgba(255, 255, 255, 0.7);
  transition: box-shadow 0.3s ease;
}

.field-input:focus-within {
  box-shadow: 0 0 0 3px var(--accent-green-light);
}

.field-input i {
  color: var(--text-muted);
}

.field-input input,
.search input {
  flex: 1;
  width: 100%;
  border: 0;
  background: transparent;
  color: var(--text-primary);
  outline: none;
}

.robot-check-wrap {
  margin: 2px 0 18px;
}

.robot-check-card {
  display: grid;
  grid-template-columns: 42px minmax(0, 1fr) 84px;
  align-items: center;
  gap: 14px;
  width: 100%;
  min-height: 78px;
  border: 1px solid rgba(95, 125, 104, 0.24);
  border-radius: 8px;
  padding: 12px 14px;
  background: rgba(255, 255, 255, 0.84);
  color: var(--text-primary);
  cursor: pointer;
  text-align: left;
  box-shadow: 0 8px 24px rgba(95, 125, 104, 0.08), inset 0 0 0 1px rgba(255, 255, 255, 0.52);
  transition: border-color 0.2s ease, box-shadow 0.2s ease, transform 0.2s ease;
}

.robot-check-card:hover:not(:disabled) {
  border-color: rgba(132, 169, 140, 0.58);
  box-shadow: 0 12px 28px rgba(95, 125, 104, 0.13), inset 0 0 0 1px rgba(255, 255, 255, 0.65);
  transform: translateY(-1px);
}

.robot-check-card:disabled {
  cursor: not-allowed;
  opacity: 0.82;
}

.robot-check-card.verified {
  border-color: rgba(90, 145, 102, 0.62);
  background: rgba(248, 255, 250, 0.92);
}

.robot-checkbox {
  display: grid;
  place-items: center;
  width: 34px;
  height: 34px;
  border: 3px solid rgba(48, 66, 56, 0.24);
  border-radius: 4px;
  background: #fff;
  color: #fff;
  font-size: 18px;
}

.robot-check-card.verified .robot-checkbox {
  border-color: var(--accent-green);
  background: var(--accent-green);
}

.robot-label {
  color: var(--text-primary);
  font-size: 17px;
  font-weight: 500;
}

.robot-badge {
  display: grid;
  justify-items: center;
  gap: 2px;
  color: var(--text-muted);
  font-size: 10px;
  line-height: 1.1;
}

.robot-badge i {
  margin-bottom: 2px;
  color: #5a8fce;
  font-size: 28px;
}

.robot-badge strong {
  color: var(--text-secondary);
  font-size: 11px;
  font-weight: 600;
}

.check-row,
.topbar,
.top-actions,
.brand,
.user-card,
.panel-head,
.account-card {
  display: flex;
  align-items: center;
}

.check-row {
  gap: 10px;
  margin-bottom: 18px;
}

.primary-button,
.ghost-button,
.user-card button {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  border: 0;
  border-radius: 99px;
  padding: 12px 20px;
  transition: all 0.3s ease;
}

.primary-button {
  width: 100%;
  background: var(--accent-green);
  color: white;
  font-weight: 500;
  box-shadow: 0 8px 20px rgba(132, 169, 140, 0.35);
}

.primary-button:hover:not(:disabled) {
  background: var(--accent-green-deep);
  transform: translateY(-2px);
}

.primary-button:disabled {
  cursor: not-allowed;
  opacity: 0.55;
}

.primary-button.compact,
.ghost-button.compact {
  width: auto;
}

.ghost-button {
  background: var(--bg-glass);
  border: 1px solid var(--border-light);
  color: var(--accent-green-deep);
  font-weight: 500;
}

.ghost-button:hover:not(:disabled) {
  background: rgba(255, 255, 255, 0.9);
}

.ghost-button.wide {
  width: 100%;
  margin-top: 10px;
}

.api-note {
  display: flex;
  align-items: center;
  gap: 6px;
  margin: 18px 0 0;
  font-size: 13px;
}

.app-shell {
  display: grid;
  grid-template-columns: 280px minmax(0, 1fr);
}

.sidebar {
  position: sticky;
  top: 0;
  height: 100vh;
  overflow: auto;
  padding: 36px 22px;
  display: flex;
  flex-direction: column;
  background: var(--bg-glass);
  backdrop-filter: blur(20px);
  -webkit-backdrop-filter: blur(20px);
  border-right: 1px solid var(--border-light);
  box-shadow: 10px 0 30px rgba(132, 169, 140, 0.05);
  color: var(--text-primary);
}

.brand {
  gap: 14px;
  margin-bottom: 34px;
  padding-left: 6px;
}

.brand .logo {
  background: var(--accent-green-light);
  color: var(--accent-green);
}

.brand strong {
  font-size: 19px;
  font-weight: 500;
  letter-spacing: 1px;
}

.brand small,
.nav-groups p,
.user-card small {
  display: block;
}

.brand small {
  color: var(--text-secondary);
  font-size: 12px;
}

.nav-groups {
  display: grid;
  gap: 18px;
  flex: 1;
}

.nav-groups p {
  margin: 0 0 8px;
  padding-left: 12px;
  color: var(--text-muted);
  font-size: 12px;
  font-weight: 500;
  letter-spacing: 0.5px;
}

.nav-item {
  display: flex;
  align-items: center;
  gap: 14px;
  width: 100%;
  margin-bottom: 6px;
  border: 0;
  border-radius: var(--radius-md);
  padding: 13px 16px;
  background: transparent;
  color: var(--text-secondary);
  text-align: left;
  font-size: 15px;
  transition: all 0.3s ease;
}

.nav-item i {
  width: 22px;
  font-size: 16px;
  text-align: center;
}

.nav-item:hover {
  background: rgba(255, 255, 255, 0.55);
  color: var(--text-primary);
}

.nav-item.active {
  background: var(--accent-green-light);
  color: var(--accent-green-deep);
  font-weight: 500;
  box-shadow: var(--shadow-inner);
}

.user-card {
  gap: 12px;
  margin-top: 24px;
  padding: 14px;
  background: rgba(255, 255, 255, 0.5);
  border-color: var(--border-light);
}

.user-card .avatar {
  width: 40px;
  height: 40px;
  font-size: 16px;
  background: var(--accent-green);
}

.user-card button {
  margin-left: auto;
  padding: 10px 12px;
  background: rgba(255, 255, 255, 0.6);
  color: var(--accent-green-deep);
}

.content {
  min-width: 0;
  padding: 40px;
  display: flex;
  flex-direction: column;
  gap: 28px;
  height: 100vh;
  overflow-y: auto;
}

.topbar {
  justify-content: space-between;
  gap: 18px;
  margin-bottom: 0;
}

.topbar h1 {
  display: flex;
  align-items: center;
  gap: 14px;
  margin: 6px 0;
  font-size: clamp(26px, 4vw, 34px);
  font-weight: 500;
}

.topbar h1 i {
  color: var(--accent-green);
  font-size: 0.8em;
}

.eyebrow {
  margin: 0;
  color: var(--accent-green);
  text-transform: uppercase;
  letter-spacing: 1px;
  font-size: 12px;
  font-weight: 500;
}

.login-brand .eyebrow {
  color: rgba(255, 255, 255, 0.85);
}

.muted {
  display: flex;
  align-items: center;
  gap: 6px;
  margin: 0;
  line-height: 1.7;
  font-size: 13px;
}

.top-actions {
  gap: 12px;
}

.search {
  display: flex;
  align-items: center;
  gap: 10px;
  min-width: 280px;
  padding: 11px 20px;
  border: 1px solid var(--border-light);
  border-radius: 99px;
  background: var(--bg-glass);
  box-shadow: var(--shadow-soft);
}

.search i {
  color: var(--text-secondary);
}

.metrics-grid,
.dashboard-grid,
.two-column,
.profile-grid,
.mini-cards,
.form-grid {
  display: grid;
  gap: 24px;
}

.metrics-grid {
  grid-template-columns: repeat(4, minmax(0, 1fr));
  margin-bottom: 0;
}

.metric-card {
  position: relative;
  overflow: hidden;
  min-height: 138px;
  padding: 28px 24px;
}

.metric-card::before {
  content: "";
  position: absolute;
  top: -24px;
  right: -24px;
  width: 100px;
  height: 100px;
  background: radial-gradient(circle, rgba(255, 255, 255, 0.85) 0%, rgba(255, 255, 255, 0) 70%);
  border-radius: 50%;
}

.metric-card p,
.metric-card strong,
.metric-card span {
  margin: 0;
  position: relative;
}

.metric-title {
  display: flex;
  align-items: center;
  justify-content: space-between;
  color: var(--text-secondary);
  font-size: 15px;
}

.metric-card strong {
  display: block;
  margin: 16px 0 10px;
  font-size: clamp(28px, 4vw, 40px);
  font-weight: 300;
  line-height: 1;
}

.metric-trend {
  display: inline-block;
  font-size: 13px;
}

.metric-card.green strong,
.metric-card.green .metric-title i,
.badge.normal {
  color: var(--accent-green);
}

.metric-card.blue strong,
.metric-card.blue .metric-title i,
.badge.info {
  color: #5b8fb0;
}

.metric-card.orange strong,
.metric-card.orange .metric-title i,
.badge.warning {
  color: var(--accent-orange);
}

.metric-card.red strong,
.metric-card.red .metric-title i {
  color: #d98a73;
}

.dashboard-grid {
  grid-template-columns: minmax(0, 1.5fr) minmax(320px, 0.9fr);
}

.two-column {
  grid-template-columns: repeat(2, minmax(0, 1fr));
}

.profile-grid {
  grid-template-columns: repeat(4, minmax(0, 1fr));
}

.form-grid {
  grid-template-columns: repeat(3, minmax(0, 1fr));
}

.panel {
  min-width: 0;
  padding: 32px;
}

.panel.full {
  grid-column: 1 / -1;
}

.panel-head {
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 24px;
}

.panel-head h3,
.panel-head p {
  margin: 0;
}

.panel-head h3 {
  font-size: 18px;
  font-weight: 500;
}

.panel-head p {
  margin-top: 4px;
  font-size: 13px;
}

.bar-chart {
  display: flex;
  align-items: end;
  justify-content: space-around;
  gap: 10px;
  min-height: 220px;
  padding-bottom: 16px;
  border-bottom: 1px dashed rgba(255, 255, 255, 0.85);
}

.bar-chart.large {
  min-height: 320px;
}

.bar-item {
  display: grid;
  flex: 1;
  justify-items: center;
  gap: 8px;
  min-width: 34px;
}

.bar {
  width: min(34px, 82%);
  border-radius: 16px;
  background: linear-gradient(180deg, var(--accent-green) 0%, rgba(132, 169, 140, 0.35) 100%);
  transition: all 0.3s ease;
}

.bar:hover {
  transform: translateY(-5px);
  background: linear-gradient(180deg, #a4c3b2 0%, var(--accent-green) 100%);
  box-shadow: 0 10px 20px rgba(132, 169, 140, 0.25);
}

.bar-item span,
.bar-item small {
  color: var(--text-secondary);
  font-size: 12px;
}

/* 带坐标轴的趋势图 */
.chart-with-axis {
  display: block;
}

.axis-unit {
  margin: 0 0 10px;
  font-size: 12px;
  font-weight: 500;
  color: var(--accent-green-deep);
}

.chart-row {
  display: flex;
  gap: 12px;
}

.y-ticks {
  flex-shrink: 0;
  width: 48px;
  height: 300px;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  align-items: flex-end;
  text-align: right;
}

.y-tick {
  font-size: 12px;
  color: var(--text-secondary);
  line-height: 1;
  transform: translateY(-50%);
}

.y-tick:first-child {
  transform: translateY(-50%);
}

.y-tick:last-child {
  transform: translateY(50%);
}

.plot {
  flex: 1;
  min-width: 0;
}

.plot-area {
  position: relative;
  height: 300px;
  display: flex;
  align-items: flex-end;
  justify-content: space-around;
  gap: 10px;
  border-left: 1px solid rgba(132, 169, 140, 0.35);
  border-bottom: 1px solid rgba(132, 169, 140, 0.35);
  padding: 0 4px;
}

.gridline {
  position: absolute;
  left: 0;
  right: 0;
  height: 0;
  border-top: 1px dashed rgba(132, 169, 140, 0.22);
  pointer-events: none;
}

.bar-col {
  position: relative;
  z-index: 1;
  flex: 1;
  display: flex;
  align-items: flex-end;
  justify-content: center;
  min-width: 24px;
  height: 100%;
}

.bar-col .bar {
  width: min(34px, 82%);
  min-height: 4px;
  border-radius: 16px 16px 0 0;
  background: linear-gradient(180deg, var(--accent-green) 0%, rgba(132, 169, 140, 0.35) 100%);
  transition: all 0.3s ease;
}

.bar-col .bar:hover {
  transform: scaleY(1.02);
  transform-origin: bottom;
  background: linear-gradient(180deg, #a4c3b2 0%, var(--accent-green) 100%);
  box-shadow: 0 10px 20px rgba(132, 169, 140, 0.25);
}

.x-labels {
  display: flex;
  justify-content: space-around;
  gap: 10px;
  margin-top: 10px;
  padding: 0 4px;
}

.x-label {
  flex: 1;
  display: grid;
  justify-items: center;
  gap: 4px;
  min-width: 24px;
}

.x-label span,
.x-label small {
  color: var(--text-secondary);
  font-size: 12px;
}

.x-label small {
  font-weight: 500;
  color: var(--text-primary);
}

.rank-list,
.pill-list {
  display: grid;
  gap: 10px;
  margin: 0;
  padding: 0;
  list-style: none;
}

.rank-list li,
.pill-row,
.table-row,
.mini-cards div,
.live-grid div {
  border: 1px solid rgba(255, 255, 255, 0.55);
  border-radius: var(--radius-md);
  background: rgba(255, 255, 255, 0.42);
  transition: all 0.2s ease;
}

.rank-list li:hover,
.table-row:hover,
.mini-cards div:hover,
.live-grid div:hover {
  background: rgba(255, 255, 255, 0.78);
  transform: translateX(2px);
}

.rank-list li {
  display: grid;
  grid-template-columns: 34px 1fr auto;
  align-items: center;
  gap: 12px;
  padding: 14px;
}

.rank-list span {
  display: grid;
  place-items: center;
  width: 28px;
  height: 28px;
  border-radius: 50%;
  background: #eaefea;
  color: var(--text-secondary);
  font-size: 12px;
  font-weight: 500;
}

.rank-list li:nth-child(1) span {
  background: var(--accent-orange);
  color: white;
}

.rank-list li:nth-child(2) span {
  background: var(--accent-green);
  color: white;
}

.rank-list li:nth-child(3) span {
  background: var(--text-muted);
  color: white;
}

.rank-list strong,
.table-row strong {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-weight: 500;
}

.rank-list em,
.table-row em,
.mini-cards em {
  color: var(--accent-orange);
  font-style: normal;
}

.live-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 14px;
}

.live-grid div,
.mini-cards div {
  padding: 18px;
}

.live-grid span,
.live-grid small,
.mini-cards span {
  display: block;
  color: var(--text-secondary);
}

.live-grid strong,
.mini-cards strong {
  display: block;
  margin: 10px 0;
  font-size: 26px;
  font-weight: 300;
  color: var(--accent-green-deep);
}

.device-overview {
  display: grid;
  gap: 10px;
}

.device-overview-row {
  display: grid;
  grid-template-columns: 1fr auto;
  align-items: center;
  gap: 12px;
  padding: 12px 14px;
  border: 1px solid rgba(255, 255, 255, 0.55);
  border-radius: var(--radius-md);
  background: rgba(255, 255, 255, 0.42);
  transition: all 0.2s ease;
}

.device-overview-row:hover {
  background: rgba(255, 255, 255, 0.78);
  transform: translateX(2px);
}

.device-name-btn {
  display: flex;
  align-items: center;
  gap: 12px;
  border: none;
  background: none;
  padding: 0;
  cursor: pointer;
  text-align: left;
  min-width: 0;
}

.device-name-text {
  display: grid;
  min-width: 0;
}

.device-name-text strong {
  font-weight: 500;
  color: var(--accent-green-deep);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.device-name-btn:hover .device-name-text strong {
  text-decoration: underline;
}

.device-name-text small {
  color: var(--text-secondary);
  font-size: 12px;
}

.device-status {
  font-size: 13px;
  color: var(--text-muted);
  padding: 3px 10px;
  border-radius: 999px;
  background: rgba(0, 0, 0, 0.05);
}

.device-status.online {
  color: var(--accent-green-deep);
  background: rgba(76, 145, 95, 0.14);
}

.user-detail-card {
  max-width: 560px;
}

.user-detail-head {
  display: flex;
  align-items: center;
  gap: 14px;
  margin: 4px 0 18px;
}

.user-avatar {
  display: grid;
  place-items: center;
  width: 46px;
  height: 46px;
  border-radius: 50%;
  background: var(--accent-green);
  color: #fff;
  font-size: 20px;
  font-weight: 500;
}

.user-detail-head strong {
  display: block;
  font-size: 17px;
  font-weight: 500;
}

.user-detail-head small {
  color: var(--text-secondary);
}

.user-status-tag {
  margin-left: auto;
  font-size: 12px;
  padding: 4px 12px;
  border-radius: 999px;
  background: rgba(76, 145, 95, 0.14);
  color: var(--accent-green-deep);
}

.user-status-tag.warn {
  background: rgba(214, 122, 60, 0.16);
  color: var(--accent-orange);
}

.user-detail-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
}

.user-detail-grid div {
  padding: 12px 14px;
  border-radius: var(--radius-md);
  background: rgba(255, 255, 255, 0.42);
  border: 1px solid rgba(255, 255, 255, 0.55);
}

.user-detail-grid span {
  display: block;
  font-size: 12px;
  color: var(--text-secondary);
  margin-bottom: 4px;
}

.user-detail-grid strong {
  font-weight: 500;
  word-break: break-all;
}

.mini-cards {
  grid-template-columns: repeat(4, minmax(0, 1fr));
}

.heat-list {
  display: grid;
  gap: 14px;
}

.heat-row {
  display: grid;
  grid-template-columns: 92px 1fr 86px;
  align-items: center;
  gap: 12px;
}

.heat-row span,
.heat-row strong {
  font-size: 14px;
}

.heat-row strong {
  font-weight: 500;
}

.heat-row div {
  height: 12px;
  overflow: hidden;
  border-radius: 99px;
  background: var(--accent-green-light);
}

.heat-row i {
  display: block;
  height: 100%;
  border-radius: inherit;
  background: linear-gradient(90deg, var(--accent-green), var(--accent-orange));
}

.pill-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 14px;
  padding: 14px 16px;
}

.pill-row strong {
  font-weight: 500;
}

.empty-state {
  display: grid;
  min-height: 180px;
  place-items: center;
  margin: 0;
  border: 1px dashed rgba(132, 169, 140, 0.35);
  border-radius: var(--radius-md);
  color: var(--text-secondary);
  background: rgba(255, 255, 255, 0.28);
}

.badge {
  border-radius: 99px;
  padding: 4px 12px;
  background: var(--accent-green-light);
  font-size: 13px;
  font-weight: 500;
}

.hero-number {
  min-height: 230px;
}

.hero-number span {
  color: var(--text-secondary);
}

.hero-number strong {
  display: block;
  margin: 28px 0 18px;
  color: var(--accent-green);
  font-size: clamp(52px, 9vw, 92px);
  font-weight: 300;
}

/* 用户价值环状图 */
.value-layout {
  display: grid;
  gap: 24px;
}

.donut-body {
  display: flex;
  align-items: center;
  gap: 40px;
  flex-wrap: wrap;
}

.donut-chart {
  position: relative;
  width: 200px;
  height: 200px;
  flex-shrink: 0;
}

.donut-chart svg {
  width: 100%;
  height: 100%;
  transform: rotate(-90deg);
}

.pie-chart {
  position: relative;
  width: 200px;
  height: 200px;
  flex-shrink: 0;
  filter: drop-shadow(0 8px 18px rgba(132, 169, 140, 0.2));
}

.pie-chart svg {
  width: 100%;
  height: 100%;
}

.pie-chart path {
  transition: opacity 0.2s ease;
}

.pie-chart:hover path {
  opacity: 0.85;
}

.pie-chart path:hover {
  opacity: 1;
}

/* 用户画像四宫格小饼图 */
.profile-pie {
  width: 140px;
  height: 140px;
  margin: 0 auto 20px;
  filter: drop-shadow(0 6px 14px rgba(132, 169, 140, 0.2));
}

.profile-pie svg {
  width: 100%;
  height: 100%;
}

.profile-pie path {
  transition: opacity 0.2s ease;
}

.profile-pie:hover path {
  opacity: 0.85;
}

.profile-pie path:hover {
  opacity: 1;
}

.profile-grid .pill-row {
  display: grid;
  grid-template-columns: 14px 1fr auto auto;
  align-items: center;
  gap: 10px;
}

.profile-grid .pill-row b {
  min-width: 42px;
  text-align: right;
  font-weight: 500;
  color: var(--accent-green-deep);
}

.donut-track {
  fill: none;
  stroke: var(--accent-green-light);
  stroke-width: 14;
}

.donut-arc {
  fill: none;
  stroke-width: 14;
  stroke-linecap: round;
  transition: stroke-dasharray 0.6s ease, stroke-dashoffset 0.6s ease;
}

.donut-center {
  position: absolute;
  inset: 0;
  display: grid;
  place-content: center;
  text-align: center;
}

.donut-center small {
  color: var(--text-secondary);
  font-size: 13px;
}

.donut-center strong {
  display: block;
  margin-top: 6px;
  font-size: 34px;
  font-weight: 300;
  color: var(--accent-green-deep);
}

.donut-legend {
  flex: 1;
  min-width: 240px;
  display: grid;
  gap: 12px;
  margin: 0;
  padding: 0;
  list-style: none;
}

.donut-legend li {
  display: grid;
  grid-template-columns: 16px 1fr auto auto;
  align-items: center;
  gap: 12px;
  padding: 14px 16px;
  border: 1px solid rgba(255, 255, 255, 0.55);
  border-radius: var(--radius-md);
  background: rgba(255, 255, 255, 0.42);
}

.legend-dot {
  width: 14px;
  height: 14px;
  border-radius: 50%;
}

.legend-label {
  font-weight: 500;
}

.donut-legend em {
  color: var(--text-secondary);
  font-style: normal;
  font-size: 14px;
}

.donut-legend b {
  min-width: 52px;
  text-align: right;
  font-weight: 500;
  color: var(--accent-green-deep);
}

.data-table {
  display: grid;
  gap: 10px;
}

.scroll-list {
  align-content: start;
  max-height: min(58vh, 520px);
  overflow-y: auto;
  padding-right: 6px;
  scrollbar-gutter: stable;
}

.feedback-scroll,
.log-scroll,
.notice-scroll,
.audit-scroll {
  max-height: min(62vh, 560px);
}

.device-scroll {
  max-height: min(46vh, 420px);
  margin-top: 14px;
}

.scroll-list::-webkit-scrollbar {
  width: 8px;
}

.scroll-list::-webkit-scrollbar-thumb {
  border-radius: 99px;
  background: rgba(132, 169, 140, 0.45);
}

.scroll-list::-webkit-scrollbar-track {
  border-radius: 99px;
  background: rgba(255, 255, 255, 0.45);
}

.table-row {
  display: grid;
  grid-template-columns: minmax(100px, 0.28fr) minmax(0, 1fr) auto;
  align-items: center;
  gap: 14px;
  padding: 15px 18px;
}

.table-row:not(.device-row) {
  cursor: pointer;
}

.user-row {
  grid-template-columns: minmax(0, 1fr) auto;
}

.user-cell {
  display: grid;
  gap: 4px;
  min-width: 0;
}

.user-cell small {
  color: var(--text-secondary);
  font-size: 12px;
}

.user-row > em {
  justify-self: end;
}

.audit-panel .panel-head {
  align-items: flex-start;
}

.audit-panel .panel-head > div {
  min-width: 0;
}

.audit-panel .panel-head p {
  white-space: normal;
  overflow-wrap: anywhere;
}

.audit-row {
  grid-template-columns: minmax(0, 1fr) max-content;
  align-items: start;
  cursor: default;
}

.audit-main {
  display: grid;
  gap: 6px;
  min-width: 0;
}

.audit-main strong,
.audit-main span {
  overflow-wrap: anywhere;
  word-break: break-word;
}

.audit-row em {
  align-self: start;
  white-space: nowrap;
}

.segmented {
  display: flex;
  gap: 6px;
  padding: 5px;
  border-radius: 99px;
  background: var(--accent-green-light);
}

.segmented button {
  border: 0;
  border-radius: 99px;
  padding: 8px 16px;
  background: transparent;
  color: var(--accent-green-deep);
  transition: all 0.3s ease;
}

.segmented button.active {
  background: var(--accent-green);
  color: white;
}

.detail-layout {
  grid-template-columns: minmax(0, 1.35fr) minmax(280px, 0.65fr);
}

.detail-card {
  align-self: start;
  display: grid;
  gap: 12px;
}

.detail-card h3,
.detail-card p {
  margin: 0;
}

.device-select {
  width: 100%;
}

.device-option {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  min-width: 0;
}

.device-option span {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.device-option em {
  flex: 0 0 auto;
  color: var(--text-muted);
  font-style: normal;
  font-size: 12px;
}

.device-pick-row {
  grid-template-columns: minmax(130px, 0.42fr) minmax(0, 1fr) auto;
}

.device-pick-row.active {
  border-color: rgba(74, 124, 89, 0.55);
  background: rgba(229, 244, 235, 0.9);
  box-shadow: inset 3px 0 0 var(--accent-green);
}

.device-pick-row strong {
  display: inline-flex;
  align-items: center;
  gap: 8px;
}

.device-actions {
  display: flex;
  gap: 10px;
  margin-top: 14px;
}

.device-actions button {
  border: 1px solid var(--border-soft);
  border-radius: 8px;
  background: white;
  padding: 8px 14px;
  color: var(--accent-green-deep);
}

.device-row {
  grid-template-columns: minmax(0, 1fr) auto;
}

.device-row > button {
  display: grid;
  grid-template-columns: 18px minmax(120px, 1fr) auto;
  align-items: center;
  gap: 12px;
  min-width: 0;
  border: 0;
  background: transparent;
  text-align: left;
}

.dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  background: var(--text-muted);
}

.dot.online {
  background: var(--accent-green);
  box-shadow: 0 0 0 5px var(--accent-green-light);
}

.row-actions {
  display: flex;
  gap: 8px;
}

.row-actions button {
  border: 0;
  border-radius: 99px;
  padding: 8px 14px;
  background: var(--accent-green-light);
  color: var(--accent-green-deep);
  transition: all 0.2s ease;
}

.row-actions button:hover {
  background: var(--accent-green);
  color: white;
}

.account-layout {
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(320px, 0.72fr);
  gap: 24px;
}

.account-card {
  justify-content: flex-start;
  gap: 24px;
}

.password-card {
  display: grid;
  align-content: start;
  gap: 18px;
}

.password-form {
  display: grid;
  gap: 16px;
}

.password-form label {
  display: grid;
  gap: 8px;
  color: var(--text-secondary);
  font-size: 14px;
}

.password-form input {
  width: 100%;
  height: 46px;
  border: 1px solid rgba(132, 169, 140, 0.22);
  border-radius: var(--radius-sm);
  background: rgba(255, 255, 255, 0.72);
  padding: 0 14px;
  color: var(--text-primary);
  outline: none;
}

.password-form input:focus {
  border-color: var(--accent-green);
  box-shadow: 0 0 0 3px rgba(132, 169, 140, 0.14);
}

.form-actions {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  flex-wrap: wrap;
}

.avatar.big {
  width: 80px;
  height: 80px;
  font-size: 30px;
  border-radius: 26px;
  background: var(--accent-green);
}

.account-card h3,
.account-card p {
  margin: 4px 0;
}

.boot-card {
  padding: 28px 40px;
  font-weight: 500;
  color: var(--accent-green-deep);
}

.spinning {
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}

.fa-rotate.spin {
  animation: spin 0.8s linear infinite;
}

/* 角色权限行 */
.role-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 18px;
  padding: 18px 20px;
  border: 1px solid rgba(255, 255, 255, 0.55);
  border-radius: var(--radius-md);
  background: rgba(255, 255, 255, 0.42);
  transition: all 0.2s ease;
}

.role-row:hover {
  background: rgba(255, 255, 255, 0.78);
}

.role-info {
  min-width: 0;
}

.role-info strong {
  font-size: 16px;
  font-weight: 500;
}

.role-info > span {
  display: block;
  margin: 4px 0 10px;
  color: var(--text-secondary);
  font-size: 13px;
}

.perm-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.perm-tag {
  padding: 3px 10px;
  border-radius: 99px;
  background: var(--accent-green-light);
  color: var(--accent-green-deep);
  font-size: 12px;
}

.role-actions {
  display: flex;
  align-items: center;
  gap: 16px;
  flex-shrink: 0;
}

.role-actions em {
  color: var(--accent-orange);
  font-style: normal;
  font-weight: 500;
}

/* 权限编辑弹窗 */
.modal-mask {
  position: fixed;
  inset: 0;
  z-index: 50;
  display: grid;
  place-items: center;
  padding: 24px;
  background: rgba(44, 62, 53, 0.28);
  backdrop-filter: blur(6px);
  -webkit-backdrop-filter: blur(6px);
}

.modal-card {
  width: min(640px, 100%);
  max-height: 88vh;
  overflow: auto;
  padding: 28px;
  border: 1px solid var(--border-light);
  border-radius: var(--radius-lg);
  background: rgba(255, 255, 255, 0.92);
  backdrop-filter: blur(24px);
  -webkit-backdrop-filter: blur(24px);
  box-shadow: 0 24px 60px rgba(44, 64, 56, 0.22);
}

.icon-close {
  display: grid;
  place-items: center;
  width: 36px;
  height: 36px;
  border: 0;
  border-radius: 50%;
  background: rgba(132, 169, 140, 0.14);
  color: var(--text-secondary);
  transition: all 0.2s ease;
}

.icon-close:hover {
  background: var(--accent-green-light);
  color: var(--accent-green-deep);
}

.perm-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 10px;
  margin: 8px 0 24px;
}

.perm-option {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 12px 14px;
  border: 1px solid rgba(132, 169, 140, 0.25);
  border-radius: var(--radius-sm);
  background: rgba(255, 255, 255, 0.5);
  cursor: pointer;
  transition: all 0.2s ease;
  font-size: 14px;
}

.perm-option:hover {
  border-color: var(--accent-green);
}

.perm-option.checked {
  background: var(--accent-green-light);
  border-color: var(--accent-green);
  color: var(--accent-green-deep);
  font-weight: 500;
}

.perm-option input {
  display: none;
}

.check-box {
  display: grid;
  place-items: center;
  width: 20px;
  height: 20px;
  flex-shrink: 0;
  border: 1px solid var(--accent-green);
  border-radius: 6px;
  background: white;
  color: white;
  font-size: 11px;
}

.perm-option.checked .check-box {
  background: var(--accent-green);
}

.check-box i {
  opacity: 0;
  transition: opacity 0.2s ease;
}

.perm-option.checked .check-box i {
  opacity: 1;
}

.modal-foot {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
}

.modal-buttons {
  display: flex;
  gap: 10px;
}

@media (max-width: 1180px) {
  .metrics-grid,
  .profile-grid,
  .mini-cards,
  .form-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .dashboard-grid,
  .two-column,
  .detail-layout {
    grid-template-columns: 1fr;
  }

}

@media (max-width: 820px) {
  .login-shell,
  .app-shell {
    grid-template-columns: 1fr;
  }

  .login-brand {
    min-height: 280px;
    padding: 34px;
  }

  .login-panel {
    margin: 28px auto;
  }

  .sidebar {
    position: relative;
    height: auto;
  }

  .topbar,
  .top-actions,
  .account-card {
    align-items: stretch;
    flex-direction: column;
  }

  .account-layout {
    grid-template-columns: 1fr;
  }

  .search {
    min-width: 0;
    width: 100%;
  }

  .metrics-grid,
  .profile-grid,
  .mini-cards,
  .live-grid,
  .form-grid {
    grid-template-columns: 1fr;
  }

  .table-row,
  .device-row,
  .device-row > button,
  .device-pick-row {
    grid-template-columns: 1fr;
  }

  .scroll-list {
    max-height: 54vh;
  }

  .audit-row em {
    justify-self: start;
  }

  .row-actions {
    justify-content: flex-start;
  }
}
</style>

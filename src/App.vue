<script setup>
import { computed, nextTick, onMounted, reactive } from "vue"
import { ElMessage, ElMessageBox } from "element-plus"
import { ApiError, API_BASE, login as loginApi, logout as logoutApi, request } from "./api"

const roleNames = {
  super_admin: "超级管理员",
  market_admin: "市场分析管理员",
  operator_admin: "普通管理员",
}

const menus = [
  { key: "overview", label: "数据总览", section: "核心看板", roles: ["super_admin", "market_admin", "operator_admin"] },
  { key: "decision", label: "决策驾驶舱", section: "核心看板", roles: ["super_admin", "market_admin"] },
  { key: "trend", label: "趋势分析", section: "核心看板", roles: ["super_admin", "market_admin", "operator_admin"] },
  { key: "region", label: "区域热力图", section: "分析洞察", roles: ["super_admin", "market_admin"] },
  { key: "profile", label: "用户画像", section: "分析洞察", roles: ["super_admin", "market_admin"] },
  { key: "value", label: "用户价值", section: "分析洞察", roles: ["super_admin", "market_admin"] },
  { key: "segments", label: "用户分群", section: "分析洞察", roles: ["super_admin", "market_admin"] },
  { key: "insights", label: "营销洞察", section: "分析洞察", roles: ["super_admin", "market_admin"] },
  { key: "songs", label: "热歌排行", section: "分析洞察", roles: ["super_admin", "market_admin"] },
  { key: "reports", label: "决策报表", section: "分析洞察", roles: ["super_admin", "market_admin"] },
  { key: "feedback", label: "用户反馈", section: "运营管理", roles: ["super_admin", "operator_admin"] },
  { key: "devices", label: "设备管理", section: "运营管理", roles: ["super_admin", "operator_admin"] },
  { key: "groups", label: "设备分组", section: "运营管理", roles: ["super_admin", "operator_admin"] },
  { key: "alerts", label: "告警中心", section: "运营管理", roles: ["super_admin", "operator_admin"] },
  { key: "firmware", label: "设备固件", section: "运营管理", roles: ["super_admin", "operator_admin"] },
  { key: "tasks", label: "任务中心", section: "运营管理", roles: ["super_admin", "operator_admin"] },
  { key: "logs", label: "设备日志", section: "运营管理", roles: ["super_admin", "operator_admin"] },
  { key: "users", label: "用户管理", section: "系统管理", roles: ["super_admin"] },
  { key: "roles", label: "角色权限", section: "系统管理", roles: ["super_admin"] },
  { key: "system", label: "系统配置", section: "系统管理", roles: ["super_admin"] },
  { key: "monitor", label: "系统监控", section: "系统管理", roles: ["super_admin"] },
  { key: "notices", label: "系统公告", section: "系统管理", roles: ["super_admin"] },
  { key: "audit", label: "审计日志", section: "系统管理", roles: ["super_admin"] },
  { key: "account", label: "个人信息", section: "账户", roles: ["super_admin", "market_admin", "operator_admin"] },
]

const state = reactive({
  loginForm: {
    username: localStorage.getItem("admin_username") || "",
    password: "",
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
  reports: { total: 0, list: [], raw: [] },
  feedback: { total: 0, list: [] },
  devices: { total: 0, list: [] },
  groups: { total: 0, list: [] },
  alerts: { total: 0, list: [] },
  runtime: null,
  firmware: null,
  firmwarePackages: { total: 0, list: [] },
  firmwareTasks: { total: 0, list: [] },
  logs: { total: 0, list: [] },
  users: { total: 0, list: [] },
  roles: { total: 0, list: [] },
  settings: {},
  monitor: { services: [], metrics: {}, exceptions: [] },
  notices: { total: 0, list: [] },
  audit: { total: 0, list: [] },
  detail: null,
})

const LOCAL_HOSTS = new Set(["localhost", "127.0.0.1", "0.0.0.0"])
const isLoggedIn = computed(() => Boolean(state.token && state.admin))
const currentRole = computed(() => state.admin?.role || "")
const currentRoleName = computed(() => state.admin?.roleName || roleNames[currentRole.value] || "未登录")
const visibleMenus = computed(() => menus.filter((item) => item.roles.includes(currentRole.value)))
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
      { label: "设备总数", value: formatNumber(state.devices.total || devices.length), hint: `${online} 台在线`, tone: "green" },
      { label: "在线率", value: percent(devices.length ? online / devices.length : 0), hint: "来自设备列表", tone: "blue" },
      { label: "固件版本", value: state.firmware?.currentVersion || "-", hint: state.firmware?.needUpdate ? "可更新" : "已是最新", tone: "orange" },
      { label: "待处理反馈", value: formatNumber(pending), hint: `共 ${state.feedback.total || 0} 条`, tone: "red" },
    ]
  }

  if (currentRole.value === "market_admin") {
    const totalPlays = state.songs.reduce((sum, item) => sum + Number(item.playCount || 0), 0)
    const avgRetention = average(state.retention.map((item) => item.day7RetentionRate))
    return [
      { label: "热歌播放", value: formatNumber(totalPlays), hint: `${state.songs.length} 首上榜歌曲`, tone: "green" },
      { label: "高活用户", value: formatNumber(state.value.highActiveUserCount || 0), hint: "近周期活跃", tone: "blue" },
      { label: "普通用户", value: formatNumber(state.value.normalUserCount || 0), hint: "用户价值分层", tone: "orange" },
      { label: "7 日留存", value: percent(avgRetention), hint: "购买设备后持续使用", tone: "red" },
    ]
  }

  const deviceTotal = state.overview.device?.deviceCount || 0
  const onlineRate = deviceTotal ? (state.overview.device?.onlineDeviceCount || 0) / deviceTotal : 0
  return [
    { label: "总用户", value: formatNumber(state.overview.user?.userCount || 0), hint: `新增 ${formatNumber(state.overview.user?.newUserCount || 0)}`, tone: "green" },
    { label: "设备数", value: formatNumber(deviceTotal), hint: `在线率 ${percent(onlineRate)}`, tone: "blue" },
    { label: "销售额", value: money(state.overview.sales?.salesAmount || 0), hint: `${formatNumber(state.overview.sales?.orderCount || 0)} 笔订单`, tone: "orange" },
    { label: "活跃度", value: percent(state.overview.activity?.activityRate || 0), hint: `${formatNumber(state.overview.activity?.activeUserCount || 0)} 活跃用户`, tone: "red" },
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

function statusText(status) {
  return {
    enabled: "启用",
    readonly: "只读",
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

async function handleLogin() {
  if (!state.loginForm.username || !state.loginForm.password) {
    ElMessage.warning("请输入用户名和密码")
    return
  }

  state.loading = true
  try {
    const data = await loginApi(state.loginForm.username.trim(), state.loginForm.password)
    applySession(data)
    if (state.loginForm.remember) {
      localStorage.setItem("admin_username", state.loginForm.username.trim())
    } else {
      localStorage.removeItem("admin_username")
    }
    state.loginForm.password = ""
    ElMessage.success("登录成功，正在加载后台数据")
    await loadPage(true)
  } catch (error) {
    ElMessage.error(error.message || "登录失败")
  } finally {
    state.loading = false
  }
}

async function handleWechatLogin() {
  state.loading = true
  try {
    const data = await request("/api/admin/wechat-login", {
      method: "POST",
      token: "",
      body: { code: "demo-wechat-code" },
    })
    applySession(data)
    ElMessage.success("微信快捷登录成功")
    await loadPage(true)
  } catch (error) {
    ElMessage.error(error.message || "微信登录失败")
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
  state.active = firstMenuForRole(data.adminInfo.role)
}

function firstMenuForRole(role) {
  return menus.find((item) => item.roles.includes(role))?.key || "overview"
}

function clearSession() {
  state.token = ""
  state.admin = null
  localStorage.removeItem("admin_token")
  localStorage.removeItem("admin_info")
}

async function handleLogout() {
  await silent(() => logoutApi(), null)
  clearSession()
  state.detail = null
  ElMessage.success("已退出登录")
}

async function restoreSession() {
  if (!state.token) {
    state.booting = false
    return
  }

  try {
    state.admin = await api("/api/admin/profile")
    localStorage.setItem("admin_info", JSON.stringify(state.admin))
    state.active = canUse(state.active) ? state.active : firstMenuForRole(state.admin.role)
    await loadPage(true)
  } catch {
    clearSession()
  } finally {
    state.booting = false
  }
}

async function selectPage(key) {
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
    if (state.active === "reports") await loadReports()
    if (state.active === "feedback") await loadFeedback()
    if (state.active === "devices") await loadDevices()
    if (state.active === "groups") await loadGroups()
    if (state.active === "alerts") await loadAlerts()
    if (state.active === "firmware") await loadFirmware()
    if (state.active === "tasks") await loadTasks()
    if (state.active === "logs") await loadLogs()
    if (state.active === "users") await loadUsers()
    if (state.active === "roles") await loadRoles()
    if (state.active === "system") await loadSettings()
    if (state.active === "monitor") await loadMonitor()
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
  if (currentRole.value === "super_admin") {
    const [user, device, sales, activity, trend, songs, feedback, salesRegion, monitor] = await Promise.all([
      silent(() => api("/api/admin/super/overview/user-count"), {}),
      silent(() => api("/api/admin/super/overview/device-count"), {}),
      silent(() => api("/api/admin/super/overview/sales-amount"), {}),
      silent(() => api("/api/admin/super/overview/activity-rate"), {}),
      silent(() => api("/api/admin/super/trend/growth", { params: { type: "device", dimension: "day" } }), { list: [] }),
      silent(() => api("/api/admin/market/top-songs"), { list: [] }),
      silent(() => api("/api/admin/super/feedback/list", { params: { page: 1, pageSize: 5 } }), { list: [], total: 0 }),
      silent(() => api("/api/admin/super/region/sales-heatmap"), { list: [] }),
      silent(() => api("/api/admin/super/monitor"), { metrics: {}, exceptions: [] }),
    ])
    state.overview = { user, device, sales, activity }
    state.trend = trend
    state.songs = songs.list || []
    state.feedback = feedback
    state.region.sales = salesRegion.list || []
    state.monitor = monitor
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

  await Promise.all([loadDevices(), loadFirmware(), loadFeedback(), loadLogs(), loadAlerts()])
}

async function loadDecision() {
  const prefix = currentRole.value === "market_admin" ? "/api/admin/market" : "/api/admin/super"
  state.decision = await api(`${prefix}/decision/summary`)
}

async function loadTrend() {
  if (currentRole.value === "super_admin") {
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

async function loadReports() {
  const prefix = currentRole.value === "market_admin" ? "/api/admin/market" : "/api/admin/super"
  state.reports = await api(`${prefix}/reports`)
}

async function loadFeedback() {
  const prefix = currentRole.value === "operator_admin" ? "/api/admin/operator" : "/api/admin/super"
  state.feedback = await api(`${prefix}/feedback/list`, { params: { page: 1, pageSize: 20 } })
}

async function loadDevices() {
  state.devices = await api("/api/admin/operator/device/list")
  const first = state.devices.list?.[0]
  if (first) {
    state.runtime = await silent(
      () => api("/api/admin/operator/device/runtime-status", { params: { deviceId: first.deviceId } }),
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

async function loadFirmware() {
  const [firmware, packages, tasks] = await Promise.all([
    api("/api/admin/operator/device/firmware-version"),
    silent(() => api("/api/admin/operator/device/firmware-packages"), { total: 0, list: [] }),
    silent(() => api("/api/admin/operator/device/firmware-tasks"), { total: 0, list: [] }),
  ])
  state.firmware = firmware
  state.firmwarePackages = packages
  state.firmwareTasks = tasks
}

async function loadTasks() {
  state.firmwareTasks = await api("/api/admin/operator/device/firmware-tasks")
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

async function loadSettings() {
  state.settings = await api("/api/admin/super/system/config")
}

async function loadMonitor() {
  state.monitor = await api("/api/admin/super/monitor")
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
  state.detail = await api("/api/admin/operator/device/detail", { params: { deviceId: item.deviceId } })
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

async function createFirmwareTask() {
  const targetVersion = state.firmware?.latestVersion || "1.0.5"
  await api("/api/admin/operator/device/firmware-task", {
    method: "POST",
    body: { targetVersion, targetScope: "灰度 20%" },
  })
  ElMessage.success("固件升级任务已创建")
  await loadFirmware()
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
      inputValue: "设备固件升级通知",
      confirmButtonText: "创建",
      cancelButtonText: "取消",
    })
    await api("/api/admin/super/notices", {
      method: "POST",
      body: { title: value, type: "notice", status: "draft" },
    })
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

onMounted(restoreSession)
</script>

<template>
  <div v-if="state.booting" class="boot-screen">
    <div class="boot-card">正在唤醒声盒后台...</div>
  </div>

  <main v-else-if="!isLoggedIn" class="login-shell">
    <section class="login-brand">
      <div class="brand-mark">Mini</div>
      <p class="eyebrow">Smart Speaker Console</p>
      <h1>声盒 Mini</h1>
      <p>智能音箱设备、音乐运营、用户反馈与系统配置的统一后台。</p>
    </section>

    <section class="login-panel" @keyup.enter="handleLogin">
      <p class="eyebrow">Welcome back</p>
      <h2>登录后台</h2>
      <label class="field">
        <span>用户名</span>
        <input v-model="state.loginForm.username" autocomplete="username" placeholder="admin / market / operator" />
      </label>
      <label class="field">
        <span>密码</span>
        <input v-model="state.loginForm.password" autocomplete="current-password" type="password" placeholder="请输入密码" />
      </label>
      <label class="check-row">
        <input v-model="state.loginForm.remember" type="checkbox" />
        <span>记住用户名</span>
      </label>
      <button class="primary-button" :disabled="state.loading" @click="handleLogin">
        {{ state.loading ? "登录中..." : "账号登录" }}
      </button>
      <button class="ghost-button wide" :disabled="state.loading" @click="handleWechatLogin">
        微信快捷登录
      </button>
      <p class="api-note">API：{{ apiLabel }}</p>
    </section>
  </main>

  <main v-else class="app-shell">
    <aside class="sidebar">
      <div class="brand">
        <div class="logo">声</div>
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
            {{ item.label }}
          </button>
        </section>
      </nav>

      <div class="user-card">
        <div class="avatar">{{ state.admin?.username?.slice(0, 1).toUpperCase() }}</div>
        <div>
          <strong>{{ state.admin?.realName || state.admin?.username }}</strong>
          <small>{{ currentRoleName }}</small>
        </div>
        <button @click="handleLogout">退出</button>
      </div>
    </aside>

    <section class="content">
      <header class="topbar">
        <div>
          <p class="eyebrow">{{ currentRoleName }}</p>
          <h1>{{ activeMenu.label }}</h1>
          <p class="muted">最近同步：{{ state.lastUpdated || "等待刷新" }}</p>
        </div>
        <div class="top-actions">
          <label class="search">
            <span>搜索</span>
            <input v-model="state.keyword" placeholder="设备、反馈、用户..." />
          </label>
          <button class="ghost-button" :disabled="state.loading" @click="loadPage()">刷新</button>
        </div>
      </header>

      <section class="metrics-grid">
        <article v-for="card in metricCards" :key="card.label" :class="['metric-card', card.tone]">
          <p>{{ card.label }}</p>
          <strong>{{ card.value }}</strong>
          <span>{{ card.hint }}</span>
        </article>
      </section>

      <section v-if="state.active === 'overview'" class="dashboard-grid">
        <article class="panel">
          <div class="panel-head">
            <div>
              <h3>{{ currentRole === 'operator_admin' ? '设备运行概览' : '增长趋势' }}</h3>
              <p>{{ currentRole === 'operator_admin' ? '当前播放、音量、电量与在线状态' : '按角色展示核心业务指标' }}</p>
            </div>
          </div>
          <div v-if="currentRole === 'operator_admin'" class="live-grid">
            <div><span>当前歌曲</span><strong>{{ state.runtime?.currentSong || "暂无播放" }}</strong><small>{{ state.runtime?.currentArtist || "未知艺术家" }}</small></div>
            <div><span>音量</span><strong>{{ state.runtime?.volume ?? "-" }}</strong><small>电量 {{ state.runtime?.battery ?? "-" }}%</small></div>
            <div><span>在线状态</span><strong>{{ state.runtime?.online ? "在线" : "离线" }}</strong><small>{{ state.runtime?.lastHeartbeat || "-" }}</small></div>
          </div>
          <div v-else class="bar-chart">
            <div v-for="item in state.trend.list" :key="item.date" class="bar-item">
              <div class="bar" :style="{ height: barHeight(item.value, maxOf(state.trend.list)) }"></div>
              <span>{{ labelDate(item.date) }}</span>
              <small>{{ item.value }}</small>
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
          <div class="panel-head"><div><h3>播放趋势</h3><p>来自 Daily_Stats 聚合</p></div></div>
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
          <div v-if="currentRole === 'super_admin'" class="segmented">
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
        <div v-else class="bar-chart large">
          <div v-for="item in state.trend.list" :key="item.date" class="bar-item">
            <div class="bar" :style="{ height: barHeight(item.value, maxOf(state.trend.list), 20, 260) }"></div>
            <span>{{ labelDate(item.date) }}</span>
            <small>{{ item.value }}</small>
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
          <ul class="pill-list">
            <li v-for="item in list" :key="item[key]" class="pill-row">
              <strong>{{ item[key] }}</strong>
              <span>{{ formatNumber(item.count) }}</span>
            </li>
          </ul>
        </article>
      </section>

      <section v-if="state.active === 'value'" class="two-column">
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
      </section>

      <section v-if="state.active === 'segments'" class="panel full">
        <div class="panel-head"><div><h3>用户分群</h3><p>按活跃、留存、绑定与偏好建立运营人群</p></div><button class="ghost-button" @click="exportRows('segments.csv', state.segments.list)">导出</button></div>
        <div class="data-table">
          <div v-for="item in state.segments.list" :key="item.name" class="table-row">
            <strong>{{ item.name }}</strong><span>{{ item.rule }} / {{ item.action }}</span><em>{{ formatNumber(item.count) }}</em>
          </div>
        </div>
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
        <div class="data-table">
          <div v-for="song in state.songs" :key="`${song.rank}-${song.songName}`" class="table-row">
            <strong>#{{ song.rank }} {{ song.songName }}</strong>
            <span>{{ song.artist }} / {{ song.platform }}</span>
            <em>{{ formatNumber(song.playCount) }} 次</em>
          </div>
        </div>
      </section>

      <section v-if="state.active === 'reports'" class="panel full">
        <div class="panel-head"><div><h3>决策报表</h3><p>日报、周报、月报，支持导出</p></div><button class="ghost-button" @click="exportRows('reports.csv', state.reports.list)">导出 Excel</button></div>
        <div class="data-table">
          <div v-for="report in state.reports.list" :key="report.reportId" class="table-row">
            <strong>{{ report.name }}</strong><span>{{ report.summary }}</span><em>{{ report.exportFormats?.join(' / ') }}</em>
          </div>
        </div>
      </section>

      <section v-if="state.active === 'feedback'" class="two-column detail-layout">
        <article class="panel">
          <div class="panel-head"><div><h3>用户反馈</h3><p>共 {{ state.feedback.total }} 条</p></div></div>
          <div class="data-table">
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
          <div class="data-table">
            <div v-for="item in filteredDevices" :key="item.deviceId" class="table-row device-row">
              <button @click="showDeviceDetail(item)">
                <i :class="['dot', { online: item.online }]"></i>
                <strong>{{ item.deviceName }}</strong>
                <span>{{ item.modelName }} / {{ item.firmwareVersion }}</span>
              </button>
              <div class="row-actions">
                <button @click="renameDevice(item)">改名</button>
                <button @click="unbindDevice(item)">解绑</button>
              </div>
            </div>
          </div>
        </article>
        <article class="panel detail-card">
          <h3>设备详情</h3>
          <template v-if="state.detail?.deviceId">
            <strong>{{ state.detail.deviceName }}</strong>
            <span>型号：{{ state.detail.modelName }} / 归属：{{ state.detail.ownerName }}</span>
            <small>音量 {{ state.detail.volume }}，电量 {{ state.detail.battery }}%，网络 {{ state.detail.currentNetwork }}</small>
            <small>最近在线：{{ state.detail.lastOnlineAt }}</small>
          </template>
          <p v-else class="muted">选择设备查看基础信息、绑定用户和实时状态。</p>
        </article>
      </section>

      <section v-if="state.active === 'groups'" class="panel full">
        <div class="panel-head"><div><h3>设备分组</h3><p>按型号、固件和在线状态聚合</p></div></div>
        <div class="data-table">
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

      <section v-if="state.active === 'firmware'" class="dashboard-grid">
        <article class="panel">
          <div class="panel-head"><div><h3>{{ state.firmware?.deviceName || "设备固件" }}</h3><p>当前版本 {{ state.firmware?.currentVersion || "-" }}，最新版本 {{ state.firmware?.latestVersion || "-" }}</p></div></div>
          <button class="primary-button compact" :disabled="!state.firmware?.needUpdate" @click="createFirmwareTask">
            {{ state.firmware?.needUpdate ? "下发灰度升级任务" : "无需更新" }}
          </button>
        </article>
        <article class="panel">
          <div class="panel-head"><div><h3>固件包</h3><p>稳定版、灰度版、回滚版本</p></div></div>
          <ul class="pill-list">
            <li v-for="item in state.firmwarePackages.list" :key="item.packageId" class="pill-row">
              <strong>{{ item.version }} · {{ item.modelName }}</strong>
              <span>{{ statusText(item.status) }} / {{ item.sizeMb }}MB</span>
            </li>
          </ul>
        </article>
      </section>

      <section v-if="state.active === 'tasks'" class="panel full">
        <div class="panel-head"><div><h3>固件升级任务</h3><p>查看任务状态、成功数、失败数和失败原因</p></div><button class="ghost-button" @click="createFirmwareTask">新建灰度任务</button></div>
        <div class="data-table">
          <div v-for="task in state.firmwareTasks.list" :key="task.taskId" class="table-row">
            <strong>{{ task.taskId }} / {{ task.targetVersion }}</strong>
            <span>{{ task.targetScope }} / 成功 {{ task.successCount }} / 失败 {{ task.failCount }}</span>
            <em>{{ statusText(task.status) }}</em>
          </div>
        </div>
      </section>

      <section v-if="state.active === 'logs'" class="two-column detail-layout">
        <article class="panel">
          <div class="panel-head"><div><h3>设备日志</h3><p>设备上线、升级、异常事件</p></div></div>
          <div class="data-table">
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
        <div class="panel-head"><div><h3>管理员与绑定用户</h3><p>账号、角色、状态和最近登录</p></div><button class="ghost-button" @click="exportRows('users.csv', state.users.list)">导出</button></div>
        <div class="data-table">
          <div v-for="user in state.users.list" :key="user.adminId" class="table-row">
            <strong>{{ user.realName }} · {{ user.username }}</strong>
            <span>{{ user.roleName }} / {{ user.jobNo }} / {{ user.phone || "未配置手机号" }}</span>
            <em>{{ statusText(user.status) }}</em>
          </div>
        </div>
      </section>

      <section v-if="state.active === 'roles'" class="panel full">
        <div class="panel-head"><div><h3>角色权限矩阵</h3><p>创建角色、修改权限、授权与撤权的基础视图</p></div></div>
        <div class="data-table">
          <div v-for="role in state.roles.list" :key="role.role" class="table-row">
            <strong>{{ role.roleName }}</strong>
            <span>{{ role.description }} / {{ role.permissions.join("、") }}</span>
            <em>{{ role.userCount }} 人</em>
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

      <section v-if="state.active === 'monitor'" class="dashboard-grid">
        <article class="panel">
          <div class="panel-head"><div><h3>服务运行状态</h3><p>API、MySQL、MongoDB</p></div></div>
          <ul class="pill-list">
            <li v-for="service in state.monitor.services" :key="service.name" class="pill-row">
              <strong>{{ service.name }}</strong><span>{{ service.status }} / {{ service.latencyMs }}ms</span>
            </li>
          </ul>
        </article>
        <article class="panel">
          <div class="panel-head"><div><h3>最近异常</h3><p>接口错误率、存储、反馈与离线设备</p></div></div>
          <ul class="pill-list">
            <li v-for="item in state.monitor.exceptions" :key="item.code" class="pill-row">
              <strong>{{ item.title }}</strong><span>{{ item.count }}</span>
            </li>
          </ul>
        </article>
      </section>

      <section v-if="state.active === 'notices'" class="panel full">
        <div class="panel-head"><div><h3>系统公告</h3><p>后台公告、维护通知、升级通知</p></div><button class="primary-button compact" @click="createNotice">新建公告</button></div>
        <div class="data-table">
          <div v-for="notice in state.notices.list" :key="notice.noticeId" class="table-row">
            <strong>{{ notice.title }}</strong><span>{{ notice.type }} / {{ notice.createdAt }}</span><em>{{ statusText(notice.status) }}</em>
          </div>
        </div>
      </section>

      <section v-if="state.active === 'audit'" class="panel full">
        <div class="panel-head"><div><h3>审计与安全日志</h3><p>操作日志、登录日志、安全事件</p></div><button class="ghost-button" @click="exportRows('audit.csv', state.audit.list)">导出</button></div>
        <div class="data-table">
          <div v-for="log in state.audit.list" :key="log.logId" class="table-row">
            <strong>{{ log.event }}</strong><span>{{ log.actor }} / {{ log.ip }}</span><em>{{ log.createdAt }}</em>
          </div>
        </div>
      </section>

      <section v-if="state.active === 'account'" class="panel full account-card">
        <div class="avatar big">{{ state.admin?.username?.slice(0, 1).toUpperCase() }}</div>
        <div>
          <h3>{{ state.admin?.realName || state.admin?.username }}</h3>
          <p>{{ state.admin?.position || currentRoleName }} / 工号 {{ state.admin?.jobNo || "-" }}</p>
          <p>{{ state.admin?.phone || "未配置手机号" }} · {{ state.admin?.email || "未配置邮箱" }}</p>
          <p>权限：{{ currentRoleName }}，可访问 {{ visibleMenus.length }} 个后台模块。</p>
        </div>
      </section>
    </section>
  </main>
</template>

<style scoped>
:global(*) {
  box-sizing: border-box;
}

:global(body) {
  margin: 0;
  min-width: 320px;
  min-height: 100vh;
  color: #1f2a33;
  background: #eef3f1;
  font-family: Inter, "PingFang SC", "Microsoft YaHei", Arial, sans-serif;
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
  border: 1px solid rgba(195, 209, 203, 0.9);
  border-radius: 8px;
  background: rgba(255, 255, 255, 0.82);
  box-shadow: 0 18px 50px rgba(44, 64, 56, 0.08);
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
    linear-gradient(135deg, rgba(38, 78, 88, 0.92), rgba(36, 107, 88, 0.88)),
    url("https://images.unsplash.com/photo-1516321318423-f06f85e504b3?auto=format&fit=crop&w=1400&q=80") center/cover;
}

.brand-mark,
.logo,
.avatar {
  display: grid;
  place-items: center;
  width: 46px;
  height: 46px;
  border-radius: 8px;
  background: #2f7d62;
  color: white;
  font-weight: 800;
}

.login-brand h1 {
  margin: 0;
  font-size: clamp(42px, 7vw, 82px);
  line-height: 1;
}

.login-brand p {
  max-width: 520px;
  margin: 0;
  line-height: 1.8;
}

.login-panel {
  align-self: center;
  width: min(440px, calc(100% - 48px));
  margin: 0 auto;
  padding: 34px;
}

.login-panel h2 {
  margin: 6px 0 28px;
  font-size: 30px;
}

.field {
  display: grid;
  gap: 8px;
  margin-bottom: 16px;
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
  color: #64746e;
}

.field input,
.search input {
  width: 100%;
  border: 1px solid #cfdad5;
  border-radius: 8px;
  padding: 12px 14px;
  background: white;
  color: #1f2a33;
  outline: none;
}

.check-row,
.topbar,
.top-actions,
.brand,
.user-card,
.panel-head,
.firmware-panel,
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
  border: 0;
  border-radius: 8px;
  padding: 11px 16px;
}

.primary-button {
  width: 100%;
  background: #2f7d62;
  color: white;
  font-weight: 700;
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
  background: #e8efec;
  color: #285244;
  font-weight: 700;
}

.ghost-button.wide {
  width: 100%;
  margin-top: 10px;
}

.api-note {
  margin-bottom: 0;
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
  padding: 24px;
  background: #17261f;
  color: white;
}

.brand {
  gap: 12px;
  margin-bottom: 26px;
}

.brand small,
.nav-groups p,
.user-card small {
  display: block;
}

.nav-groups {
  display: grid;
  gap: 18px;
}

.nav-groups p {
  margin: 0 0 8px;
  color: #8db3a4;
  font-size: 12px;
  font-weight: 800;
}

.nav-item {
  display: block;
  width: 100%;
  margin-bottom: 6px;
  border: 0;
  border-radius: 8px;
  padding: 10px 12px;
  background: transparent;
  color: #dce8e3;
  text-align: left;
}

.nav-item.active,
.nav-item:hover {
  background: #2f7d62;
  color: white;
}

.user-card {
  gap: 10px;
  margin-top: 24px;
  padding: 14px;
  background: rgba(255, 255, 255, 0.08);
  border-color: rgba(255, 255, 255, 0.14);
}

.user-card button {
  margin-left: auto;
  background: rgba(255, 255, 255, 0.12);
  color: white;
}

.content {
  min-width: 0;
  padding: 28px;
}

.topbar {
  justify-content: space-between;
  gap: 18px;
  margin-bottom: 22px;
}

.topbar h1 {
  margin: 4px 0;
  font-size: clamp(28px, 4vw, 42px);
}

.eyebrow {
  margin: 0;
  color: #2f7d62;
  text-transform: uppercase;
  letter-spacing: 0;
  font-size: 12px;
  font-weight: 800;
}

.login-brand .eyebrow {
  color: #bde9d7;
}

.muted {
  margin: 0;
  line-height: 1.7;
}

.top-actions {
  gap: 10px;
}

.search {
  display: flex;
  align-items: center;
  gap: 10px;
  min-width: 260px;
}

.metrics-grid,
.dashboard-grid,
.two-column,
.profile-grid,
.mini-cards,
.form-grid {
  display: grid;
  gap: 16px;
}

.metrics-grid {
  grid-template-columns: repeat(4, minmax(0, 1fr));
  margin-bottom: 18px;
}

.metric-card {
  min-height: 128px;
  padding: 22px;
}

.metric-card p,
.metric-card strong,
.metric-card span {
  margin: 0;
}

.metric-card strong {
  display: block;
  margin: 16px 0 10px;
  font-size: clamp(26px, 4vw, 40px);
  line-height: 1;
}

.metric-card.green strong,
.badge.normal {
  color: #2f7d62;
}

.metric-card.blue strong,
.badge.info {
  color: #2563a5;
}

.metric-card.orange strong,
.badge.warning {
  color: #bf6b2c;
}

.metric-card.red strong {
  color: #a74848;
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
  padding: 22px;
}

.panel.full {
  grid-column: 1 / -1;
}

.panel-head {
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 18px;
}

.panel-head h3,
.panel-head p {
  margin: 0;
}

.panel-head h3 {
  font-size: 20px;
}

.bar-chart {
  display: flex;
  align-items: end;
  justify-content: space-between;
  gap: 10px;
  min-height: 220px;
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
  border-radius: 8px 8px 4px 4px;
  background: linear-gradient(180deg, #2f7d62, #7eb39d);
}

.bar-item span,
.bar-item small {
  color: #64746e;
  font-size: 12px;
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
  border: 1px solid #d8e2de;
  border-radius: 8px;
  background: #f9fbfa;
}

.rank-list li {
  display: grid;
  grid-template-columns: 34px 1fr auto;
  align-items: center;
  gap: 12px;
  padding: 12px;
}

.rank-list span {
  display: grid;
  place-items: center;
  width: 28px;
  height: 28px;
  border-radius: 8px;
  background: #e2f0eb;
  color: #2f7d62;
  font-weight: 800;
}

.rank-list strong,
.table-row strong {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.rank-list em,
.table-row em,
.mini-cards em {
  color: #bf6b2c;
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
  color: #64746e;
}

.live-grid strong,
.mini-cards strong {
  display: block;
  margin: 10px 0;
  font-size: 26px;
}

.mini-cards {
  grid-template-columns: repeat(4, minmax(0, 1fr));
}

.heat-list {
  display: grid;
  gap: 12px;
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

.heat-row div {
  height: 12px;
  overflow: hidden;
  border-radius: 8px;
  background: #e7efeb;
}

.heat-row i {
  display: block;
  height: 100%;
  border-radius: inherit;
  background: linear-gradient(90deg, #2f7d62, #d39254);
}

.pill-row {
  display: flex;
  justify-content: space-between;
  gap: 14px;
  padding: 13px;
}

.badge {
  border-radius: 8px;
  padding: 4px 8px;
  background: #edf3f1;
  font-weight: 800;
}

.hero-number {
  min-height: 230px;
}

.hero-number span {
  color: #64746e;
}

.hero-number strong {
  display: block;
  margin: 28px 0 18px;
  color: #2f7d62;
  font-size: clamp(52px, 9vw, 92px);
  font-weight: 300;
}

.data-table {
  display: grid;
  gap: 10px;
}

.table-row {
  display: grid;
  grid-template-columns: minmax(100px, 0.28fr) minmax(0, 1fr) auto;
  align-items: center;
  gap: 14px;
  padding: 13px 15px;
}

.table-row:not(.device-row) {
  cursor: pointer;
}

.segmented {
  display: flex;
  gap: 6px;
  padding: 5px;
  border-radius: 8px;
  background: #edf3f1;
}

.segmented button {
  border: 0;
  border-radius: 8px;
  padding: 8px 13px;
  background: transparent;
  color: #466056;
}

.segmented button.active {
  background: #2f7d62;
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
  background: #aebbb6;
}

.dot.online {
  background: #2f7d62;
  box-shadow: 0 0 0 5px rgba(47, 125, 98, 0.14);
}

.row-actions {
  display: flex;
  gap: 8px;
}

.row-actions button {
  border: 0;
  border-radius: 8px;
  padding: 8px 12px;
  background: #e3efea;
  color: #285244;
}

.account-card {
  justify-content: flex-start;
  gap: 20px;
}

.avatar.big {
  width: 72px;
  height: 72px;
  font-size: 28px;
}

.account-card h3,
.account-card p {
  margin: 4px 0;
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
  .device-row > button {
    grid-template-columns: 1fr;
  }

  .row-actions {
    justify-content: flex-start;
  }
}
</style>

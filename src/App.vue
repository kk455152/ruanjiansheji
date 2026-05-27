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
  { key: "trend", label: "趋势分析", section: "核心看板", roles: ["super_admin", "market_admin", "operator_admin"] },
  { key: "region", label: "区域热力图", section: "分析洞察", roles: ["super_admin", "market_admin"] },
  { key: "profile", label: "用户画像", section: "分析洞察", roles: ["super_admin", "market_admin"] },
  { key: "value", label: "用户价值", section: "分析洞察", roles: ["super_admin", "market_admin"] },
  { key: "songs", label: "热歌排行", section: "分析洞察", roles: ["super_admin", "market_admin"] },
  { key: "feedback", label: "用户反馈", section: "运营管理", roles: ["super_admin", "operator_admin"] },
  { key: "devices", label: "设备管理", section: "运营管理", roles: ["super_admin", "operator_admin"] },
  { key: "firmware", label: "设备固件", section: "运营管理", roles: ["super_admin", "operator_admin"] },
  { key: "logs", label: "设备日志", section: "运营管理", roles: ["super_admin", "operator_admin"] },
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
  trend: { type: "user", dimension: "day", list: [] },
  region: { sales: [], users: [] },
  profile: {
    age: [],
    region: [],
    activity: [],
    service: [],
  },
  value: {},
  songs: [],
  retention: [],
  feedback: { total: 0, list: [] },
  devices: { total: 0, list: [] },
  runtime: null,
  firmware: null,
  logs: { total: 0, list: [] },
  detail: null,
})

const isLoggedIn = computed(() => Boolean(state.token && state.admin))
const currentRole = computed(() => state.admin?.role || "")
const currentRoleName = computed(() => state.admin?.roleName || roleNames[currentRole.value] || "未登录")
const activeMenu = computed(() => menus.find((item) => item.key === state.active) || menus[0])
const apiLabel = computed(() => API_BASE || "当前站点")

const visibleMenus = computed(() => menus.filter((item) => item.roles.includes(currentRole.value)))
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
      { label: "在线率", value: percent(devices.length ? online / devices.length : 0), hint: "来自设备列表", tone: "orange" },
      { label: "固件版本", value: state.firmware?.currentVersion || "-", hint: state.firmware?.needUpdate ? "可更新" : "已是最新", tone: "ink" },
      { label: "待处理反馈", value: formatNumber(pending), hint: `共 ${state.feedback.total || 0} 条`, tone: "green" },
    ]
  }

  if (currentRole.value === "market_admin") {
    const totalPlays = state.songs.reduce((sum, item) => sum + Number(item.playCount || 0), 0)
    const avgRetention = average(state.retention.map((item) => item.day7RetentionRate))
    return [
      { label: "热歌播放", value: formatNumber(totalPlays), hint: `${state.songs.length} 首上榜歌曲`, tone: "green" },
      { label: "高活用户", value: formatNumber(state.value.highActiveUserCount || 0), hint: "近周期活跃", tone: "orange" },
      { label: "普通用户", value: formatNumber(state.value.normalUserCount || 0), hint: "用户价值分层", tone: "ink" },
      { label: "7日留存", value: percent(avgRetention), hint: "购买设备后持续使用", tone: "green" },
    ]
  }

  const deviceTotal = state.overview.device?.deviceCount || 0
  const onlineRate = deviceTotal ? (state.overview.device?.onlineDeviceCount || 0) / deviceTotal : 0
  return [
    { label: "总用户", value: formatNumber(state.overview.user?.userCount || 0), hint: `新增 ${formatNumber(state.overview.user?.newUserCount || 0)}`, tone: "green" },
    { label: "设备数", value: formatNumber(deviceTotal), hint: `在线率 ${percent(onlineRate)}`, tone: "ink" },
    { label: "销售额", value: money(state.overview.sales?.salesAmount || 0), hint: `${formatNumber(state.overview.sales?.orderCount || 0)} 笔订单`, tone: "orange" },
    { label: "活跃度", value: percent(state.overview.activity?.activityRate || 0), hint: `${formatNumber(state.overview.activity?.activeUserCount || 0)} 活跃用户`, tone: "green" },
  ]
})

const filteredDevices = computed(() => {
  const word = state.keyword.trim().toLowerCase()
  if (!word) return state.devices.list || []
  return (state.devices.list || []).filter((item) =>
    [item.deviceId, item.deviceName, item.ownerName, item.modelName].some((value) =>
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

function canUse(key) {
  return visibleMenus.value.some((item) => item.key === key)
}

function average(values) {
  const usable = values.map(Number).filter((item) => Number.isFinite(item))
  return usable.length ? usable.reduce((sum, item) => sum + item, 0) / usable.length : 0
}

function formatNumber(value) {
  return Number(value || 0).toLocaleString("zh-CN")
}

function money(value) {
  const number = Number(value || 0)
  if (number >= 10000) return `${(number / 10000).toFixed(1)}万`
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

function barHeight(value, max) {
  return `${Math.max(14, Math.round((Number(value || 0) / Math.max(max, 1)) * 150))}px`
}

function setUpdated() {
  state.lastUpdated = new Date().toLocaleString("zh-CN", {
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  })
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
    const token = data.token || data.access_token
    state.token = token
    state.admin = data.adminInfo
    localStorage.setItem("admin_token", token)
    localStorage.setItem("admin_info", JSON.stringify(data.adminInfo))
    if (state.loginForm.remember) {
      localStorage.setItem("admin_username", state.loginForm.username.trim())
    } else {
      localStorage.removeItem("admin_username")
    }
    state.loginForm.password = ""
    state.active = firstMenuForRole(data.adminInfo.role)
    ElMessage.success("登录成功，正在加载后台数据")
    await loadPage(true)
  } catch (error) {
    ElMessage.error(error.message || "登录失败")
  } finally {
    state.loading = false
  }
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
  await nextTick()
  await loadPage()
}

async function loadPage(initial = false) {
  if (!isLoggedIn.value) return
  state.loading = true

  try {
    if (initial || state.active === "overview") await loadOverview()
    if (state.active === "trend") await loadTrend()
    if (state.active === "region") await loadRegion()
    if (state.active === "profile") await loadProfile()
    if (state.active === "value") await loadValue()
    if (state.active === "songs") await loadSongs()
    if (state.active === "feedback") await loadFeedback()
    if (state.active === "devices") await loadDevices()
    if (state.active === "firmware") await loadFirmware()
    if (state.active === "logs") await loadLogs()
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
    await Promise.all([loadSongs(), loadValue(), loadRetention(), loadRegion(), loadProfile()])
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

  await Promise.all([loadDevices(), loadFirmware(), loadFeedback(), loadLogs()])
}

async function loadTrend() {
  if (currentRole.value === "super_admin") {
    state.trend = await api("/api/admin/super/trend/growth", {
      params: { type: state.trend.type || "user", dimension: state.trend.dimension || "day" },
    })
  } else if (currentRole.value === "market_admin") {
    await loadRetention()
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

async function loadFirmware() {
  state.firmware = await api("/api/admin/operator/device/firmware-version")
}

async function loadLogs() {
  state.logs = await api("/api/admin/operator/device/logs", { params: { page: 1, pageSize: 20 } })
}

async function loadAccount() {
  state.admin = await api("/api/admin/profile")
  localStorage.setItem("admin_info", JSON.stringify(state.admin))
}

async function showFeedbackDetail(item) {
  const prefix = currentRole.value === "operator_admin" ? "/api/admin/operator" : "/api/admin/super"
  state.detail = await api(`${prefix}/feedback/detail`, { params: { feedbackId: item.feedbackId } })
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

async function updateFirmware() {
  const deviceId = state.firmware?.deviceId || state.devices.list?.[0]?.deviceId
  const targetVersion = state.firmware?.latestVersion
  await api("/api/admin/operator/device/update-firmware", {
    method: "POST",
    body: { deviceId, targetVersion },
  })
  ElMessage.success("固件升级任务已创建")
  await loadFirmware()
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
      <div>
        <p class="eyebrow">后台管理系统</p>
        <h1>声盒 Mini</h1>
        <p class="login-copy">让设备管理、音乐趋势与用户反馈在一张柔和的工作台里安静流动。</p>
      </div>
    </section>

    <section class="login-panel" @keyup.enter="handleLogin">
      <p class="eyebrow">Welcome back</p>
      <h2>欢迎登录</h2>
      <p class="muted">请使用服务器后台管理员账号进入系统</p>
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
        {{ state.loading ? "登录中..." : "登录" }}
      </button>
      <p class="api-note">API：{{ apiLabel }}</p>
    </section>
  </main>

  <main v-else class="app-shell">
    <aside class="sidebar">
      <div class="brand">
        <div class="logo">声</div>
        <div>
          <h2>声盒 Mini</h2>
          <p>{{ currentRoleName }}</p>
        </div>
      </div>

      <nav class="nav-groups">
        <section v-for="group in groupedMenus" :key="group.section" class="nav-group">
          <p>{{ group.section }}</p>
          <button
            v-for="item in group.items"
            :key="item.key"
            :class="['nav-item', { active: state.active === item.key }]"
            @click="selectPage(item.key)"
          >
            <span>{{ item.label.slice(0, 1) }}</span>
            {{ item.label }}
          </button>
        </section>
      </nav>

      <div class="user-card">
        <div class="avatar">{{ state.admin?.username?.slice(0, 1).toUpperCase() }}</div>
        <div>
          <strong>{{ state.admin?.realName || state.admin?.username }}</strong>
          <small>{{ state.admin?.jobNo || "在线" }}</small>
        </div>
      </div>
    </aside>

    <section class="content">
      <header class="topbar">
        <div>
          <p class="eyebrow">Web Admin Console</p>
          <h1>{{ activeMenu.label }}</h1>
          <p class="muted">最近同步：{{ state.lastUpdated || "等待刷新" }}</p>
        </div>
        <div class="top-actions">
          <label class="search">
            <span>搜索</span>
            <input v-model="state.keyword" placeholder="设备、反馈、用户..." />
          </label>
          <button class="ghost-button" :disabled="state.loading" @click="loadPage()">刷新</button>
          <button class="ghost-button" @click="handleLogout">退出</button>
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
        <article class="panel wide">
          <div class="panel-head">
            <div>
              <h3>{{ currentRole === "operator_admin" ? "设备运行概览" : "增长走势" }}</h3>
              <p>{{ currentRole === "operator_admin" ? "在线设备、日志与固件任务" : "接口实时返回的数据序列" }}</p>
            </div>
          </div>
          <div v-if="currentRole === 'operator_admin'" class="device-live">
            <div>
              <small>当前歌曲</small>
              <strong>{{ state.runtime?.currentSong || "暂无播放" }}</strong>
              <span>{{ state.runtime?.currentArtist || "未知艺术家" }}</span>
            </div>
            <div>
              <small>音量</small>
              <strong>{{ state.runtime?.volume ?? "-" }}</strong>
              <span>电量 {{ state.runtime?.battery ?? "-" }}%</span>
            </div>
            <div>
              <small>心跳</small>
              <strong>{{ state.runtime?.online ? "在线" : "离线" }}</strong>
              <span>{{ state.runtime?.lastHeartbeat || "-" }}</span>
            </div>
          </div>
          <div v-else class="bar-chart">
            <div
              v-for="item in state.trend.list"
              :key="item.date"
              class="bar-item"
              :title="`${item.date}: ${item.value}`"
            >
              <div class="bar" :style="{ height: barHeight(item.value, maxOf(state.trend.list)) }"></div>
              <span>{{ labelDate(item.date) }}</span>
            </div>
          </div>
        </article>

        <article class="panel">
          <div class="panel-head">
            <div>
              <h3>{{ currentRole === "operator_admin" ? "最近反馈" : "活跃用户热歌排行" }}</h3>
              <p>{{ currentRole === "operator_admin" ? "来自用户反馈接口" : "来自热歌排行接口" }}</p>
            </div>
          </div>
          <ul v-if="currentRole !== 'operator_admin'" class="rank-list">
            <li v-for="song in state.songs.slice(0, 6)" :key="`${song.rank}-${song.songName}`">
              <span>{{ song.rank }}</span>
              <strong>{{ song.songName }}</strong>
              <em>{{ formatNumber(song.playCount) }} 次</em>
            </li>
          </ul>
          <ul v-else class="rank-list">
            <li v-for="item in state.feedback.list.slice(0, 6)" :key="item.feedbackId">
              <span>{{ item.rating || "F" }}</span>
              <strong>{{ item.nickname }}</strong>
              <em>{{ item.statusText }}</em>
            </li>
          </ul>
        </article>

        <article v-if="currentRole !== 'operator_admin'" class="panel full">
          <div class="panel-head">
            <div>
              <h3>区域动能</h3>
              <p>销售额最高的省份，用于快速判断市场热度</p>
            </div>
          </div>
          <div class="heat-list">
            <div v-for="item in state.region.sales" :key="item.regionCode" class="heat-row">
              <span>{{ item.regionName }}</span>
              <div>
                <i :style="{ width: `${Math.max(10, (item.salesAmount / maxOf(state.region.sales, 'salesAmount')) * 100)}%` }"></i>
              </div>
              <strong>{{ money(item.salesAmount) }}</strong>
            </div>
          </div>
        </article>
      </section>

      <section v-if="state.active === 'trend'" class="panel full">
        <div class="panel-head">
          <div>
            <h3>{{ currentRole === "market_admin" ? "购买后留存趋势" : currentRole === "operator_admin" ? "设备日志趋势" : "增长趋势分析" }}</h3>
            <p>{{ currentRole === "super_admin" ? "可切换用户、设备、销售额增长指标" : "根据角色自动展示可访问数据" }}</p>
          </div>
          <div v-if="currentRole === 'super_admin'" class="segmented">
            <button :class="{ active: state.trend.type === 'user' }" @click="state.trend.type = 'user'; loadTrend()">用户</button>
            <button :class="{ active: state.trend.type === 'device' }" @click="state.trend.type = 'device'; loadTrend()">设备</button>
            <button :class="{ active: state.trend.type === 'sales' }" @click="state.trend.type = 'sales'; loadTrend()">销售</button>
          </div>
        </div>
        <div v-if="currentRole === 'market_admin'" class="retention-grid">
          <article v-for="item in state.retention" :key="item.date">
            <span>{{ labelDate(item.date) }}</span>
            <strong>{{ percent(item.day7RetentionRate) }}</strong>
            <small>购买 {{ item.purchaseUserCount }} 人</small>
          </article>
        </div>
        <div v-else-if="currentRole === 'operator_admin'" class="data-table">
          <div v-for="log in state.logs.list" :key="log.logId" class="table-row" @click="showLogDetail(log)">
            <span>{{ log.logId }}</span>
            <strong>{{ log.content }}</strong>
            <em>{{ log.createdAt }}</em>
          </div>
        </div>
        <div v-else class="bar-chart large">
          <div v-for="item in state.trend.list" :key="item.date" class="bar-item">
            <div class="bar" :style="{ height: barHeight(item.value, maxOf(state.trend.list)) }"></div>
            <span>{{ labelDate(item.date) }}</span>
          </div>
        </div>
      </section>

      <section v-if="state.active === 'region'" class="two-column">
        <article class="panel">
          <div class="panel-head"><h3>销售热力</h3><p>地区销售额与订单数</p></div>
          <div class="heat-list">
            <div v-for="item in state.region.sales" :key="item.regionCode" class="heat-row">
              <span>{{ item.regionName }}</span>
              <div><i :style="{ width: `${Math.max(10, (item.salesAmount / maxOf(state.region.sales, 'salesAmount')) * 100)}%` }"></i></div>
              <strong>{{ money(item.salesAmount) }}</strong>
            </div>
          </div>
        </article>
        <article class="panel">
          <div class="panel-head"><h3>用户热力</h3><p>地区用户与活跃用户</p></div>
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
        <article v-for="block in [
          ['年龄分布', state.profile.age, 'ageRange'],
          ['地区分布', state.profile.region, 'regionName'],
          ['活跃分层', state.profile.activity, 'levelName'],
          ['绑定软件', state.profile.service, 'serviceName'],
        ]" :key="block[0]" class="panel">
          <div class="panel-head"><h3>{{ block[0] }}</h3><p>用户画像统计</p></div>
          <div class="pill-list">
            <div v-for="item in block[1]" :key="item[block[2]]" class="pill-row">
              <span>{{ item[block[2]] }}</span>
              <strong>{{ formatNumber(item.count) }}</strong>
            </div>
          </div>
        </article>
      </section>

      <section v-if="state.active === 'value'" class="two-column">
        <article class="panel hero-number">
          <span>普通用户</span>
          <strong>{{ formatNumber(state.value.normalUserCount || 0) }}</strong>
          <p>适合做唤醒、召回与新手引导。</p>
        </article>
        <article class="panel hero-number">
          <span>高活跃用户</span>
          <strong>{{ formatNumber(state.value.highActiveUserCount || 0) }}</strong>
          <p>适合做会员权益、歌单推荐与复购运营。</p>
        </article>
      </section>

      <section v-if="state.active === 'songs'" class="panel full">
        <div class="panel-head"><div><h3>热歌排行</h3><p>市场分析管理员与超级管理员可见</p></div></div>
        <div class="data-table">
          <div v-for="song in state.songs" :key="`${song.rank}-${song.songName}`" class="table-row">
            <span>#{{ song.rank }}</span>
            <strong>{{ song.songName }} - {{ song.artist }}</strong>
            <em>{{ formatNumber(song.playCount) }} 次播放</em>
          </div>
        </div>
      </section>

      <section v-if="state.active === 'feedback'" class="two-column detail-layout">
        <article class="panel">
          <div class="panel-head"><div><h3>用户反馈</h3><p>共 {{ state.feedback.total }} 条</p></div></div>
          <div class="data-table">
            <div v-for="item in filteredFeedback" :key="item.feedbackId" class="table-row" @click="showFeedbackDetail(item)">
              <span>{{ item.ratingText || item.feedbackTypeText }}</span>
              <strong>{{ item.nickname }}：{{ item.content }}</strong>
              <em>{{ item.statusText }}</em>
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
          </template>
          <p v-else class="muted">点击左侧反馈查看详情。</p>
        </article>
      </section>

      <section v-if="state.active === 'devices'" class="two-column detail-layout">
        <article class="panel">
          <div class="panel-head"><div><h3>设备列表</h3><p>共 {{ state.devices.total }} 台设备</p></div></div>
          <div class="data-table">
            <div v-for="item in filteredDevices" :key="item.deviceId" class="table-row device-row">
              <button @click="showDeviceDetail(item)">
                <span :class="['dot', { online: item.online }]"></span>
                <strong>{{ item.deviceName }}</strong>
                <em>{{ item.ownerName }} / {{ item.firmwareVersion }}</em>
              </button>
              <div class="row-actions">
                <button @click="renameDevice(item)">重命名</button>
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
          </template>
          <p v-else class="muted">点击设备查看详情。</p>
        </article>
      </section>

      <section v-if="state.active === 'firmware'" class="panel full firmware-panel">
        <div>
          <p class="eyebrow">Firmware</p>
          <h3>{{ state.firmware?.deviceName || "设备固件" }}</h3>
          <p>当前版本 {{ state.firmware?.currentVersion || "-" }}，最新版本 {{ state.firmware?.latestVersion || "-" }}</p>
        </div>
        <button class="primary-button" :disabled="!state.firmware?.needUpdate" @click="updateFirmware">
          {{ state.firmware?.needUpdate ? "下发升级任务" : "无需更新" }}
        </button>
      </section>

      <section v-if="state.active === 'logs'" class="two-column detail-layout">
        <article class="panel">
          <div class="panel-head"><div><h3>设备日志</h3><p>运维追踪与固件事件</p></div></div>
          <div class="data-table">
            <div v-for="log in state.logs.list" :key="log.logId" class="table-row" @click="showLogDetail(log)">
              <span>{{ log.logType }}</span>
              <strong>{{ log.content }}</strong>
              <em>{{ log.createdAt }}</em>
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
          <p v-else class="muted">点击日志查看完整追踪信息。</p>
        </article>
      </section>

      <section v-if="state.active === 'account'" class="panel full account-card">
        <div class="avatar big">{{ state.admin?.username?.slice(0, 1).toUpperCase() }}</div>
        <div>
          <p class="eyebrow">{{ currentRoleName }}</p>
          <h3>{{ state.admin?.realName || state.admin?.username }}</h3>
          <p>{{ state.admin?.position || currentRoleName }} / 工号 {{ state.admin?.jobNo || "-" }}</p>
          <p>{{ state.admin?.phone || "未配置手机号" }} · {{ state.admin?.email || "未配置邮箱" }}</p>
        </div>
      </section>
    </section>
  </main>
</template>

<style scoped>
:global(body) {
  margin: 0;
  min-width: 320px;
  background:
    radial-gradient(circle at 18% 18%, rgba(255, 255, 255, 0.8), transparent 28%),
    linear-gradient(135deg, #f4f7f2 0%, #dfeae2 100%);
  color: #243a31;
  font-family: "Noto Sans SC", "Microsoft YaHei", sans-serif;
}

* {
  box-sizing: border-box;
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

.boot-card {
  padding: 24px 32px;
  border-radius: 28px;
  background: rgba(255, 255, 255, 0.72);
  box-shadow: 0 20px 60px rgba(75, 112, 92, 0.14);
}

.login-shell {
  display: grid;
  grid-template-columns: minmax(320px, 42vw) 1fr;
  background: #e7f0e9;
}

.login-brand {
  display: flex;
  align-items: center;
  gap: 24px;
  padding: 72px;
  color: #f7faf4;
  background:
    radial-gradient(circle at 20% 20%, rgba(132, 169, 140, 0.4), transparent 25%),
    #253f33;
}

.brand-mark,
.logo {
  display: grid;
  place-items: center;
  border-radius: 22px;
  background: #7fa58a;
  color: white;
  font-weight: 700;
}

.brand-mark {
  width: 76px;
  height: 76px;
}

.login-brand h1 {
  margin: 8px 0 10px;
  font-size: clamp(34px, 5vw, 54px);
  letter-spacing: 0.04em;
}

.login-copy {
  max-width: 420px;
  color: rgba(247, 250, 244, 0.7);
  line-height: 1.9;
}

.login-panel {
  align-self: center;
  justify-self: center;
  width: min(420px, calc(100vw - 40px));
  padding: 36px;
  border: 1px solid rgba(255, 255, 255, 0.82);
  border-radius: 28px;
  background: rgba(255, 255, 255, 0.74);
  box-shadow: 0 28px 90px rgba(75, 112, 92, 0.18);
  backdrop-filter: blur(20px);
}

.login-panel h2 {
  margin: 8px 0 6px;
  font-size: 28px;
}

.field {
  display: block;
  margin-top: 18px;
}

.field span,
.check-row,
.api-note,
.muted,
.eyebrow {
  color: #73877c;
}

.field span {
  display: block;
  margin-bottom: 8px;
  font-size: 13px;
}

.field input,
.search input {
  width: 100%;
  border: 1px solid rgba(127, 165, 138, 0.22);
  outline: 0;
  background: rgba(255, 255, 255, 0.78);
  color: #243a31;
}

.field input {
  height: 46px;
  padding: 0 16px;
  border-radius: 16px;
}

.check-row {
  display: flex;
  align-items: center;
  gap: 8px;
  margin: 16px 0;
  font-size: 14px;
}

.primary-button,
.ghost-button {
  border: 0;
  border-radius: 999px;
  transition: transform 0.2s ease, box-shadow 0.2s ease, opacity 0.2s ease;
}

.primary-button {
  width: 100%;
  padding: 13px 18px;
  background: #6f997b;
  color: white;
  box-shadow: 0 16px 32px rgba(111, 153, 123, 0.25);
}

.primary-button:disabled,
.ghost-button:disabled {
  cursor: not-allowed;
  opacity: 0.55;
}

.primary-button:not(:disabled):hover,
.ghost-button:not(:disabled):hover {
  transform: translateY(-1px);
}

.api-note {
  margin: 16px 0 0;
  font-size: 12px;
  text-align: center;
}

.app-shell {
  display: grid;
  grid-template-columns: 260px 1fr;
}

.sidebar {
  position: sticky;
  top: 0;
  display: flex;
  flex-direction: column;
  height: 100vh;
  padding: 30px 20px;
  border-right: 1px solid rgba(255, 255, 255, 0.7);
  background: rgba(247, 250, 246, 0.64);
  backdrop-filter: blur(26px);
}

.brand {
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 4px 8px 26px;
}

.logo {
  width: 42px;
  height: 42px;
  border-radius: 15px;
}

.brand h2,
.brand p {
  margin: 0;
}

.brand h2 {
  font-size: 18px;
}

.brand p {
  margin-top: 4px;
  color: #789086;
  font-size: 12px;
}

.nav-groups {
  display: grid;
  gap: 18px;
  overflow: auto;
  padding-bottom: 16px;
  scrollbar-width: thin;
  scrollbar-color: rgba(127, 165, 138, 0.34) transparent;
}

.nav-groups::-webkit-scrollbar {
  width: 6px;
}

.nav-groups::-webkit-scrollbar-thumb {
  border-radius: 999px;
  background: rgba(127, 165, 138, 0.34);
}

.nav-group p {
  margin: 0 0 8px 12px;
  color: #95a99f;
  font-size: 12px;
}

.nav-item {
  display: flex;
  align-items: center;
  width: 100%;
  gap: 12px;
  margin-bottom: 6px;
  padding: 12px 14px;
  border: 0;
  border-radius: 18px;
  background: transparent;
  color: #657b70;
  text-align: left;
}

.nav-item span {
  display: grid;
  place-items: center;
  width: 26px;
  height: 26px;
  border-radius: 10px;
  background: rgba(127, 165, 138, 0.13);
  color: #6f997b;
}

.nav-item.active,
.nav-item:hover {
  background: rgba(127, 165, 138, 0.16);
  color: #243a31;
}

.user-card {
  margin-top: auto;
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 14px;
  border: 1px solid rgba(255, 255, 255, 0.75);
  border-radius: 20px;
  background: rgba(255, 255, 255, 0.64);
}

.avatar {
  display: grid;
  place-items: center;
  width: 42px;
  height: 42px;
  border-radius: 50%;
  background: #7fa58a;
  color: white;
  font-weight: 700;
}

.avatar.big {
  width: 86px;
  height: 86px;
  font-size: 32px;
}

.user-card strong,
.user-card small {
  display: block;
}

.user-card small {
  margin-top: 3px;
  color: #789086;
}

.content {
  min-width: 0;
  padding: 36px clamp(20px, 4vw, 58px);
}

.topbar,
.top-actions,
.panel-head,
.firmware-panel,
.account-card {
  display: flex;
  align-items: center;
}

.topbar {
  justify-content: space-between;
  gap: 24px;
  margin-bottom: 26px;
}

.topbar h1 {
  margin: 4px 0;
  font-size: clamp(28px, 4vw, 42px);
}

.eyebrow {
  margin: 0;
  text-transform: uppercase;
  letter-spacing: 0.12em;
  font-size: 12px;
  font-weight: 700;
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
  padding: 10px 16px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.62);
}

.search span {
  color: #7e9388;
  font-size: 12px;
  white-space: nowrap;
}

.search input {
  border: 0;
  background: transparent;
}

.ghost-button {
  padding: 11px 16px;
  background: rgba(255, 255, 255, 0.68);
  color: #385246;
}

.metrics-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 16px;
  margin-bottom: 22px;
}

.metric-card,
.panel {
  position: relative;
  overflow: hidden;
  border: 1px solid rgba(255, 255, 255, 0.72);
  background: rgba(255, 255, 255, 0.58);
  box-shadow: 0 20px 60px rgba(75, 112, 92, 0.1);
  backdrop-filter: blur(18px);
}

.metric-card {
  min-height: 138px;
  padding: 24px;
  border-radius: 28px;
}

.metric-card::after {
  content: "";
  position: absolute;
  top: -40px;
  right: -34px;
  width: 110px;
  height: 110px;
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.72);
}

.metric-card p,
.metric-card strong,
.metric-card span {
  position: relative;
  z-index: 1;
}

.metric-card p {
  margin: 0 0 18px;
  color: #72887d;
}

.metric-card strong {
  display: block;
  color: #6f997b;
  font-size: clamp(28px, 4vw, 42px);
  font-weight: 400;
  line-height: 1;
}

.metric-card.ink strong {
  color: #253f33;
}

.metric-card.orange strong {
  color: #dc8e4f;
}

.metric-card span {
  display: block;
  margin-top: 12px;
  color: #8ba096;
}

.dashboard-grid,
.two-column,
.profile-grid {
  display: grid;
  gap: 20px;
}

.dashboard-grid {
  grid-template-columns: minmax(0, 1.7fr) minmax(300px, 0.9fr);
}

.two-column {
  grid-template-columns: repeat(2, minmax(0, 1fr));
}

.profile-grid {
  grid-template-columns: repeat(4, minmax(0, 1fr));
}

.panel {
  min-width: 0;
  padding: 26px;
  border-radius: 30px;
}

.panel.full {
  grid-column: 1 / -1;
}

.panel-head {
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 22px;
}

.panel-head h3,
.panel-head p {
  margin: 0;
}

.panel-head h3 {
  font-size: 20px;
}

.panel-head p {
  margin-top: 6px;
  color: #7f958a;
}

.bar-chart {
  display: flex;
  align-items: end;
  justify-content: space-between;
  gap: 12px;
  min-height: 220px;
  padding: 18px 4px 0;
}

.bar-chart.large {
  min-height: 320px;
}

.bar-item {
  display: grid;
  flex: 1;
  justify-items: center;
  gap: 10px;
  min-width: 34px;
}

.bar {
  width: min(36px, 80%);
  border-radius: 999px 999px 10px 10px;
  background: linear-gradient(180deg, #7fa58a, rgba(127, 165, 138, 0.36));
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.55);
}

.bar-item span {
  color: #89a095;
  font-size: 12px;
}

.rank-list,
.pill-list {
  display: grid;
  gap: 12px;
  margin: 0;
  padding: 0;
  list-style: none;
}

.rank-list li,
.pill-row,
.table-row {
  border: 1px solid rgba(255, 255, 255, 0.66);
  background: rgba(255, 255, 255, 0.46);
}

.rank-list li {
  display: grid;
  grid-template-columns: 34px 1fr auto;
  align-items: center;
  gap: 12px;
  padding: 13px;
  border-radius: 18px;
}

.rank-list span {
  display: grid;
  place-items: center;
  width: 28px;
  height: 28px;
  border-radius: 50%;
  background: rgba(127, 165, 138, 0.2);
  color: #6f997b;
}

.rank-list em,
.table-row em {
  color: #d49057;
  font-style: normal;
}

.device-live,
.retention-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 14px;
}

.device-live div,
.retention-grid article {
  padding: 22px;
  border-radius: 24px;
  background: rgba(255, 255, 255, 0.46);
}

.device-live small,
.device-live span,
.retention-grid small,
.retention-grid span {
  display: block;
  color: #7f958a;
}

.device-live strong,
.retention-grid strong {
  display: block;
  margin: 10px 0;
  font-size: 28px;
  font-weight: 500;
}

.heat-list {
  display: grid;
  gap: 14px;
}

.heat-row {
  display: grid;
  grid-template-columns: 86px 1fr 80px;
  align-items: center;
  gap: 14px;
}

.heat-row span,
.heat-row strong {
  font-size: 14px;
}

.heat-row div {
  height: 12px;
  overflow: hidden;
  border-radius: 999px;
  background: rgba(127, 165, 138, 0.13);
}

.heat-row i {
  display: block;
  height: 100%;
  border-radius: inherit;
  background: linear-gradient(90deg, #9ab99f, #d99a62);
}

.pill-row {
  display: flex;
  justify-content: space-between;
  gap: 14px;
  padding: 14px;
  border-radius: 18px;
}

.hero-number {
  min-height: 240px;
}

.hero-number span {
  color: #73877c;
}

.hero-number strong {
  display: block;
  margin: 28px 0 18px;
  color: #6f997b;
  font-size: clamp(54px, 9vw, 96px);
  font-weight: 300;
}

.data-table {
  display: grid;
  gap: 10px;
}

.table-row {
  display: grid;
  grid-template-columns: minmax(80px, 0.22fr) minmax(0, 1fr) auto;
  align-items: center;
  gap: 14px;
  padding: 14px 16px;
  border-radius: 18px;
}

.table-row:not(.device-row) {
  cursor: pointer;
}

.table-row strong {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.segmented {
  display: flex;
  gap: 8px;
  padding: 5px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.56);
}

.segmented button {
  border: 0;
  border-radius: 999px;
  padding: 9px 14px;
  background: transparent;
  color: #657b70;
}

.segmented button.active {
  background: #6f997b;
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

.detail-card span,
.detail-card small {
  display: block;
  color: #6f8278;
  line-height: 1.8;
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
  background: #c7d2cc;
}

.dot.online {
  background: #6f997b;
  box-shadow: 0 0 0 5px rgba(111, 153, 123, 0.14);
}

.row-actions {
  display: flex;
  gap: 8px;
}

.row-actions button {
  border: 0;
  border-radius: 999px;
  padding: 8px 12px;
  background: rgba(127, 165, 138, 0.14);
  color: #466354;
}

.firmware-panel,
.account-card {
  justify-content: space-between;
  gap: 24px;
}

.firmware-panel .primary-button {
  width: auto;
}

.account-card {
  justify-content: flex-start;
}

.account-card h3,
.account-card p {
  margin: 4px 0;
}

@media (max-width: 1180px) {
  .metrics-grid,
  .profile-grid {
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
    min-height: 300px;
    padding: 34px;
  }

  .login-panel {
    margin: 28px auto;
  }

  .sidebar {
    position: relative;
    height: auto;
  }

  .user-card {
    position: static;
    margin-top: 22px;
  }

  .topbar,
  .top-actions,
  .firmware-panel,
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
  .device-live,
  .retention-grid {
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

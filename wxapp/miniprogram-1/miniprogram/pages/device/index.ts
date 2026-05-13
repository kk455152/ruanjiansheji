import {
  getBindProgress,
  getDeviceBattery,
  getDeviceDetail,
  getMusicServices,
  saveAdvancedSettings,
  saveBatteryNotice,
  searchNearbyDevices,
} from '../../services/api'
import { stepStatusLabel, syncStatusLabel } from '../../utils/display'
import { ensureAuthenticated } from '../../utils/auth'

type NearbyCard = {
  deviceId: string
  deviceName: string
  modelName: string
  signalStrength: number
}

type BindStepView = {
  label: string
  name: string
  status: string
}

type ServicePill = {
  serviceName: string
  syncText: string
}

type StoredSettings = {
  bassGain: number
  fullChargeNotice: boolean
  lowBatteryThreshold: number
  nightModeEnd: string
  nightModeStart: string
  volumeLimit: number
}

const SETTINGS_KEY = 'device_settings_v1'
const DEFAULT_DEVICE_NAME = '声盒 Mini'
const DEFAULT_MODEL_NAME = 'SH-Mini A1'
const DEFAULT_NETWORK = 'Home-5G'

function clean(value: string, fallback: string) {
  if (!value) return fallback
  if (value.includes('兜底') || value.includes('Smart Speaker')) return fallback
  return value
}

function readStoredSettings(): Partial<StoredSettings> {
  try {
    const raw = wx.getStorageSync(SETTINGS_KEY) as StoredSettings | ''
    if (raw && typeof raw === 'object') {
      return raw
    }
  } catch (error) {
    // ignore
  }
  return {}
}

function writeStoredSettings(payload: StoredSettings) {
  try {
    wx.setStorageSync(SETTINGS_KEY, payload)
  } catch (error) {
    // ignore
  }
}

Component({
  data: {
    bassGain: 8,
    batteryLevel: 82,
    bindProgress: 0,
    bindSteps: [] as BindStepView[],
    currentNetwork: DEFAULT_NETWORK,
    deviceName: DEFAULT_DEVICE_NAME,
    estimatedPlayTime: '11 小时 20 分',
    fullChargeNotice: true,
    isCharging: false,
    isLoading: false,
    lowBatteryThreshold: 20,
    modelName: DEFAULT_MODEL_NAME,
    nearbyDevices: [] as NearbyCard[],
    nightModeEnd: '07:00',
    nightModeStart: '23:00',
    online: true,
    saving: false,
    services: [] as ServicePill[],
    signalStrength: 0,
    volumeLimit: 80,
  },
  lifetimes: {
    attached() {
      this.syncTabBar()
      this.applyStoredSettings()
      void this.loadPage()
    },
  },
  pageLifetimes: {
    show() {
      if (!ensureAuthenticated('pages/device/index')) return
      this.syncTabBar()
      this.applyStoredSettings()
      void this.loadPage()
    },
  },
  methods: {
    syncTabBar() {
      const tabBar = (this as WechatMiniprogram.Component.TrivialInstance & {
        getTabBar?: () => { setData: (payload: Record<string, unknown>) => void } | null
      }).getTabBar
        ? (this as WechatMiniprogram.Component.TrivialInstance & {
            getTabBar?: () => { setData: (payload: Record<string, unknown>) => void } | null
          }).getTabBar!()
        : null
      if (tabBar) {
        tabBar.setData({ selected: 'pages/device/index' })
      }
    },
    applyStoredSettings() {
      const stored = readStoredSettings()
      if (!stored || !Object.keys(stored).length) return

      const patch: Record<string, unknown> = {}
      if (typeof stored.bassGain === 'number') patch.bassGain = stored.bassGain
      if (typeof stored.fullChargeNotice === 'boolean') patch.fullChargeNotice = stored.fullChargeNotice
      if (typeof stored.lowBatteryThreshold === 'number') patch.lowBatteryThreshold = stored.lowBatteryThreshold
      if (typeof stored.nightModeEnd === 'string') patch.nightModeEnd = stored.nightModeEnd
      if (typeof stored.nightModeStart === 'string') patch.nightModeStart = stored.nightModeStart
      if (typeof stored.volumeLimit === 'number') patch.volumeLimit = stored.volumeLimit

      if (Object.keys(patch).length) {
        this.setData(patch)
      }
    },
    async loadPage() {
      this.setData({ isLoading: true })

      const stored = readStoredSettings()

      try {
        const [detail, batteryInfo, servicesResult, nearbyResult, bindProgress] = await Promise.all([
          getDeviceDetail().catch(() => null),
          getDeviceBattery().catch(() => null),
          getMusicServices().catch(() => ({ services: [] as any[] })),
          searchNearbyDevices().catch(() => ({ list: [] as any[] })),
          getBindProgress().catch(() => ({ progress: 0, steps: [] as any[] })),
        ])

        const patch: Record<string, unknown> = {
          bindProgress: bindProgress.progress || 0,
          bindSteps: (bindProgress.steps || []).map((step: any) => ({
            label: stepStatusLabel(step.status),
            name: step.name,
            status: step.status,
          })),
          nearbyDevices: (nearbyResult.list || []).map((device: any) => ({
            deviceId: device.deviceId,
            deviceName: clean(device.deviceName, '未命名设备'),
            modelName: clean(device.modelName, DEFAULT_MODEL_NAME),
            signalStrength: device.signalStrength,
          })),
          services: (servicesResult.services || [])
            .filter((service: any) => service.bound)
            .map((service: any) => ({
              serviceName: service.serviceName,
              syncText: syncStatusLabel(service.syncStatus),
            })),
        }

        if (detail) {
          patch.currentNetwork = clean(detail.currentNetwork, DEFAULT_NETWORK)
          patch.deviceName = clean(detail.deviceName, DEFAULT_DEVICE_NAME)
          patch.modelName = clean(detail.modelName, DEFAULT_MODEL_NAME)
          patch.online = detail.online
          patch.signalStrength = detail.signalStrength
        }

        if (batteryInfo) {
          patch.batteryLevel = batteryInfo.battery
          patch.estimatedPlayTime = batteryInfo.estimatedPlayTime
          patch.isCharging = batteryInfo.isCharging
        }

        const detailBass = detail && typeof detail.bassGain === 'number' ? detail.bassGain : undefined
        const detailVolume = detail && typeof detail.volumeLimit === 'number' ? detail.volumeLimit : undefined
        const batteryNotice = batteryInfo && typeof batteryInfo.fullChargeNotice === 'boolean'
          ? batteryInfo.fullChargeNotice
          : undefined
        const batteryThreshold = batteryInfo && typeof batteryInfo.lowBatteryThreshold === 'number'
          ? batteryInfo.lowBatteryThreshold
          : undefined

        patch.bassGain = typeof stored.bassGain === 'number'
          ? stored.bassGain
          : (detailBass !== undefined ? detailBass : this.data.bassGain)
        patch.volumeLimit = typeof stored.volumeLimit === 'number'
          ? stored.volumeLimit
          : (detailVolume !== undefined ? detailVolume : this.data.volumeLimit)
        patch.fullChargeNotice = typeof stored.fullChargeNotice === 'boolean'
          ? stored.fullChargeNotice
          : (batteryNotice !== undefined ? batteryNotice : this.data.fullChargeNotice)
        patch.lowBatteryThreshold = typeof stored.lowBatteryThreshold === 'number'
          ? stored.lowBatteryThreshold
          : (batteryThreshold !== undefined ? batteryThreshold : this.data.lowBatteryThreshold)
        if (typeof stored.nightModeStart === 'string') patch.nightModeStart = stored.nightModeStart
        if (typeof stored.nightModeEnd === 'string') patch.nightModeEnd = stored.nightModeEnd

        this.setData(patch)
      } finally {
        this.setData({ isLoading: false })
      }
    },
    changeVolumeLimit(event: WechatMiniprogram.SliderChange) {
      this.setData({ volumeLimit: Number(event.detail.value) })
    },
    changeBassGain(event: WechatMiniprogram.SliderChange) {
      this.setData({ bassGain: Number(event.detail.value) })
    },
    toggleFullChargeNotice(event: WechatMiniprogram.SwitchChange) {
      this.setData({ fullChargeNotice: event.detail.value })
    },
    async saveDeviceSettings() {
      this.setData({ saving: true })

      const snapshot: StoredSettings = {
        bassGain: this.data.bassGain,
        fullChargeNotice: this.data.fullChargeNotice,
        lowBatteryThreshold: this.data.lowBatteryThreshold,
        nightModeEnd: this.data.nightModeEnd,
        nightModeStart: this.data.nightModeStart,
        volumeLimit: this.data.volumeLimit,
      }

      writeStoredSettings(snapshot)

      try {
        await Promise.all([
          saveAdvancedSettings({
            bassGain: snapshot.bassGain,
            nightModeEnd: snapshot.nightModeEnd,
            nightModeStart: snapshot.nightModeStart,
            volumeLimit: snapshot.volumeLimit,
          }).catch(() => null),
          saveBatteryNotice({
            fullChargeNotice: snapshot.fullChargeNotice,
            lowBatteryThreshold: snapshot.lowBatteryThreshold,
          }).catch(() => null),
        ])
        wx.showToast({ title: '设备设置已保存', icon: 'success' })
      } finally {
        this.setData({ saving: false })
      }
    },
    async refreshNearbyDevices() {
      try {
        const nearbyResult = await searchNearbyDevices()
        this.setData({
          nearbyDevices: (nearbyResult.list || []).map((device: any) => ({
            deviceId: device.deviceId,
            deviceName: clean(device.deviceName, '未命名设备'),
            modelName: clean(device.modelName, DEFAULT_MODEL_NAME),
            signalStrength: device.signalStrength,
          })),
        })
        wx.showToast({ title: '已更新附近设备', icon: 'success' })
      } catch (error) {
        wx.showToast({ title: '扫描失败', icon: 'none' })
      }
    },
    copyCurrentNetwork() {
      if (!this.data.currentNetwork || this.data.currentNetwork === '--') {
        wx.showToast({ title: '当前没有可复制的网络名', icon: 'none' })
        return
      }

      wx.setClipboardData({
        data: this.data.currentNetwork,
        success: () => wx.showToast({ title: '网络名称已复制', icon: 'success' }),
      })
    },
    inspectNearbyDevice(event: WechatMiniprogram.TouchEvent) {
      const deviceId = String(event.currentTarget.dataset.deviceId || '')
      const deviceName = String(event.currentTarget.dataset.deviceName || '未知设备')
      const modelName = String(event.currentTarget.dataset.modelName || '--')
      const signalStrength = String(event.currentTarget.dataset.signalStrength || '--')

      wx.showModal({
        title: deviceName,
        content: `型号：${modelName}\n信号：${signalStrength} dBm\n设备 ID：${deviceId}`,
        confirmText: '复制 ID',
        success: (result) => {
          if (result.confirm && deviceId) {
            wx.setClipboardData({
              data: deviceId,
              success: () => wx.showToast({ title: '设备 ID 已复制', icon: 'success' }),
            })
          }
        },
      })
    },
  },
})

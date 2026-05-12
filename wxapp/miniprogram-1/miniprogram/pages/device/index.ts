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

Component({
  data: {
    bassGain: 8,
    batteryLevel: 0,
    bindProgress: 0,
    bindSteps: [] as BindStepView[],
    currentNetwork: '--',
    deviceName: 'Smart Speaker Mini',
    estimatedPlayTime: '--',
    fullChargeNotice: false,
    isCharging: false,
    isLoading: false,
    lowBatteryThreshold: 20,
    modelName: '--',
    nearbyDevices: [] as NearbyCard[],
    nightModeEnd: '07:00',
    nightModeStart: '23:00',
    online: false,
    saving: false,
    services: [] as ServicePill[],
    signalStrength: 0,
    volumeLimit: 80,
  },
  lifetimes: {
    attached() {
      this.syncTabBar()
      void this.loadPage()
    },
  },
  pageLifetimes: {
    show() {
      this.syncTabBar()
      void this.loadPage()
    },
  },
  methods: {
    syncTabBar() {
      const tabBar = (this as WechatMiniprogram.Component.TrivialInstance & {
        getTabBar?: () => { setData: (payload: Record<string, unknown>) => void } | null
      }).getTabBar?.()
      tabBar?.setData({ selected: 'pages/device/index' })
    },
    async loadPage() {
      this.setData({ isLoading: true })

      try {
        const [detail, batteryInfo, servicesResult, nearbyResult, bindProgress] = await Promise.all([
          getDeviceDetail(),
          getDeviceBattery(),
          getMusicServices(),
          searchNearbyDevices(),
          getBindProgress(),
        ])

        this.setData({
          bassGain: detail.bassGain,
          batteryLevel: batteryInfo.battery,
          bindProgress: bindProgress.progress,
          bindSteps: bindProgress.steps.map((step) => ({
            label: stepStatusLabel(step.status),
            name: step.name,
            status: step.status,
          })),
          currentNetwork: detail.currentNetwork,
          deviceName: detail.deviceName,
          estimatedPlayTime: batteryInfo.estimatedPlayTime,
          fullChargeNotice: batteryInfo.fullChargeNotice,
          isCharging: batteryInfo.isCharging,
          lowBatteryThreshold: batteryInfo.lowBatteryThreshold,
          modelName: detail.modelName,
          nearbyDevices: nearbyResult.list.map((device) => ({
            deviceId: device.deviceId,
            deviceName: device.deviceName,
            modelName: device.modelName,
            signalStrength: device.signalStrength,
          })),
          online: detail.online,
          services: servicesResult.services
            .filter((service) => service.bound)
            .map((service) => ({
              serviceName: service.serviceName,
              syncText: syncStatusLabel(service.syncStatus),
            })),
          signalStrength: detail.signalStrength,
          volumeLimit: detail.volumeLimit,
        })
      } catch (error) {
        wx.showToast({ title: '设备页加载失败', icon: 'none' })
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

      try {
        await Promise.all([
          saveAdvancedSettings({
            bassGain: this.data.bassGain,
            nightModeEnd: this.data.nightModeEnd,
            nightModeStart: this.data.nightModeStart,
            volumeLimit: this.data.volumeLimit,
          }),
          saveBatteryNotice({
            fullChargeNotice: this.data.fullChargeNotice,
            lowBatteryThreshold: this.data.lowBatteryThreshold,
          }),
        ])
        wx.showToast({ title: '设备设置已保存', icon: 'success' })
      } catch (error) {
        wx.showToast({ title: '设置保存失败', icon: 'none' })
      } finally {
        this.setData({ saving: false })
        void this.loadPage()
      }
    },
    async refreshNearbyDevices() {
      try {
        const nearbyResult = await searchNearbyDevices()
        this.setData({
          nearbyDevices: nearbyResult.list.map((device) => ({
            deviceId: device.deviceId,
            deviceName: device.deviceName,
            modelName: device.modelName,
            signalStrength: device.signalStrength,
          })),
        })
        wx.showToast({ title: '已更新附近设备', icon: 'success' })
      } catch (error) {
        wx.showToast({ title: '扫描失败', icon: 'none' })
      }
    },
  },
})

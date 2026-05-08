import { reportConnection, reportVolume } from '../../services/secure-request'

Component({
  data: {
    deviceName: '客厅音箱',
    battery: 82,
    volumeLimit: 80,
    isOnline: true,
    saving: false,
  },
  methods: {
    async toggleConnection() {
      const next = !this.data.isOnline
      try {
        await reportConnection(next)
        this.setData({ isOnline: next })
        wx.showToast({ title: next ? '设备已连接' : '设备已断开', icon: 'success' })
      } catch (error) {
        wx.showToast({ title: '状态同步失败', icon: 'error' })
      }
    },
    async changeLimit(event: WechatMiniprogram.SliderChanging) {
      const value = Number(event.detail.value)
      this.setData({ volumeLimit: value })
      try {
        await reportVolume(value)
      } catch (error) {
        wx.showToast({ title: '音量上限同步失败', icon: 'none' })
      }
    },
    inputName(event: WechatMiniprogram.Input) {
      this.setData({ deviceName: event.detail.value })
    },
    saveName() {
      wx.showToast({ title: '设备名已更新', icon: 'success' })
    },
  },
})

import { reportConnection, reportSongInfo, reportVolume } from '../../services/secure-request'

Component({
  data: {
    connected: true,
    battery: 82,
    volume: 63,
    currentSong: '城市夜航',
    source: '网易云音乐',
    syncStatus: '点击操作后连接后端',
    sending: false,
    serviceList: [
      { name: 'QQ 音乐', status: '待授权', path: '/pages/auth/index?service=qq' },
      { name: '网易云音乐', status: '待授权', path: '/pages/auth/index?service=netease' },
    ],
  },
  methods: {
    async pingConnection() {
      try {
        await reportConnection(true)
        this.setData({ syncStatus: '后端已连接' })
      } catch (error) {
        this.setData({ syncStatus: '后端待连接' })
      }
    },
    openAuth(event: WechatMiniprogram.TouchEvent) {
      const path = event.currentTarget.dataset.path as string
      wx.navigateTo({ url: path })
    },
    goFriends() {
      wx.switchTab({ url: '/pages/friends/index' })
    },
    goData() {
      wx.switchTab({ url: '/pages/data/index' })
    },
    goDevice() {
      wx.switchTab({ url: '/pages/device/index' })
    },
    goHistory() {
      wx.navigateTo({ url: '/pages/history/index' })
    },
    async changeVolume(event: WechatMiniprogram.SliderChanging) {
      const value = Number(event.detail.value)
      this.setData({ volume: value })
      try {
        await reportVolume(value)
        wx.showToast({ title: '音量已同步', icon: 'success' })
      } catch (error) {
        wx.showToast({ title: '同步失败', icon: 'error' })
      }
    },
    async playRecommend() {
      this.setData({ sending: true })
      try {
        await reportSongInfo('稻香')
        this.setData({ currentSong: '稻香', source: '网易云音乐', syncStatus: '歌曲已同步' })
        wx.showToast({ title: '已发送到后端', icon: 'success' })
      } catch (error) {
        wx.showToast({ title: '发送失败', icon: 'error' })
      } finally {
        this.setData({ sending: false })
      }
    },
  },
})

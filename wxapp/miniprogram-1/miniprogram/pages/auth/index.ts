import { bindMusicService, getMusicServices, getMusicSyncProgress } from '../../services/api'
import { MUSIC_SERVICE_META, MusicServiceKey } from '../../services/config'
import { syncStatusLabel } from '../../utils/display'

type AuthPageData = {
  accountName: string
  binding: boolean
  currentTask: string
  heroIcon: string
  mode: 'connect' | 'service'
  permissions: string[]
  progress: number
  selectedService: MusicServiceKey
  sectionTitle: string
  service: MusicServiceKey
  serviceButtonText: string
  serviceName: string
  serviceOptions: Array<{ description: string; key: MusicServiceKey; title: string }>
  slogan: string
  syncStatus: string
  syncStatusText: string
}

const initialData: AuthPageData = {
  accountName: '未绑定账号',
  binding: false,
  currentTask: '等待开始同步',
  heroIcon: 'Q',
  mode: 'connect',
  permissions: [...MUSIC_SERVICE_META.netease.permissions],
  progress: 0,
  selectedService: 'qq',
  sectionTitle: '稍后可在这里取消授权',
  service: 'netease',
  serviceButtonText: '同意并授权网易云音乐',
  serviceOptions: [
    { key: 'qq', title: 'QQ 音乐', description: '同步收藏歌单、每日推荐和最近播放。' },
    { key: 'netease', title: '网易云音乐', description: '同步私人 FM、喜欢的歌和日推内容。' },
  ],
  serviceName: MUSIC_SERVICE_META.netease.serviceName,
  slogan: MUSIC_SERVICE_META.netease.slogan,
  syncStatus: 'idle',
  syncStatusText: '待连接',
}

Page({
  data: initialData,
  onLoad(query) {
    const mode = query.service ? 'service' : 'connect'
    const service = query.service === 'qq' ? 'qq' : 'netease'
    const meta = MUSIC_SERVICE_META[service]
    const heroIcon = service === 'qq' ? 'Q' : '云'
    const sectionTitle = service === 'qq' ? '授权内容' : '稍后可在这里取消授权'
    const serviceButtonText = service === 'qq' ? '同意并绑定 QQ 音乐' : '同意并授权网易云音乐'

    this.setData({
      heroIcon,
      mode,
      permissions: [...meta.permissions],
      selectedService: service === 'qq' ? 'qq' : 'netease',
      sectionTitle,
      service,
      serviceButtonText,
      serviceName: meta.serviceName,
      slogan: meta.slogan,
    })
  },
  onShow() {
    if (this.data.mode === 'service') {
      void this.loadStatus()
    }
  },
  async loadStatus() {
    try {
      const [servicesResult, progressResult] = await Promise.all([
        getMusicServices(),
        getMusicSyncProgress(this.data.service),
      ])
      const serviceInfo = servicesResult.services.find((item) => item.service === this.data.service)
      const accountName = serviceInfo ? serviceInfo.accountName : '未绑定账号'

      this.setData({
        accountName,
        currentTask: progressResult.currentTask,
        progress: progressResult.progress,
        syncStatus: progressResult.status,
        syncStatusText: syncStatusLabel(progressResult.status),
      })
    } catch (error) {
      this.setData({
        currentTask: '同步信息暂不可用',
        syncStatus: 'idle',
        syncStatusText: '待连接',
      })
    }
  },
  async bindService() {
    this.setData({ binding: true })

    try {
      await bindMusicService(this.data.service)
      wx.showToast({ title: '授权成功', icon: 'success' })
      await this.loadStatus()
    } catch (error) {
      wx.showToast({ title: '授权失败', icon: 'none' })
    } finally {
      this.setData({ binding: false })
    }
  },
  selectService(event: WechatMiniprogram.TouchEvent) {
    const service = String(event.currentTarget.dataset.service || 'qq') === 'netease' ? 'netease' : 'qq'
    this.setData({ selectedService: service })
  },
  openSelectedService() {
    wx.navigateTo({ url: `/pages/auth/index?service=${this.data.selectedService}` })
  },
  goBack() {
    wx.navigateBack()
  },
})

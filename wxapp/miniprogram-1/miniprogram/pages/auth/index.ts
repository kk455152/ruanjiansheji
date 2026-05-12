import { bindMusicService, getMusicServices, getMusicSyncProgress } from '../../services/api'
import { MUSIC_SERVICE_META, MusicServiceKey } from '../../services/config'
import { syncStatusLabel } from '../../utils/display'

type AuthPageData = {
  accountName: string
  binding: boolean
  currentTask: string
  heroIcon: string
  permissions: string[]
  progress: number
  sectionTitle: string
  service: MusicServiceKey
  serviceButtonText: string
  serviceName: string
  slogan: string
  syncStatus: string
  syncStatusText: string
}

const initialData: AuthPageData = {
  accountName: '未绑定账号',
  binding: false,
  currentTask: '等待开始同步',
  heroIcon: '♥',
  permissions: [...MUSIC_SERVICE_META.netease.permissions],
  progress: 0,
  sectionTitle: '稍后用',
  service: 'netease',
  serviceButtonText: '同意并授权网易云',
  serviceName: MUSIC_SERVICE_META.netease.serviceName,
  slogan: MUSIC_SERVICE_META.netease.slogan,
  syncStatus: 'idle',
  syncStatusText: '待连接',
}

Page({
  data: initialData,
  onLoad(query) {
    const service = query.service === 'qq' ? 'qq' : 'netease'
    const meta = MUSIC_SERVICE_META[service]
    const heroIcon = service === 'qq' ? '♫' : '♥'
    const sectionTitle = service === 'qq' ? '授权内容' : '稍后用'
    const serviceButtonText = service === 'qq' ? '同意并绑定 QQ 音乐' : '同意并授权网易云'

    this.setData({
      heroIcon,
      permissions: [...meta.permissions],
      sectionTitle,
      service,
      serviceButtonText,
      serviceName: meta.serviceName,
      slogan: meta.slogan,
    })
  },
  onShow() {
    void this.loadStatus()
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
  goBack() {
    wx.navigateBack()
  },
})

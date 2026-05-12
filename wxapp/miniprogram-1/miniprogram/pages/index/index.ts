import {
  addNextSong,
  controlPlayer,
  getDeviceDetail,
  getHomeOverview,
  getMusicServices,
  getMusicSyncProgress,
  playSong,
  setPlayerVolume,
} from '../../services/api'
import { FEATURED_TRACK } from '../../services/config'
import { sourceLabel, syncStatusLabel } from '../../utils/display'

type HomeServiceCard = {
  accountName: string
  path: string
  service: string
  serviceName: string
  syncText: string
}

Component({
  data: {
    battery: 0,
    currentArtist: '暂无播放内容',
    currentSong: '点击下方按钮开始播放',
    currentSource: '本地音源',
    deviceModel: '',
    deviceName: 'Smart Speaker Mini',
    historyCount: 0,
    isActionLoading: false,
    isLoading: false,
    isPlaying: false,
    online: false,
    services: [] as HomeServiceCard[],
    syncHint: '连接音乐服务后即可同步你的歌单',
    volume: 50,
  },
  lifetimes: {
    attached() {
      void this.loadPage()
    },
  },
  pageLifetimes: {
    show() {
      void this.loadPage()
    },
  },
  methods: {
    async loadPage() {
      this.setData({ isLoading: true })

      try {
        const [overview, detail, serviceResult] = await Promise.all([
          getHomeOverview(),
          getDeviceDetail(),
          getMusicServices(),
        ])

        const services = serviceResult.services.map((service) => ({
          accountName: service.accountName || '未绑定账号',
          path: `/pages/auth/index?service=${service.service}`,
          service: service.service,
          serviceName: service.serviceName,
          syncText: syncStatusLabel(service.syncStatus),
        }))

        let syncHint = '连接音乐服务后即可同步你的歌单'
        const activeService = serviceResult.services.find((service) => service.syncStatus === 'syncing')

        if (activeService) {
          const syncProgress = await getMusicSyncProgress(activeService.service)
          syncHint = `${activeService.serviceName}：${syncProgress.currentTask}`
        } else if (serviceResult.services.length > 0) {
          syncHint = `${serviceResult.services[0].serviceName} 已完成最近一次同步`
        }

        this.setData({
          battery: overview.device.battery,
          currentArtist: overview.playing.artist,
          currentSong: overview.playing.songName,
          currentSource: sourceLabel(overview.playing.source),
          deviceModel: detail.modelName || overview.device.model,
          deviceName: detail.deviceName || overview.device.name,
          historyCount: overview.historyCount,
          isPlaying: overview.playing.isPlaying,
          online: overview.device.online,
          services,
          syncHint,
          volume: detail.volume,
        })
      } catch (error) {
        wx.showToast({ title: '首页数据加载失败', icon: 'none' })
      } finally {
        this.setData({ isLoading: false })
      }
    },
    async changeVolume(event: WechatMiniprogram.SliderChange) {
      const volume = Number(event.detail.value)
      this.setData({ volume })

      try {
        await setPlayerVolume(volume)
      } catch (error) {
        wx.showToast({ title: '音量同步失败', icon: 'none' })
      }
    },
    async playFeaturedSong() {
      this.setData({ isActionLoading: true })
      const nextAction = this.data.isPlaying ? 'pause' : 'play'

      try {
        await controlPlayer(nextAction)
        this.setData({ isPlaying: nextAction === 'play' })
        wx.showToast({ title: nextAction === 'play' ? '继续播放' : '已暂停', icon: 'none' })
      } catch (error) {
        try {
          await playSong(FEATURED_TRACK)
          this.setData({
            currentArtist: FEATURED_TRACK.artist,
            currentSong: FEATURED_TRACK.songName,
            currentSource: sourceLabel(FEATURED_TRACK.source),
            isPlaying: true,
          })
          wx.showToast({ title: '已切换到推荐歌曲', icon: 'success' })
        } catch (fallbackError) {
          wx.showToast({ title: '播放控制失败', icon: 'none' })
        }
      } finally {
        this.setData({ isActionLoading: false })
        void this.loadPage()
      }
    },
    async addSongToQueue() {
      try {
        await addNextSong({ songId: FEATURED_TRACK.songId, source: FEATURED_TRACK.source })
        wx.showToast({ title: '已加入下一首', icon: 'success' })
      } catch (error) {
        wx.showToast({ title: '歌曲已在下一首队列中', icon: 'none' })
      }
    },
    openAuth(event: WechatMiniprogram.TouchEvent) {
      const path = event.currentTarget.dataset.path as string
      wx.navigateTo({ url: path })
    },
    openFriends() {
      wx.switchTab({ url: '/pages/friends/index' })
    },
    openData() {
      wx.switchTab({ url: '/pages/data/index' })
    },
    openDevice() {
      wx.switchTab({ url: '/pages/device/index' })
    },
    openHistory() {
      wx.navigateTo({ url: '/pages/history/index' })
    },
  },
})

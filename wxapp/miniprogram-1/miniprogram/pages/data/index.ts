import {
  generateListeningCard,
  getListeningSummary,
  getPlayHistory,
  getWeeklyReport,
  playSong,
} from '../../services/api'
import { sourceLabel } from '../../utils/display'

type HistoryPreview = {
  artist: string
  historyId: string
  songId: string
  songName: string
  source: string
  sourceText: string
}

Component({
  data: {
    activeTime: '--',
    cardImageUrl: '',
    compareLastWeek: '',
    favoriteStyle: '--',
    historyPreview: [] as HistoryPreview[],
    isGenerating: false,
    isLoading: false,
    minutes: 0,
    songCount: 0,
    summaryText: '',
    topArtistName: '--',
    topArtistSongCount: 0,
    topPercent: '--',
    topPlaylistName: '--',
    topPlaylistPlayCount: 0,
    weeklyTitle: '',
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
      }).getTabBar
        ? (this as WechatMiniprogram.Component.TrivialInstance & {
            getTabBar?: () => { setData: (payload: Record<string, unknown>) => void } | null
          }).getTabBar!()
        : null
      if (tabBar) {
        tabBar.setData({ selected: 'pages/data/index' })
      }
    },
    async loadPage() {
      this.setData({ isLoading: true })

      try {
        const [summary, weeklyReport, historyResult] = await Promise.all([
          getListeningSummary(),
          getWeeklyReport(),
          getPlayHistory({ pageSize: 3 }),
        ])

        this.setData({
          activeTime: summary.activeTime,
          compareLastWeek: weeklyReport.compareLastWeek,
          favoriteStyle: summary.favoriteStyle,
          historyPreview: historyResult.list.map((item) => ({
            artist: item.artist,
            historyId: item.historyId,
            songId: item.songId,
            songName: item.songName,
            source: item.source,
            sourceText: `${sourceLabel(item.source)} · ${item.artist}`,
          })),
          minutes: summary.minutes,
          songCount: summary.songCount,
          summaryText: weeklyReport.summaryText,
          topArtistName: weeklyReport.topArtist.artistName,
          topArtistSongCount: weeklyReport.topArtist.songCount,
          topPercent: summary.topPercent,
          topPlaylistName: weeklyReport.topPlaylist.playlistName,
          topPlaylistPlayCount: weeklyReport.topPlaylist.playCount,
          weeklyTitle: `${weeklyReport.year} 第 ${weeklyReport.week} 周`,
        })
      } catch (error) {
        wx.showToast({ title: '数据页加载失败', icon: 'none' })
      } finally {
        this.setData({ isLoading: false })
      }
    },
    async generateCard() {
      this.setData({ isGenerating: true })

      try {
        const card = await generateListeningCard()
        this.setData({ cardImageUrl: card.imageUrl })
        wx.showToast({ title: '总结卡片已生成', icon: 'success' })
      } catch (error) {
        wx.showToast({ title: '卡片生成失败', icon: 'none' })
      } finally {
        this.setData({ isGenerating: false })
      }
    },
    async replay(event: WechatMiniprogram.TouchEvent) {
      const songId = String(event.currentTarget.dataset.songId || '')
      const songName = String(event.currentTarget.dataset.songName || '')
      const artist = String(event.currentTarget.dataset.artist || '')
      const source = String(event.currentTarget.dataset.source || '')

      try {
        await playSong({ artist, songId, songName, source })
        wx.showToast({ title: '已发送到音箱播放', icon: 'success' })
      } catch (error) {
        wx.showToast({ title: '重播失败', icon: 'none' })
      }
    },
    openHistory() {
      wx.navigateTo({ url: '/pages/history/index' })
    },
  },
})

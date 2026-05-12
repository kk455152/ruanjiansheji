import { clearOldHistory, getPlayHistory, playSong } from '../../services/api'
import { compactTime, sourceLabel } from '../../utils/display'

type SourceFilter = 'all' | 'netease' | 'qq'

type HistoryRow = {
  artist: string
  historyId: string
  playedAt: string
  playedAtText: string
  songId: string
  songName: string
  source: SourceFilter | string
  sourceText: string
}

Component({
  data: {
    filteredList: [] as HistoryRow[],
    isClearing: false,
    isLoading: false,
    keyword: '',
    selectedSource: 'all' as SourceFilter,
    sourceOptions: [
      { key: 'all', label: '全部' },
      { key: 'netease', label: '网易云' },
      { key: 'qq', label: 'QQ 音乐' },
    ],
    historyList: [] as HistoryRow[],
  },
  lifetimes: {
    attached() {
      void this.loadHistory()
    },
  },
  pageLifetimes: {
    show() {
      void this.loadHistory()
    },
  },
  methods: {
    async loadHistory() {
      this.setData({ isLoading: true })

      try {
        const history = await getPlayHistory({ pageSize: 50 })
        const historyList = history.list.map((item) => ({
          artist: item.artist,
          historyId: item.historyId,
          playedAt: item.playedAt,
          playedAtText: compactTime(item.playedAt),
          songId: item.songId,
          songName: item.songName,
          source: item.source,
          sourceText: `${sourceLabel(item.source)} · ${item.artist}`,
        }))

        this.setData({ historyList }, () => this.applyFilters())
      } catch (error) {
        wx.showToast({ title: '历史记录加载失败', icon: 'none' })
      } finally {
        this.setData({ isLoading: false })
      }
    },
    inputKeyword(event: WechatMiniprogram.Input) {
      this.setData({ keyword: event.detail.value }, () => this.applyFilters())
    },
    selectSource(event: WechatMiniprogram.TouchEvent) {
      const selectedSource = event.currentTarget.dataset.key as SourceFilter
      this.setData({ selectedSource }, () => this.applyFilters())
    },
    applyFilters() {
      const keyword = this.data.keyword.trim().toLowerCase()
      const selectedSource = this.data.selectedSource

      const filteredList = this.data.historyList.filter((item) => {
        const matchesSource = selectedSource === 'all' || item.source === selectedSource
        const haystack = `${item.songName} ${item.artist} ${item.sourceText}`.toLowerCase()
        const matchesKeyword = !keyword || haystack.includes(keyword)
        return matchesSource && matchesKeyword
      })

      this.setData({ filteredList })
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
        wx.showToast({ title: '播放失败', icon: 'none' })
      }
    },
    async clearOldRecords() {
      this.setData({ isClearing: true })

      try {
        await clearOldHistory(30)
        wx.showToast({ title: '已执行清理请求', icon: 'success' })
        void this.loadHistory()
      } catch (error) {
        wx.showToast({ title: '清理失败', icon: 'none' })
      } finally {
        this.setData({ isClearing: false })
      }
    },
  },
})

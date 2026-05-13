import {
  addNextSong,
  controlPlayer,
  getDeviceDetail,
  getHomeOverview,
  getMusicServices,
  getMusicSyncProgress,
  getNeteaseSongPreviewUrl,
  getSongInfo,
  NeteaseSearchSong,
  playSong,
  searchNeteaseSongs,
  setPlayerVolume,
  SongInfoResult,
} from '../../services/api'
import { FEATURED_TRACK } from '../../services/config'
import { sourceLabel, syncStatusLabel } from '../../utils/display'
import { recordListeningSession } from '../../utils/listening-stats'
import { ensureAuthenticated } from '../../utils/auth'

let previewAudio: WechatMiniprogram.InnerAudioContext | null = null
let currentSessionStart = 0
let currentSessionInfo: { artist: string; songName: string; source: string } | null = null

function commitSession() {
  if (!currentSessionStart || !currentSessionInfo) {
    currentSessionStart = 0
    currentSessionInfo = null
    return
  }
  const durationMs = Date.now() - currentSessionStart
  if (durationMs > 3000) {
    recordListeningSession({ ...currentSessionInfo, durationMs })
  }
  currentSessionStart = 0
  currentSessionInfo = null
}

type HomeServiceCard = {
  accountName: string
  path: string
  service: string
  serviceName: string
  syncText: string
}

const DEFAULT_PLAYLIST_KEYWORDS = ['雨后电台', '柳爽 城市夜航', '陈粒', '毛不易 入海', '理想三旬']
const DEFAULT_DEVICE_NAME = '声盒 Mini'
const DEFAULT_DEVICE_MODEL = 'SH-Mini A1'

function mapSongInfoToSearchSong(song: SongInfoResult, keyword: string): NeteaseSearchSong {
  return {
    album: song.album,
    audioUrl: song.audioUrl,
    artistText: song.artistText,
    artists: song.artists,
    coverUrl: song.coverUrl,
    durationMs: song.durationMs,
    durationSeconds: song.durationSeconds,
    keyword,
    name: song.name,
    previewAvailable: Boolean(song.audioUrl),
    songId: song.songId,
    source: song.source,
  }
}

function formatDuration(seconds: number) {
  if (!seconds || seconds <= 0) {
    return '—'
  }
  const mins = Math.floor(seconds / 60)
  const secs = Math.floor(seconds % 60)
  return `${mins}:${secs < 10 ? '0' : ''}${secs}`
}

function sanitizeDeviceName(name: string) {
  if (!name) return DEFAULT_DEVICE_NAME
  if (name.includes('兜底') || name.includes('Smart Speaker')) return DEFAULT_DEVICE_NAME
  return name
}

function sanitizeDeviceModel(model: string) {
  if (!model) return DEFAULT_DEVICE_MODEL
  if (model.includes('兜底')) return DEFAULT_DEVICE_MODEL
  return model
}

Component({
  data: {
    activeSongId: '',
    battery: 82,
    currentAlbum: '',
    currentArtist: '加载中',
    currentCover: '',
    currentDuration: '—',
    currentSong: '正在准备今日推荐',
    currentSource: '网易云音乐',
    deviceModel: DEFAULT_DEVICE_MODEL,
    deviceName: DEFAULT_DEVICE_NAME,
    historyCount: 0,
    isActionLoading: false,
    isLoading: false,
    isPlaying: false,
    isSongSearching: false,
    online: true,
    playlist: [] as NeteaseSearchSong[],
    playlistIndex: 0,
    previewState: 'idle',
    searchKeyword: '',
    searchedSongs: [] as NeteaseSearchSong[],
    services: [] as HomeServiceCard[],
    syncHint: '连接音乐服务后即可同步你的歌单',
    volume: 60,
  },
  lifetimes: {
    attached() {
      this.syncTabBar()
      previewAudio = wx.createInnerAudioContext()
      previewAudio.autoplay = false
      previewAudio.obeyMuteSwitch = false
      previewAudio.onPlay(() => {
        this.setData({ previewState: 'playing', isPlaying: true })
        const song = this.data.playlist[this.data.playlistIndex]
        if (song) {
          currentSessionStart = Date.now()
          currentSessionInfo = {
            artist: song.artistText || '未知艺人',
            songName: song.name || '',
            source: song.source || 'netease',
          }
        }
      })
      previewAudio.onPause(() => {
        this.setData({ previewState: 'paused', isPlaying: false })
        commitSession()
      })
      previewAudio.onStop(() => {
        this.setData({ previewState: 'paused', isPlaying: false })
        commitSession()
      })
      previewAudio.onEnded(() => {
        this.setData({ previewState: 'paused', isPlaying: false })
        commitSession()
        void this.playNextSong()
      })
      previewAudio.onError(() => {
        this.setData({ previewState: 'error', isPlaying: false })
        commitSession()
        const index = this.data.playlistIndex
        const invalidated = this.data.playlist.map((item, idx) =>
          idx === index ? { ...item, audioUrl: '', previewAvailable: false } : item,
        )
        this.setData({ playlist: invalidated })
        void this.playNextSong()
      })
      void this.loadPage()
      void this.loadDefaultPlaylist()
    },
    detached() {
      if (previewAudio) {
        previewAudio.stop()
        previewAudio.destroy()
        previewAudio = null
      }
    },
  },
  pageLifetimes: {
    show() {
      if (!ensureAuthenticated('pages/index/index')) return
      this.syncTabBar()
      void this.loadPage()
      if (!this.data.playlist.length) {
        void this.loadDefaultPlaylist()
      }
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
        tabBar.setData({ selected: 'pages/index/index' })
      }
    },
    async loadDefaultPlaylist() {
      try {
        const keyword = DEFAULT_PLAYLIST_KEYWORDS[
          Math.floor(Math.random() * DEFAULT_PLAYLIST_KEYWORDS.length)
        ]
        const songs = await searchNeteaseSongs(keyword, 10)
        const usable = songs.filter((song) => song.songId && song.name)

        if (!usable.length) {
          return
        }

        this.setData({
          playlist: usable,
          playlistIndex: 0,
        })
        this.applyCurrentSong(0)
      } catch (error) {
        // 静默失败，保持占位
      }
    },
    applyCurrentSong(index: number) {
      const songs = this.data.playlist
      if (!songs.length) return
      const safeIndex = ((index % songs.length) + songs.length) % songs.length
      const song = songs[safeIndex]

      this.setData({
        activeSongId: song.songId,
        currentAlbum: song.album || '',
        currentArtist: song.artistText || '未知艺人',
        currentCover: song.coverUrl || '',
        currentDuration: formatDuration(song.durationSeconds || 0),
        currentSong: song.name,
        currentSource: sourceLabel(song.source || 'netease'),
        playlistIndex: safeIndex,
      })
    },
    async ensurePreviewForIndex(index: number): Promise<string> {
      const songs = this.data.playlist
      if (!songs.length) return ''
      const safeIndex = ((index % songs.length) + songs.length) % songs.length
      const song = songs[safeIndex]
      if (!song) return ''

      if (song.audioUrl) {
        return song.audioUrl
      }

      try {
        const audioUrl = await getNeteaseSongPreviewUrl(song.songId)
        if (audioUrl) {
          const updated = this.data.playlist.map((item, idx) =>
            idx === safeIndex ? { ...item, audioUrl, previewAvailable: true } : item,
          )
          this.setData({ playlist: updated })
        }
        return audioUrl
      } catch (error) {
        return ''
      }
    },
    async resolvePlayableFromIndex(startIndex: number) {
      const songs = this.data.playlist
      if (!songs.length) {
        return { audioUrl: '', resolvedIndex: -1 }
      }

      const total = songs.length
      for (let offset = 0; offset < total; offset += 1) {
        const tryIndex = ((startIndex + offset) % total + total) % total
        const audioUrl = await this.ensurePreviewForIndex(tryIndex)
        if (audioUrl) {
          return { audioUrl, resolvedIndex: tryIndex }
        }
      }
      return { audioUrl: '', resolvedIndex: -1 }
    },
    async ensurePreviewForCurrent() {
      const { audioUrl, resolvedIndex } = await this.resolvePlayableFromIndex(this.data.playlistIndex)

      if (audioUrl && resolvedIndex >= 0 && resolvedIndex !== this.data.playlistIndex) {
        this.applyCurrentSong(resolvedIndex)
      }

      return audioUrl
    },
    async playCurrentFromPlaylist() {
      const audioUrl = await this.ensurePreviewForCurrent()

      if (!audioUrl || !previewAudio) {
        wx.showToast({ title: '暂未找到可试听音源', icon: 'none' })
        this.setData({ previewState: 'error', isPlaying: false })
        return
      }

      previewAudio.stop()
      previewAudio.src = audioUrl
      previewAudio.play()
      this.setData({ previewState: 'playing', isPlaying: true })
    },
    async triggerPlayerAction(action: 'next' | 'previous', successTitle: string) {
      this.setData({ isActionLoading: true })

      try {
        await controlPlayer(action)
      } catch (error) {
        // 音箱端失败也不阻塞本地切歌
      }

      const songs = this.data.playlist
      if (songs.length) {
        const offset = action === 'next' ? 1 : -1
        const startIndex = this.data.playlistIndex + offset
        const { audioUrl, resolvedIndex } = await this.resolvePlayableFromIndex(startIndex)

        if (audioUrl && resolvedIndex >= 0 && previewAudio) {
          this.applyCurrentSong(resolvedIndex)
          previewAudio.stop()
          previewAudio.src = audioUrl
          previewAudio.play()
          this.setData({ previewState: 'playing', isPlaying: true })
          wx.showToast({ title: successTitle, icon: 'none' })
        } else {
          wx.showToast({ title: '当前列表暂无可试听歌曲', icon: 'none' })
          this.setData({ previewState: 'error', isPlaying: false })
        }
      } else {
        if (previewAudio) {
          previewAudio.stop()
        }
        this.setData({ previewState: 'paused', isPlaying: false })
      }

      this.setData({ isActionLoading: false })
    },
    getActiveSong() {
      const searched = this.data.searchedSongs.find((song) => song.songId === this.data.activeSongId)
      if (searched) return searched
      const inPlaylist = this.data.playlist[this.data.playlistIndex]
      return inPlaylist || null
    },
    updateSearchedSongs(nextSongs: NeteaseSearchSong[], activeSongId?: string) {
      this.setData({
        activeSongId: activeSongId || ((nextSongs[0] && nextSongs[0].songId) || ''),
        searchedSongs: nextSongs,
      })
    },
    async ensureSongPreview(song: NeteaseSearchSong) {
      if (song.audioUrl) {
        return song.audioUrl
      }

      try {
        const audioUrl = await getNeteaseSongPreviewUrl(song.songId)
        const nextSongs = this.data.searchedSongs.map((item) =>
          item.songId === song.songId
            ? { ...item, audioUrl, previewAvailable: Boolean(audioUrl) }
            : item,
        )
        this.updateSearchedSongs(nextSongs, song.songId)
        return audioUrl
      } catch (error) {
        return ''
      }
    },
    async playSongPreview(song: NeteaseSearchSong) {
      const audioUrl = await this.ensureSongPreview(song)

      if (!audioUrl || !previewAudio) {
        this.setData({ previewState: 'error' })
        return false
      }

      previewAudio.stop()
      previewAudio.src = audioUrl
      previewAudio.play()
      return true
    },
    async loadPage() {
      this.setData({ isLoading: true })

      try {
        const [overview, detail, serviceResult] = await Promise.all([
          getHomeOverview().catch(() => null),
          getDeviceDetail().catch(() => null),
          getMusicServices().catch(() => ({ services: [] as any[] })),
        ])

        const services = (serviceResult.services || []).map((service: any) => ({
          accountName: (service.accountName && !String(service.accountName).includes('兜底'))
            ? service.accountName
            : '未绑定账号',
          path: `/pages/auth/index?service=${service.service}`,
          service: service.service,
          serviceName: service.serviceName,
          syncText: syncStatusLabel(service.syncStatus),
        }))

        let syncHint = '连接音乐服务后即可同步你的歌单'
        const activeService = (serviceResult.services || []).find(
          (service: any) => service.syncStatus === 'syncing',
        )

        if (activeService) {
          try {
            const syncProgress = await getMusicSyncProgress(activeService.service)
            syncHint = `${activeService.serviceName}：${syncProgress.currentTask}`
          } catch (error) {
            syncHint = `${activeService.serviceName} 正在同步中`
          }
        } else if ((serviceResult.services || []).length > 0) {
          syncHint = `${serviceResult.services[0].serviceName} 已完成最近一次同步`
        }

        this.setData({
          battery: overview ? overview.device.battery : this.data.battery,
          deviceModel: sanitizeDeviceModel(detail ? detail.modelName : (overview ? overview.device.model : '')),
          deviceName: sanitizeDeviceName(detail ? detail.deviceName : (overview ? overview.device.name : '')),
          historyCount: overview ? overview.historyCount : 0,
          online: overview ? overview.device.online : true,
          services,
          syncHint,
          volume: detail ? detail.volume : this.data.volume,
        })
      } catch (error) {
        // 不再弹 toast，避免兜底数据失败干扰用户
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
        // 忽略音量同步失败
      }
    },
    async playFeaturedSong() {
      if (this.data.previewState === 'playing' && previewAudio) {
        previewAudio.pause()
        this.setData({ isPlaying: false, previewState: 'paused' })
        try {
          await controlPlayer('pause')
        } catch (error) {
          // 忽略音箱暂停失败
        }
        return
      }

      if (previewAudio && this.data.previewState === 'paused') {
        try {
          previewAudio.play()
          this.setData({ isPlaying: true, previewState: 'playing' })
          return
        } catch (error) {
          // fall through
        }
      }

      if (this.data.playlist.length) {
        await this.playCurrentFromPlaylist()
        return
      }

      await this.loadDefaultPlaylist()
      if (this.data.playlist.length) {
        await this.playCurrentFromPlaylist()
      }
    },
    async addSongToQueue() {
      const activeSong = this.getActiveSong()
      const queueSong = activeSong || FEATURED_TRACK

      try {
        await addNextSong({ songId: queueSong.songId, source: queueSong.source })
        wx.showToast({ title: '已加入下一首', icon: 'success' })
      } catch (error) {
        wx.showToast({ title: '歌曲已在下一首队列中', icon: 'none' })
      }
    },
    inputSongKeyword(event: WechatMiniprogram.Input) {
      this.setData({ searchKeyword: event.detail.value })
    },
    async searchNeteaseSong() {
      const keyword = this.data.searchKeyword.trim()

      if (!keyword) {
        wx.showToast({ title: '请输入歌曲名或歌手', icon: 'none' })
        return
      }

      this.setData({ isSongSearching: true })

      try {
        let songs = await searchNeteaseSongs(keyword, 6)

        if (!songs.length) {
          const fallbackSong = await getSongInfo({ keyword })
          songs = [mapSongInfoToSearchSong(fallbackSong, keyword)]
        }

        const merged = [...songs, ...this.data.searchedSongs].reduce((acc, song) => {
          if (!acc.some((item) => item.songId === song.songId)) {
            acc.push(song)
          }
          return acc
        }, [] as NeteaseSearchSong[])

        this.updateSearchedSongs(merged, (songs[0] && songs[0].songId) || '')

        const playlist = songs.slice()
        if (playlist.length) {
          this.setData({ playlist, playlistIndex: 0 })
          this.applyCurrentSong(0)
        }

        wx.showToast({ title: `找到 ${songs.length} 首相关歌曲`, icon: 'success' })
      } catch (error) {
        wx.showToast({ title: '搜索失败，请重试', icon: 'none' })
      } finally {
        this.setData({ isSongSearching: false })
      }
    },
    selectSearchSong(event: WechatMiniprogram.TouchEvent) {
      const songId = String(event.currentTarget.dataset.songId || '')
      const song = this.data.searchedSongs.find((item) => item.songId === songId)

      if (!song) {
        return
      }

      const playlistIndex = this.data.playlist.findIndex((item) => item.songId === songId)
      if (playlistIndex >= 0) {
        this.applyCurrentSong(playlistIndex)
      } else {
        const nextPlaylist = [song, ...this.data.playlist]
        this.setData({ playlist: nextPlaylist, playlistIndex: 0 })
        this.applyCurrentSong(0)
      }
    },
    async playSelectedSong(event?: WechatMiniprogram.TouchEvent) {
      const songId = event ? String(event.currentTarget.dataset.songId || '') : this.data.activeSongId
      const song = this.data.searchedSongs.find((item) => item.songId === songId) || this.getActiveSong()

      if (!song) {
        wx.showToast({ title: '请先搜索歌曲', icon: 'none' })
        return
      }

      let playlistIndex = this.data.playlist.findIndex((item) => item.songId === song.songId)
      if (playlistIndex < 0) {
        const nextPlaylist = [song, ...this.data.playlist]
        this.setData({ playlist: nextPlaylist })
        playlistIndex = 0
      }

      this.applyCurrentSong(playlistIndex)
      this.setData({ isActionLoading: true })

      try {
        await playSong({
          artist: song.artistText,
          songId: song.songId,
          songName: song.name,
          source: song.source,
        })
      } catch (error) {
        // 忽略音箱端失败
      }

      await this.playCurrentFromPlaylist()
      this.setData({ isActionLoading: false })
    },
    async queueSelectedSong() {
      const song = this.getActiveSong()

      if (!song) {
        wx.showToast({ title: '请先搜索歌曲', icon: 'none' })
        return
      }

      try {
        await addNextSong({ songId: song.songId, source: song.source })
        wx.showToast({ title: '已加入下一首', icon: 'success' })
      } catch (error) {
        wx.showToast({ title: '歌曲已在队列中', icon: 'none' })
      }
    },
    async switchSearchedSong(event: WechatMiniprogram.TouchEvent) {
      const direction = String(event.currentTarget.dataset.direction || 'next')
      const songs = this.data.searchedSongs

      if (songs.length < 2) {
        wx.showToast({ title: '至少搜索两首歌后才能切换', icon: 'none' })
        return
      }

      const currentIndex = songs.findIndex((song) => song.songId === this.data.activeSongId)
      const safeIndex = currentIndex >= 0 ? currentIndex : 0
      const nextIndex =
        direction === 'prev'
          ? (safeIndex - 1 + songs.length) % songs.length
          : (safeIndex + 1) % songs.length
      const nextSong = songs[nextIndex]

      this.setData({ activeSongId: nextSong.songId })
      await this.playSelectedSong()
    },
    async playPreviousSong() {
      await this.triggerPlayerAction('previous', '已切到上一首')
    },
    async playNextSong() {
      await this.triggerPlayerAction('next', '已切到下一首')
    },
    clearSearchResults() {
      if (previewAudio) {
        previewAudio.stop()
      }
      this.setData({
        activeSongId: this.data.playlist[this.data.playlistIndex]
          ? this.data.playlist[this.data.playlistIndex].songId
          : '',
        previewState: 'idle',
        searchKeyword: '',
        searchedSongs: [],
      })
      wx.showToast({ title: '已清空搜索结果', icon: 'none' })
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

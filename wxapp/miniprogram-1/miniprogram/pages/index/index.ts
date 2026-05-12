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

let previewAudio: WechatMiniprogram.InnerAudioContext | null = null

type HomeServiceCard = {
  accountName: string
  path: string
  service: string
  serviceName: string
  syncText: string
}

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

Component({
  data: {
    activeSongId: '',
    battery: 0,
    currentArtist: '暂无播放内容',
    currentSong: '搜索一首网易云歌曲开始播放',
    currentSource: '本地音源',
    deviceModel: '',
    deviceName: 'Smart Speaker Mini',
    historyCount: 0,
    isActionLoading: false,
    isLoading: false,
    isPlaying: false,
    isSongSearching: false,
    online: false,
    previewState: 'idle',
    searchKeyword: '',
    searchedSongs: [] as NeteaseSearchSong[],
    services: [] as HomeServiceCard[],
    syncHint: '连接音乐服务后即可同步你的歌单',
    volume: 50,
  },
  lifetimes: {
    attached() {
      previewAudio = wx.createInnerAudioContext()
      previewAudio.autoplay = false
      previewAudio.obeyMuteSwitch = false
      previewAudio.onPlay(() => this.setData({ previewState: 'playing' }))
      previewAudio.onPause(() => this.setData({ previewState: 'paused' }))
      previewAudio.onStop(() => this.setData({ previewState: 'paused' }))
      previewAudio.onEnded(() => this.setData({ previewState: 'paused' }))
      previewAudio.onError(() => {
        this.setData({ previewState: 'error' })
        wx.showToast({ title: '当前歌曲暂无可试听音源', icon: 'none' })
      })
      void this.loadPage()
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
      void this.loadPage()
    },
  },
  methods: {
    async triggerPlayerAction(action: 'next' | 'previous', successTitle: string) {
      this.setData({ isActionLoading: true })

      try {
        await controlPlayer(action)
        if (previewAudio) {
          previewAudio.stop()
        }
        this.setData({ previewState: 'paused' })
        wx.showToast({ title: successTitle, icon: 'success' })
      } catch (error) {
        wx.showToast({ title: '播放控制失败', icon: 'none' })
      } finally {
        this.setData({ isActionLoading: false })
        void this.loadPage()
      }
    },
    getActiveSong() {
      return this.data.searchedSongs.find((song) => song.songId === this.data.activeSongId) || null
    },
    updateSearchedSongs(nextSongs: NeteaseSearchSong[], activeSongId?: string) {
      this.setData({
        activeSongId: activeSongId || (nextSongs[0]?.songId || ''),
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
      const activeSong = this.getActiveSong()

      if (activeSong) {
        if (this.data.previewState === 'playing' && previewAudio) {
          previewAudio.pause()
          this.setData({ isPlaying: false })
          try {
            await controlPlayer('pause')
          } catch (error) {
            wx.showToast({ title: '音箱暂停失败', icon: 'none' })
          }
          return
        }

        await this.playSelectedSong()
        return
      }

      this.setData({ isActionLoading: true })
      const nextAction = this.data.isPlaying ? 'pause' : 'play'

      try {
        await controlPlayer(nextAction)
        this.setData({ isPlaying: nextAction === 'play' })
        wx.showToast({ title: nextAction === 'play' ? '继续播放' : '已暂停', icon: 'none' })
      } catch (error) {
        if (nextAction === 'play') {
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
        } else {
          wx.showToast({ title: '播放控制失败', icon: 'none' })
        }
      } finally {
        this.setData({ isActionLoading: false })
        void this.loadPage()
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

        this.updateSearchedSongs(merged, songs[0]?.songId)
        this.setData({
          currentArtist: songs[0].artistText,
          currentSong: songs[0].name,
          currentSource: sourceLabel(songs[0].source),
        })
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

      this.setData({
        activeSongId: songId,
        currentArtist: song.artistText,
        currentSong: song.name,
        currentSource: sourceLabel(song.source),
      })
    },
    async playSelectedSong(event?: WechatMiniprogram.TouchEvent) {
      const songId = event ? String(event.currentTarget.dataset.songId || '') : this.data.activeSongId
      const song = this.data.searchedSongs.find((item) => item.songId === songId) || this.getActiveSong()

      if (!song) {
        wx.showToast({ title: '请先搜索歌曲', icon: 'none' })
        return
      }

      this.setData({
        activeSongId: song.songId,
        currentArtist: song.artistText,
        currentSong: song.name,
        currentSource: sourceLabel(song.source),
        isActionLoading: true,
      })

      try {
        await playSong({
          artist: song.artistText,
          songId: song.songId,
          songName: song.name,
          source: song.source,
        })
        const previewStarted = await this.playSongPreview(song)
        this.setData({
          isPlaying: true,
          previewState: previewStarted ? 'playing' : 'error',
        })
        wx.showToast({ title: previewStarted ? '音箱与手机试听已开始' : '已发送到音箱播放', icon: 'success' })
      } catch (error) {
        wx.showToast({ title: '播放失败，请重试', icon: 'none' })
      } finally {
        this.setData({ isActionLoading: false })
        void this.loadPage()
      }
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

      this.setData({
        activeSongId: nextSong.songId,
        currentArtist: nextSong.artistText,
        currentSong: nextSong.name,
        currentSource: sourceLabel(nextSong.source),
      })
      await this.playSelectedSong()
    },
    async playPreviousSong() {
      await this.triggerPlayerAction('previous', '已切到上一首')
    },
    async playNextSong() {
      await this.triggerPlayerAction('next', '已切到下一首')
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

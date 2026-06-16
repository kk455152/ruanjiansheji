import {
  BACKEND_BASE_URL,
  BACKEND_FALLBACK_BASE_URLS,
  DEFAULT_BIND_TASK_ID,
  DEFAULT_DEVICE_ID,
  MusicServiceKey,
} from './config'

type HttpMethod = 'GET' | 'POST' | 'DELETE'
type QueryValue = string | number | boolean | undefined

interface ApiEnvelope<T> {
  code: number
  message?: string
  data: T
}

export interface HomeOverview {
  device: {
    battery: number
    deviceId: string
    model: string
    name: string
    online: boolean
  }
  historyCount: number
  playing: {
    artist: string
    isPlaying: boolean
    songId: string
    songName: string
    source: string
  }
}

export interface FriendsListening {
  recentFriends: Array<{
    avatar: string
    friendId: string
    isOnline: boolean
    name: string
    nickname: string
    status: string
  }>
  room: {
    memberCount: number
    members: string[]
    roomId: string
    roomName: string
    songName: string
  }
}

export interface ListeningSummary {
  activeTime: string
  favoriteStyle: string
  minutes: number
  songCount: number
  topPercent: string
}

export interface WeeklyReport {
  compareLastWeek: string
  minutes: number
  rank: string
  summaryText: string
  topArtist: {
    artistName: string
    songCount: number
  }
  topPlaylist: {
    playCount: number
    playlistName: string
  }
  week: number
  year: number
}

export interface GeneratedCard {
  cardType: string
  imageUrl: string
  week: number
  year: number
}

export interface PlayHistoryItem {
  artist: string
  coverUrl: string
  historyId: string
  playedAt: string
  songId: string
  songName: string
  source: string
}

export interface SongInfoResult {
  album: string
  audioUrl?: string
  artistText: string
  artists: string[]
  coverUrl: string
  durationMs: number
  durationSeconds: number
  name: string
  songId: string
  source: string
}

export interface NeteaseSearchSong extends SongInfoResult {
  keyword?: string
  previewAvailable?: boolean
}

export interface DeviceDetail {
  bassGain: number
  currentNetwork: string
  deviceId: string
  deviceName: string
  isConnecting: boolean
  modelName: string
  online: boolean
  signalStrength: number
  volume: number
  volumeLimit: number
}

export interface DeviceBattery {
  battery: number
  deviceId: string
  estimatedPlayTime: string
  fullChargeNotice: boolean
  isCharging: boolean
  lowBatteryThreshold: number
  powerSaveEnabled: boolean
}

export interface MusicServiceBinding {
  accountName: string
  bound: boolean
  service: string
  serviceName: string
  syncStatus: string
}

export interface MusicSyncProgress {
  currentTask: string
  progress: number
  service: string
  status: string
  syncedSongs: number
  totalSongs: number
}

export interface NearbyDevice {
  binded: boolean
  deviceId: string
  deviceName: string
  modelName: string
  online: boolean
  signalStrength: number
}

export interface BindProgress {
  progress: number
  steps: Array<{
    name: string
    status: string
  }>
}

export interface ListenRoomState {
  deviceId: string
  memberCount: number
  ownerUserId: number
  role: string
  roomId: string
  roomName: string
  songId: string
  songName: string
  status: string
}

export interface ShareSongCardResult {
  cardId: string
  expireAt: string
  imageUrl: string
  previewUrl: string
  roomId: string
  songId: string
}

export interface PlayerStateResult {
  artist?: string
  currentSong?: {
    artist: string
    songId: string
    songName: string
  }
  deviceId: string
  isMuted?: boolean
  isPlaying?: boolean
  playTime?: number
  songId?: string
  songName?: string
  source?: string
  volume?: number
}

export interface BoundMusicServiceResult {
  accountName: string
  bound: boolean
  service: string
}

function mapSongInfoToSearchSong(song: SongInfoResult, keyword = ''): NeteaseSearchSong {
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

function buildQuery(query?: Record<string, QueryValue>) {
  if (!query) {
    return ''
  }

  const searchParams = Object.entries(query).reduce((params, [key, value]) => {
    if (value === undefined || value === '') {
      return params
    }
    params.push(`${encodeURIComponent(key)}=${encodeURIComponent(String(value))}`)
    return params
  }, [] as string[])

  return searchParams.length > 0 ? `?${searchParams.join('&')}` : ''
}

function isEnvelope<T>(payload: unknown): payload is ApiEnvelope<T> {
  return typeof payload === 'object' && payload !== null && 'code' in payload && 'data' in payload
}

function unwrapPayload<T>(payload: unknown): T {
  if (isEnvelope<T>(payload)) {
    if (payload.code >= 200 && payload.code < 300) {
      return payload.data
    }
    throw new Error(payload.message || '请求失败')
  }

  return payload as T
}

function requestLegacy<T>(
  path: string,
  method: HttpMethod,
  data?: Record<string, unknown>,
  query?: Record<string, QueryValue>,
) {
  const url = `${BACKEND_BASE_URL}${path}${buildQuery(query)}`

  return new Promise<T>((resolve, reject) => {
    wx.request({
      url,
      method,
      data,
      timeout: 15000,
      header: {
        'content-type': 'application/json',
      },
      success: (response) => {
        if (response.statusCode < 200 || response.statusCode >= 300) {
          reject(new Error(`请求失败（${response.statusCode}）`))
          return
        }

        try {
          resolve(unwrapPayload<T>(response.data))
        } catch (error) {
          reject(error)
        }
      },
      fail: () => reject(new Error('网络请求失败，请检查服务器连接')),
    })
  })
}

function getPlatform() {
  try {
    const wxAny = wx as any
    const deviceInfo = wxAny.getDeviceInfo ? wxAny.getDeviceInfo() : null
    if (deviceInfo && deviceInfo.platform) {
      return deviceInfo.platform
    }
  } catch (error) {
    // Ignore and fall back to the legacy runtime path.
  }

  try {
    return wx.getSystemInfoSync().platform
  } catch (error) {
    return ''
  }
}

function shouldRetryOnFallback(error: unknown) {
  const message = error instanceof Error ? error.message : String(error)
  return /timeout|fail|network|certificate|ssl/i.test(message)
}

function getCandidateBaseUrls() {
  if (getPlatform() === 'devtools') {
    return [BACKEND_BASE_URL, ...BACKEND_FALLBACK_BASE_URLS]
  }

  return [BACKEND_BASE_URL]
}

function requestWithUrl<T>(url: string, method: HttpMethod, data?: Record<string, unknown>) {
  return new Promise<T>((resolve, reject) => {
    wx.request({
      url,
      method,
      data,
      timeout: 15000,
      header: {
        'content-type': 'application/json',
      },
      success: (response) => {
        if (response.statusCode < 200 || response.statusCode >= 300) {
          reject(new Error(`request failed (${response.statusCode})`))
          return
        }

        try {
          resolve(unwrapPayload<T>(response.data))
        } catch (error) {
          reject(error)
        }
      },
      fail: (error) => reject(new Error(error.errMsg || 'network request failed')),
    })
  })
}

async function request<T>(
  path: string,
  method: HttpMethod,
  data?: Record<string, unknown>,
  query?: Record<string, QueryValue>,
) {
  if (getCandidateBaseUrls().length === 1) {
    return requestLegacy<T>(path, method, data, query)
  }

  const suffix = `${path}${buildQuery(query)}`
  const baseUrls = getCandidateBaseUrls()
  let lastError: unknown = null

  for (let index = 0; index < baseUrls.length; index += 1) {
    const baseUrl = baseUrls[index]

    try {
      return await requestWithUrl<T>(`${baseUrl}${suffix}`, method, data)
    } catch (error) {
      lastError = error

      if (index === baseUrls.length - 1 || !shouldRetryOnFallback(error)) {
        throw error
      }

      console.warn(`[api] request failed via ${baseUrl}, retrying fallback`, error)
    }
  }

  throw lastError instanceof Error ? lastError : new Error('network request failed')
}

function requestAbsolute<T>(url: string, method: HttpMethod) {
  return new Promise<T>((resolve, reject) => {
    wx.request({
      url,
      method,
      timeout: 15000,
      header: {
        'content-type': 'application/json',
      },
      success: (response) => {
        if (response.statusCode < 200 || response.statusCode >= 300) {
          reject(new Error(`request failed (${response.statusCode})`))
          return
        }

        resolve(response.data as T)
      },
      fail: () => reject(new Error('network request failed')),
    })
  })
}

function normalizeAudioUrl(url?: string | null) {
  if (!url) {
    return ''
  }

  return url.replace(/^http:\/\//, 'https://')
}

export function getHomeOverview() {
  return request<HomeOverview>('/api/home/overview', 'GET')
}

export function getFriendsListening() {
  return request<FriendsListening>('/api/friends/listening', 'GET')
}

export function getListeningSummary() {
  return request<ListeningSummary>('/api/listening-data/summary', 'GET')
}

export function getWeeklyReport() {
  return request<WeeklyReport>('/api/listening-data/weekly-report', 'GET')
}

export function generateListeningCard(style = 'modern') {
  return request<GeneratedCard>('/api/listening-data/generate-card', 'POST', {
    share: true,
    style,
  })
}

export function getPlayHistory(query?: { keyword?: string; page?: number; pageSize?: number; source?: string }) {
  return request<{ list: PlayHistoryItem[] }>('/api/play-history/list', 'GET', undefined, query)
}

export function getSongInfo(query?: { keyword?: string; songId?: string }) {
  return request<SongInfoResult>('/api/song-info', 'GET', undefined, query)
}

export async function searchNeteaseSongs(keyword: string, limit = 6) {
  const searchUrl =
    `https://music.163.com/api/search/get/web?csrf_token=&hlpretag=&hlposttag=&s=${encodeURIComponent(keyword)}` +
    `&type=1&offset=0&total=true&limit=${limit}`

  type SearchResponse = {
    result?: {
      songs?: Array<{
        id: number
        name: string
        dt?: number
        duration?: number
        artists?: Array<{ name: string }>
        ar?: Array<{ name: string }>
        album?: { name?: string; picUrl?: string }
        al?: { name?: string; picUrl?: string }
      }>
    }
  }

  try {
    const payload = await requestAbsolute<SearchResponse>(searchUrl, 'GET')
    const songs = (payload.result && payload.result.songs) || []

    return songs.map((song) => {
      const artists = (song.artists || song.ar || [])
        .map((artist) => artist.name)
        .filter(Boolean)
      const durationMs = Number(song.dt || song.duration || 0)
      const album = song.album || song.al || {}

      return {
        album: album.name || '',
        artistText: artists.join(' / '),
        artists,
        coverUrl: album.picUrl || '',
        durationMs,
        durationSeconds: durationMs > 0 ? Math.floor(durationMs / 1000) : 0,
        keyword,
        name: song.name,
        previewAvailable: false,
        songId: String(song.id),
        source: 'netease',
      } as NeteaseSearchSong
    })
  } catch (error) {
    const fallbackSong = await getSongInfo({ keyword })
    return [mapSongInfoToSearchSong(fallbackSong, keyword)]
  }
}

export async function getNeteaseSongPreviewUrl(songId: string) {
  type PreviewResponse = {
    data?: Array<{
      code?: number
      url?: string | null
    }>
  }

  if (!songId) {
    return ''
  }

  const mirrors = [
    'https://netease-cloud-music-api-one-rouge.vercel.app',
    'https://music-api.focalors.ltd',
    'https://netease-cloud-music-api-binaryify.vercel.app',
  ]
  const levels = ['standard', 'higher', 'exhigh', 'lossless']

  for (const base of mirrors) {
    for (const level of levels) {
      try {
        const url =
          `${base}/song/url/v1?id=${encodeURIComponent(songId)}&level=${encodeURIComponent(level)}`
        const payload = await requestAbsolute<PreviewResponse>(url, 'GET')
        const item = payload.data && payload.data[0]
        const normalized = normalizeAudioUrl(item ? item.url || '' : '')
        if (normalized) {
          return normalized
        }
      } catch (error) {
        // try next mirror / level
      }
    }
  }

  for (const base of mirrors) {
    try {
      const url = `${base}/song/url?id=${encodeURIComponent(songId)}&br=320000`
      const payload = await requestAbsolute<PreviewResponse>(url, 'GET')
      const item = payload.data && payload.data[0]
      const normalized = normalizeAudioUrl(item ? item.url || '' : '')
      if (normalized) {
        return normalized
      }
    } catch (error) {
      // ignore
    }
  }

  return `https://music.163.com/song/media/outer/url?id=${encodeURIComponent(songId)}.mp3`
}

export function clearOldHistory(days = 30) {
  return request<{ cleared?: number }>('/api/play-history/clear-old', 'DELETE', { days })
}

export function getDeviceDetail() {
  return request<DeviceDetail>('/api/device/detail', 'GET')
}

export function getDeviceBattery() {
  return request<DeviceBattery>('/api/device/battery', 'GET')
}

export function saveAdvancedSettings(payload: {
  bassGain: number
  nightModeEnd: string
  nightModeStart: string
  volumeLimit: number
}) {
  return request<{
    autoFirmwareUpdate: boolean
    deviceId: string
    nightEnd: string
    nightModeEnabled: boolean
    nightStart: string
    volumeLimit: number
  }>('/api/device/advanced-settings', 'POST', {
    bassGain: payload.bassGain,
    nightEnd: payload.nightModeEnd,
    nightModeEnabled: true,
    nightStart: payload.nightModeStart,
    volumeLimit: payload.volumeLimit,
  })
}

export function saveBatteryNotice(payload: { fullChargeNotice: boolean; lowBatteryThreshold: number }) {
  return request<{
    deviceId: string
    fullChargeNotice: boolean
    lowBatteryEnabled: boolean
    threshold: number
  }>('/api/device/battery-notice', 'POST', {
    fullChargeNotice: payload.fullChargeNotice,
    lowBatteryEnabled: true,
    threshold: payload.lowBatteryThreshold,
  })
}

export function searchNearbyDevices() {
  return request<{ list: NearbyDevice[]; total: number }>('/api/device/search-nearby', 'GET')
}

export interface BindByCodeResult {
  bound: boolean
  deviceId: string
  deviceName: string
  modelName: string
}

export function bindDeviceByAccessCode(accessCode: string) {
  return request<BindByCodeResult>('/api/device/bind-by-code', 'POST', {
    accessCode,
  })
}

export function getBindProgress(taskId = DEFAULT_BIND_TASK_ID) {
  return request<BindProgress>('/api/device/bind-progress', 'GET', undefined, { taskId })
}

export function getMusicServices() {
  return request<{ services: MusicServiceBinding[] }>('/api/music-service/list', 'GET')
}

export function getMusicSyncProgress(service: string) {
  return request<MusicSyncProgress>('/api/music-service/sync-progress', 'GET', undefined, { service })
}

export function bindMusicService(service: MusicServiceKey) {
  return request<BoundMusicServiceResult>('/api/music-service/bind', 'POST', {
    authCode: 'wx-demo-code',
    scope: ['playlist.read', 'history.read'],
    service,
  })
}

export function createListenRoom(roomName: string) {
  return request<ListenRoomState>('/api/listen-room/create', 'POST', { roomName })
}

export function shareSongCard(payload: {
  artist: string
  songId: string
  songName: string
  source: string
}) {
  return request<ShareSongCardResult>('/api/share/song-card', 'POST', payload)
}

export function playSong(payload: { artist: string; songId: string; songName: string; source: string }) {
  return request<PlayerStateResult>('/api/player/play-song', 'POST', payload)
}

export function addNextSong(payload: { songId: string; source: string }) {
  return request<{ deviceId: string; queuePosition: number; songId: string }>('/api/player/add-next', 'POST', payload)
}

export function setPlayerVolume(volume: number) {
  return request<PlayerStateResult>('/api/player/volume', 'POST', {
    deviceId: DEFAULT_DEVICE_ID,
    volume,
  })
}

export function controlPlayer(action: 'next' | 'pause' | 'play' | 'previous') {
  return request<PlayerStateResult>('/api/player/control', 'POST', {
    action,
    deviceId: DEFAULT_DEVICE_ID,
    source: 'netease',
  })
}

export interface FeedbackResult {
  feedbackId: string
  status: string
  submittedAt: string
}

export function submitFeedback(payload: { contact?: string; content: string; type: string }) {
  return request<FeedbackResult>('/api/feedback/submit', 'POST', {
    contact: payload.contact || '',
    content: payload.content,
    type: payload.type,
  })
}

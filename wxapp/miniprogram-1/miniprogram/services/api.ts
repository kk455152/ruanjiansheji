import {
  BACKEND_BASE_URL,
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

function request<T>(
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
  }>('/api/device/advanced-settings', 'POST', payload)
}

export function saveBatteryNotice(payload: { fullChargeNotice: boolean; lowBatteryThreshold: number }) {
  return request<{
    deviceId: string
    fullChargeNotice: boolean
    lowBatteryEnabled: boolean
    threshold: number
  }>('/api/device/battery-notice', 'POST', payload)
}

export function searchNearbyDevices() {
  return request<{ list: NearbyDevice[]; total: number }>('/api/device/search-nearby', 'GET')
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

export function controlPlayer(action: 'next' | 'pause' | 'play') {
  return request<PlayerStateResult>('/api/player/control', 'POST', {
    action,
    deviceId: DEFAULT_DEVICE_ID,
    source: 'netease',
  })
}

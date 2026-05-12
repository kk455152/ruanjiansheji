export const BACKEND_BASE_URL = 'https://8.137.165.220'

export const DEFAULT_DEVICE_ID = 'dev_001'
export const DEFAULT_USER_ID = 10001
export const DEFAULT_BIND_TASK_ID = 'bind_001'
export const DEFAULT_USER = {
  account: 'wx_speaker_01@smart-speaker.local',
  password: 'wx_speaker_01_pwd_2026',
}

export const FEATURED_TRACK = {
  songId: '1491830535',
  songName: '测试歌曲',
  artist: '茶北Ciper',
  source: 'netease',
} as const

export const MUSIC_SERVICE_META = {
  qq: {
    serviceName: 'QQ 音乐',
    slogan: '同步你在 QQ 音乐里的收藏、歌单和最近播放，直接投到音箱继续听。',
    permissions: ['读取收藏歌单与喜欢歌曲', '同步最近播放历史', '生成听歌总结与分享卡片'],
  },
  netease: {
    serviceName: '网易云音乐',
    slogan: '把你的日推、私人 FM 和收藏歌曲同步到 Smart Speaker Mini。',
    permissions: ['读取每日推荐与私人 FM', '同步播放历史和收藏内容', '生成周报与分享卡片'],
  },
} as const

export type MusicServiceKey = keyof typeof MUSIC_SERVICE_META

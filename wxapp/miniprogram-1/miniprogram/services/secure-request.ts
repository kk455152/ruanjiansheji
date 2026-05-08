import { BACKEND_BASE_URL, DEFAULT_DEVICE_ID, DEFAULT_USER } from './config'

declare const require: (path: string) => any

const CryptoJS = require('../vendor/crypto-js')

const TOKEN_SALT = 'smart_speaker_2026_salt'
const SECRET_KEY = 'speaker_key_2026'

type MetricType =
  | 'volume'
  | 'signal_strength'
  | 'bass_gain'
  | 'is_connected'
  | 'is_connecting'
  | 'like_status'
  | 'song_info'

export interface SpeakerPayload {
  device_id?: string
  type: MetricType
  value: number | boolean | string
  user_account?: string
  user_password?: string
}

interface SecureEnvelope {
  timestamp: number
  token: string
  data: string
  sign: string
}

const ENDPOINT_MAP: Record<MetricType, string> = {
  bass_gain: '/api/bass',
  signal_strength: '/api/signal',
  volume: '/api/volume',
  is_connected: '/api/status/connection',
  is_connecting: '/api/status/connection',
  like_status: '/api/status/like',
  song_info: '/api/song-info',
}

function evpBytesToKey(passphrase: string, salt: any) {
  const pass = CryptoJS.enc.Utf8.parse(passphrase)
  let derived = CryptoJS.lib.WordArray.create()
  let block = CryptoJS.lib.WordArray.create()

  while (derived.sigBytes < 32) {
    block = CryptoJS.MD5(block.clone().concat(pass).concat(salt))
    derived = derived.concat(block)
  }

  return {
    key: CryptoJS.lib.WordArray.create(derived.words.slice(0, 4), 16),
    iv: CryptoJS.lib.WordArray.create(derived.words.slice(4, 8), 16),
  }
}

function encryptData(payload: Record<string, unknown>) {
  const salt = CryptoJS.lib.WordArray.random(8)
  const keyPair = evpBytesToKey(SECRET_KEY, salt)
  const encrypted = CryptoJS.AES.encrypt(JSON.stringify(payload), keyPair.key, {
    iv: keyPair.iv,
    mode: CryptoJS.mode.CBC,
    padding: CryptoJS.pad.Pkcs7,
  })
  return CryptoJS.enc.Utf8.parse('Salted__')
    .concat(salt)
    .concat(encrypted.ciphertext)
    .toString(CryptoJS.enc.Base64)
}

function buildEnvelope(payload: Record<string, unknown>): SecureEnvelope {
  const timestamp = Math.floor(Date.now() / 1000)
  const token = CryptoJS.MD5(`${TOKEN_SALT}${timestamp}`).toString()
  return {
    timestamp,
    token,
    data: encryptData(payload),
    sign: token,
  }
}

export function securePost(payload: SpeakerPayload): Promise<WechatMiniprogram.RequestSuccessCallbackResult> {
  const deviceId = payload.device_id || DEFAULT_DEVICE_ID
  const endpoint = ENDPOINT_MAP[payload.type]
  const businessPayload = {
    ...payload,
    device_id: deviceId,
    user_account: payload.user_account || DEFAULT_USER.account,
    user_password: payload.user_password || DEFAULT_USER.password,
  }
  const envelope = buildEnvelope(businessPayload)

  return new Promise((resolve, reject) => {
    wx.request({
      url: `${BACKEND_BASE_URL}${endpoint}`,
      method: 'POST',
      data: envelope,
      header: {
        Authorization: envelope.token,
        'content-type': 'application/json',
      },
      timeout: 15000,
      success: (res) => {
        if (res.statusCode >= 200 && res.statusCode < 300) {
          resolve(res)
          return
        }
        reject(res)
      },
      fail: reject,
    })
  })
}

export function reportVolume(value: number) {
  return securePost({ type: 'volume', value })
}

export function reportSongInfo(keyword: string) {
  return securePost({ type: 'song_info', value: keyword })
}

export function reportLikeStatus(value: boolean) {
  return securePost({ type: 'like_status', value })
}

export function reportConnection(value: boolean) {
  return securePost({ type: 'is_connected', value })
}

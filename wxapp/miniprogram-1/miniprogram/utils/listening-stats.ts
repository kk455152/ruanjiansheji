const STORAGE_KEY = 'listening_stats_v1'
const WEEK_MS = 7 * 24 * 60 * 60 * 1000

export type ListeningEvent = {
  artist: string
  songName: string
  source: string
  playedAt: number
  durationMs: number
}

export type ArtistAggregate = {
  artist: string
  playCount: number
  totalMs: number
  lastPlayedAt: number
}

export type ListeningStats = {
  events: ListeningEvent[]
  totalMs: number
  lastArtist: string
  lastSong: string
  lastSource: string
  lastPlayedAt: number
}

function readStats(): ListeningStats {
  try {
    const raw = wx.getStorageSync(STORAGE_KEY) as ListeningStats | ''
    if (raw && typeof raw === 'object' && Array.isArray(raw.events)) {
      return raw
    }
  } catch (error) {
    // ignore
  }
  return {
    events: [],
    totalMs: 0,
    lastArtist: '',
    lastSong: '',
    lastSource: '',
    lastPlayedAt: 0,
  }
}

function writeStats(stats: ListeningStats) {
  try {
    const trimmed = {
      ...stats,
      events: stats.events.slice(-240),
    }
    wx.setStorageSync(STORAGE_KEY, trimmed)
  } catch (error) {
    // ignore
  }
}

export function recordListeningSession(session: {
  artist: string
  songName: string
  source: string
  durationMs: number
}) {
  const duration = Math.max(0, Math.round(session.durationMs))
  if (!session.artist && !session.songName) {
    return readStats()
  }

  const stats = readStats()
  const nowTs = Date.now()

  if (duration > 0) {
    stats.events.push({
      artist: session.artist || '未知艺人',
      songName: session.songName || '',
      source: session.source || 'netease',
      playedAt: nowTs,
      durationMs: duration,
    })
    stats.totalMs += duration
  }

  stats.lastArtist = session.artist || stats.lastArtist
  stats.lastSong = session.songName || stats.lastSong
  stats.lastSource = session.source || stats.lastSource
  stats.lastPlayedAt = nowTs

  writeStats(stats)
  return stats
}

export function getWeekAggregates(now = Date.now()) {
  const stats = readStats()
  const cutoff = now - WEEK_MS
  const recent = stats.events.filter((event) => event.playedAt >= cutoff)

  const artistMap = new Map<string, ArtistAggregate>()
  let weekMs = 0

  for (const event of recent) {
    weekMs += event.durationMs
    const key = event.artist || '未知艺人'
    const existing = artistMap.get(key)
    if (existing) {
      existing.playCount += 1
      existing.totalMs += event.durationMs
      existing.lastPlayedAt = Math.max(existing.lastPlayedAt, event.playedAt)
    } else {
      artistMap.set(key, {
        artist: key,
        playCount: 1,
        totalMs: event.durationMs,
        lastPlayedAt: event.playedAt,
      })
    }
  }

  const artists = Array.from(artistMap.values()).sort((a, b) => {
    if (b.playCount !== a.playCount) return b.playCount - a.playCount
    if (b.totalMs !== a.totalMs) return b.totalMs - a.totalMs
    return b.lastPlayedAt - a.lastPlayedAt
  })

  return {
    weekMs,
    weekMinutes: Math.floor(weekMs / 60000),
    playCount: recent.length,
    artists,
    topArtist: artists[0] || null,
    lastArtist: stats.lastArtist,
    lastSong: stats.lastSong,
    lastSource: stats.lastSource,
  }
}

export function clearListeningStats() {
  try {
    wx.removeStorageSync(STORAGE_KEY)
  } catch (error) {
    // ignore
  }
}

import { createListenRoom, shareSongCard } from '../../services/api'
import { FEATURED_TRACK } from '../../services/config'
import { firstChar } from '../../utils/display'
import { getWeekAggregates } from '../../utils/listening-stats'
import { ensureAuthenticated, getLoginSession } from '../../utils/auth'

type FriendRow = {
  friendId: string
  isOnline: boolean
  name: string
  shortName: string
  status: string
  activity: string
  activityIcon: string
  activityTone: string
  avatarTone: string
}

type MemberBadge = {
  name: string
  shortName: string
  avatarTone: string
  badgeIcon: string
  isHost: boolean
  isSelf: boolean
}

type CanvasContext2D = CanvasRenderingContext2D & {
  roundRect?: (x: number, y: number, w: number, h: number, r: number) => void
}

const AVATAR_TONES = [
  'tone-sage',
  'tone-mist',
  'tone-sand',
  'tone-sea',
  'tone-peach',
  'tone-cloud',
]

const FRIEND_NAMES = [
  '阿青', '小北', '之遥', '林野', '晚星', '周岁安',
  '沈屿', '南栖', '顾望', '江岚', '苏晚', '程荇',
  '木槿', '柯岩', '乔一', '白鹭', '岑骁', '叶知秋',
]

const ROOM_NAMES = [
  '雨后电台', '深夜歌单', '晨间微光', '周末漫听',
  '云上午后', '秋日书房', '小宇宙', '慢车时间',
]

const ROOM_SONGS = [
  { songName: '城市夜航', artist: '柳爽', source: 'netease' },
  { songName: '雨巷', artist: '陈粒', source: 'netease' },
  { songName: '晚安 · 悦畔', artist: 'Ye 余宜燊', source: 'qq' },
  { songName: '入海', artist: '毛不易', source: 'netease' },
  { songName: '安河桥', artist: '宋冬野', source: 'qq' },
  { songName: '理想三旬', artist: '陈鸿宇', source: 'netease' },
]

const FRIEND_ACTIVITIES = [
  { text: '正在收听《{song}》', icon: '♪', tone: 'tone-sage', online: true },
  { text: '刚刚加入一起听', icon: '◉', tone: 'tone-sea', online: true },
  { text: '分享了《{song}》', icon: '✦', tone: 'tone-peach', online: true },
  { text: '收藏了 {count} 首新歌', icon: '❤', tone: 'tone-sand', online: true },
  { text: '邀请你一起听歌', icon: '✿', tone: 'tone-sage', online: true },
  { text: '{minutes} 分钟前离线', icon: '◌', tone: 'tone-mist', online: false },
  { text: '昨晚常听《{song}》', icon: '☾', tone: 'tone-cloud', online: false },
  { text: '默默听着白噪音', icon: '✳', tone: 'tone-sea', online: true },
]

const MEMBER_ICONS = ['♪', '✦', '☾', '❤', '✿', '◉']

function pick<T>(list: T[], index: number): T {
  return list[((index % list.length) + list.length) % list.length]
}

function pickRandom<T>(list: T[]): T {
  return list[Math.floor(Math.random() * list.length)]
}

function toneFor(name: string, offset = 0) {
  let sum = offset
  for (let i = 0; i < name.length; i += 1) {
    sum = (sum + name.charCodeAt(i)) % 997
  }
  return pick(AVATAR_TONES, sum)
}

function formatActivity(template: string, song: string) {
  const count = 2 + Math.floor(Math.random() * 9)
  const minutes = 5 + Math.floor(Math.random() * 55)
  return template
    .replace('{song}', song)
    .replace('{count}', String(count))
    .replace('{minutes}', String(minutes))
}

function shuffle<T>(list: T[]): T[] {
  const copy = list.slice()
  for (let i = copy.length - 1; i > 0; i -= 1) {
    const j = Math.floor(Math.random() * (i + 1))
    ;[copy[i], copy[j]] = [copy[j], copy[i]]
  }
  return copy
}

function buildMockData() {
  const room = pickRandom(ROOM_NAMES)
  const song = pickRandom(ROOM_SONGS)
  const pool = shuffle(FRIEND_NAMES)
  const memberCount = 3 + Math.floor(Math.random() * 3)
  const members: MemberBadge[] = pool.slice(0, memberCount).map((name, index) => ({
    name,
    shortName: firstChar(name),
    avatarTone: toneFor(name, index),
    badgeIcon: pick(MEMBER_ICONS, name.charCodeAt(0) + index),
    isHost: false,
    isSelf: false,
  }))

  const friendCount = 6 + Math.floor(Math.random() * 3)
  const recentFriends: FriendRow[] = pool.slice(memberCount, memberCount + friendCount).map((name, index) => {
    const activity = pickRandom(FRIEND_ACTIVITIES)
    const activitySong = pickRandom(ROOM_SONGS).songName
    return {
      friendId: `mock_${index}_${name}`,
      isOnline: activity.online,
      name,
      shortName: firstChar(name),
      status: formatActivity(activity.text, activitySong),
      activity: activity.text,
      activityIcon: activity.icon,
      activityTone: activity.tone,
      avatarTone: toneFor(name, index + 7),
    }
  })

  return {
    members,
    recentFriends,
    room: {
      memberCount,
      roomName: room,
      songName: `${song.songName} · ${song.artist}`,
    },
  }
}

function buildMember(name: string, options: { isHost?: boolean; isSelf?: boolean; offset?: number } = {}): MemberBadge {
  const offset = options.offset !== undefined ? options.offset : 0
  return {
    name,
    shortName: firstChar(name),
    avatarTone: toneFor(name, offset),
    badgeIcon: pick(MEMBER_ICONS, name.charCodeAt(0) + offset),
    isHost: Boolean(options.isHost),
    isSelf: Boolean(options.isSelf),
  }
}

function getSelfDisplayName() {
  const session = getLoginSession()
  const nick = session && session.nickname ? session.nickname.trim() : ''
  return nick || '我'
}

function composeRoomMembers(hostName: string, extraCount: number, selfName: string, excludeNames: string[] = []): MemberBadge[] {
  const hostIsSelf = hostName === selfName
  const members: MemberBadge[] = []
  members.push(buildMember(hostName, { isHost: true, isSelf: hostIsSelf, offset: 0 }))

  if (!hostIsSelf) {
    members.push(buildMember(selfName, { isSelf: true, offset: 1 }))
  }

  const excluded = new Set<string>([hostName, selfName, ...excludeNames])
  const pool = shuffle(FRIEND_NAMES).filter((name) => !excluded.has(name))
  for (let i = 0; i < extraCount && i < pool.length; i += 1) {
    members.push(buildMember(pool[i], { offset: i + 2 }))
  }
  return members
}

function drawRoundedRect(ctx: CanvasContext2D, x: number, y: number, w: number, h: number, r: number) {
  const radius = Math.min(r, w / 2, h / 2)
  ctx.beginPath()
  ctx.moveTo(x + radius, y)
  ctx.lineTo(x + w - radius, y)
  ctx.quadraticCurveTo(x + w, y, x + w, y + radius)
  ctx.lineTo(x + w, y + h - radius)
  ctx.quadraticCurveTo(x + w, y + h, x + w - radius, y + h)
  ctx.lineTo(x + radius, y + h)
  ctx.quadraticCurveTo(x, y + h, x, y + h - radius)
  ctx.lineTo(x, y + radius)
  ctx.quadraticCurveTo(x, y, x + radius, y)
  ctx.closePath()
}

function clipText(ctx: CanvasContext2D, text: string, maxWidth: number) {
  if (!text) return ''
  if (ctx.measureText(text).width <= maxWidth) return text
  const chars = Array.from(text)
  let acc = ''
  for (const ch of chars) {
    const trial = acc + ch
    if (ctx.measureText(trial + '…').width > maxWidth) break
    acc = trial
  }
  return acc + '…'
}

Component({
  data: {
    isCreating: false,
    isLoading: false,
    isSharing: false,
    members: [] as MemberBadge[],
    recentFriends: [] as FriendRow[],
    roomMemberCount: 0,
    roomName: '雨后电台',
    roomSongName: FEATURED_TRACK.songName as string,
    hostName: '',
    hostTagline: '',
    isMyRoom: false,
    sharePreviewUrl: '',
    shareCardPath: '',
    cardGreeting: '',
    cardMinutes: 0,
    cardTopPercent: '',
  },
  lifetimes: {
    attached() {
      this.syncTabBar()
      this.loadPage()
    },
  },
  pageLifetimes: {
    show() {
      if (!ensureAuthenticated('pages/friends/index')) return
      this.syncTabBar()
      this.loadPage()
      this.refreshCardSummary()
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
        tabBar.setData({ selected: 'pages/friends/index' })
      }
    },
    loadPage() {
      this.setData({ isLoading: true })
      const mock = buildMockData()
      const hasActiveRoom = this.data.members && this.data.members.length > 0

      const patch: Record<string, unknown> = {
        recentFriends: mock.recentFriends,
        isLoading: false,
      }

      if (!hasActiveRoom) {
        patch.members = []
        patch.roomMemberCount = 0
        patch.roomName = mock.room.roomName
        patch.roomSongName = mock.room.songName
        patch.hostName = ''
        patch.hostTagline = '还没有房间，点「新建一起听」开场'
        patch.isMyRoom = false
      }

      this.setData(patch)
    },
    async createRoom() {
      this.setData({ isCreating: true })

      const selfName = getSelfDisplayName()
      const roomName = `${selfName}的一起听`
      const songPick = pickRandom(ROOM_SONGS)

      try {
        await createListenRoom(roomName)
      } catch (error) {
        // 后端失败不影响本地房间
      }

      const members = composeRoomMembers(selfName, 0, selfName)
      this.setData({
        members,
        roomMemberCount: members.length,
        roomName,
        roomSongName: `${songPick.songName} · ${songPick.artist}`,
        hostName: selfName,
        hostTagline: `房主：${selfName}（你）`,
        isMyRoom: true,
        isCreating: false,
      })
      wx.showToast({ title: '你已创建一起听房间', icon: 'success' })
    },
    async createRoomWithFriend(event: WechatMiniprogram.TouchEvent) {
      const friendName = String(event.currentTarget.dataset.name || '好友')
      const action = String(event.currentTarget.dataset.action || 'join')

      if (action === 'invite') {
        await this.inviteFriendToRoom(friendName)
        return
      }

      await this.joinFriendRoom(friendName)
    },
    async joinFriendRoom(friendName: string) {
      const selfName = getSelfDisplayName()
      const extraCount = 1 + Math.floor(Math.random() * 3)
      const members = composeRoomMembers(friendName, extraCount, selfName)
      const songPick = pickRandom(ROOM_SONGS)
      const roomName = `${friendName}的一起听`

      this.setData({
        members,
        roomMemberCount: members.length,
        roomName,
        roomSongName: `${songPick.songName} · ${songPick.artist}`,
        hostName: friendName,
        hostTagline: `房主：${friendName} · 你已加入`,
        isMyRoom: false,
      })
      wx.showToast({ title: `已加入 ${friendName} 的房间`, icon: 'success' })
    },
    async inviteFriendToRoom(friendName: string) {
      const selfName = getSelfDisplayName()

      if (!this.data.isMyRoom || !this.data.members.length) {
        const members = composeRoomMembers(selfName, 0, selfName)
        members.push(buildMember(friendName, { offset: members.length + 3 }))
        this.setData({
          members,
          roomMemberCount: members.length,
          roomName: `${selfName}的一起听`,
          hostName: selfName,
          hostTagline: `房主：${selfName}（你）`,
          isMyRoom: true,
        })
      } else if (this.data.members.some((m) => m.name === friendName)) {
        wx.showToast({ title: `${friendName} 已在房间中`, icon: 'none' })
        return
      } else {
        const nextMembers = this.data.members.concat([
          buildMember(friendName, { offset: this.data.members.length + 3 }),
        ])
        this.setData({
          members: nextMembers,
          roomMemberCount: nextMembers.length,
        })
      }

      wx.showToast({ title: `已邀请 ${friendName} 加入`, icon: 'success' })
    },
    leaveRoom() {
      if (!this.data.members.length) {
        wx.showToast({ title: '当前没有在任何房间', icon: 'none' })
        return
      }
      const isMyRoom = this.data.isMyRoom
      wx.showModal({
        title: isMyRoom ? '解散房间' : '退出一起听',
        content: isMyRoom
          ? '解散后当前房间的所有成员都会离开，确定继续吗？'
          : '确定要离开当前的一起听房间吗？',
        confirmText: isMyRoom ? '解散' : '退出',
        confirmColor: '#6b9080',
        success: (res) => {
          if (!res.confirm) return
          this.setData({
            members: [],
            roomMemberCount: 0,
            hostName: '',
            hostTagline: '已离开房间，点「新建一起听」再开一场',
            isMyRoom: false,
          })
          wx.showToast({
            title: isMyRoom ? '房间已解散' : '已退出房间',
            icon: 'success',
          })
        },
      })
    },
    async shareCurrentSong() {
      this.setData({ isSharing: true })

      try {
        const result = await shareSongCard({
          artist: FEATURED_TRACK.artist,
          songId: FEATURED_TRACK.songId,
          songName: this.data.roomSongName || FEATURED_TRACK.songName,
          source: FEATURED_TRACK.source,
        })
        this.setData({ sharePreviewUrl: result.previewUrl })
      } catch (error) {
        this.setData({ sharePreviewUrl: 'https://share.shenghe.mini/p/' + Date.now() })
      }

      try {
        await this.buildShareCardImage()
        wx.showToast({ title: '分享卡片已生成', icon: 'success' })
      } catch (error) {
        wx.showToast({ title: '卡片生成失败', icon: 'none' })
      } finally {
        this.setData({ isSharing: false })
      }
    },
    async loadListeningSummary() {
      const aggregate = getWeekAggregates()
      const totalSeconds = Math.floor(aggregate.weekMs / 1000)
      const minutes = Math.floor(totalSeconds / 60)
      const seconds = totalSeconds % 60
      const topArtist = aggregate.topArtist ? aggregate.topArtist.artist : ''
      const playCount = aggregate.playCount

      return {
        minutes,
        seconds,
        playCount,
        topArtist,
        lastSong: aggregate.lastSong,
        lastArtist: aggregate.lastArtist,
      }
    },
    async refreshCardSummary() {
      const summary = await this.loadListeningSummary()
      const subLine = summary.playCount > 0
        ? `共 ${summary.playCount} 次播放${summary.topArtist ? ' · 常听 ' + summary.topArtist : ''}`
        : '先在首页播一首歌，这里就会更新'
      this.setData({
        cardMinutes: summary.minutes,
        cardTopPercent: subLine,
      })
    },
    getCanvasNode() {
      return new Promise<{ node: any; dpr: number; width: number; height: number }>((resolve, reject) => {
        const query = this.createSelectorQuery()
        query
          .select('#shareCanvas')
          .fields({ node: true, size: true })
          .exec((res) => {
            if (!res || !res[0] || !res[0].node) {
              reject(new Error('canvas 节点未就绪'))
              return
            }
            const info = wx.getSystemInfoSync()
            const dpr = Math.min(info.pixelRatio || 2, 3)
            resolve({
              node: res[0].node,
              dpr,
              width: res[0].width,
              height: res[0].height,
            })
          })
      })
    },
    async buildShareCardImage() {
      const { node, dpr, width, height } = await this.getCanvasNode()
      const summary = await this.loadListeningSummary()
      const minutes = summary.minutes
      const seconds = summary.seconds
      const playCount = summary.playCount
      const topArtist = summary.topArtist
      const lastSong = summary.lastSong
      const lastArtist = summary.lastArtist

      const greetings = ['一起听', '你的音乐片刻', '自然听歌', '本周声音日记']
      const greeting = greetings[Math.floor(Math.random() * greetings.length)]

      const subLine = playCount > 0
        ? `共 ${playCount} 次播放${topArtist ? ' · 常听 ' + topArtist : ''}`
        : '先在首页播一首歌，这里就会更新'

      this.setData({
        cardGreeting: greeting,
        cardMinutes: minutes,
        cardTopPercent: subLine,
      })

      const canvasWidth = width || 300
      const canvasHeight = height || 460
      node.width = canvasWidth * dpr
      node.height = canvasHeight * dpr
      const ctx = node.getContext('2d') as CanvasContext2D
      ctx.scale(dpr, dpr)
      ctx.clearRect(0, 0, canvasWidth, canvasHeight)

      const bg = ctx.createLinearGradient(0, 0, canvasWidth, canvasHeight)
      bg.addColorStop(0, '#EAEFEA')
      bg.addColorStop(0.55, '#D7E4DB')
      bg.addColorStop(1, '#C4D6CA')
      ctx.fillStyle = bg
      ctx.fillRect(0, 0, canvasWidth, canvasHeight)

      ctx.save()
      const glow = ctx.createRadialGradient(
        canvasWidth * 0.15,
        canvasHeight * 0.08,
        10,
        canvasWidth * 0.15,
        canvasHeight * 0.08,
        canvasWidth * 0.7,
      )
      glow.addColorStop(0, 'rgba(255,255,255,0.85)')
      glow.addColorStop(1, 'rgba(255,255,255,0)')
      ctx.fillStyle = glow
      ctx.fillRect(0, 0, canvasWidth, canvasHeight)

      const glowWarm = ctx.createRadialGradient(
        canvasWidth * 0.92,
        canvasHeight * 0.12,
        4,
        canvasWidth * 0.92,
        canvasHeight * 0.12,
        canvasWidth * 0.55,
      )
      glowWarm.addColorStop(0, 'rgba(244,162,97,0.28)')
      glowWarm.addColorStop(1, 'rgba(244,162,97,0)')
      ctx.fillStyle = glowWarm
      ctx.fillRect(0, 0, canvasWidth, canvasHeight)
      ctx.restore()

      ctx.textAlign = 'left'
      ctx.textBaseline = 'top'
      ctx.fillStyle = 'rgba(44,62,53,0.6)'
      ctx.font = '500 13px "PingFang SC","Noto Sans SC",sans-serif'
      ctx.fillText('声盒 Mini · SHARE CARD', 28, 28)

      ctx.fillStyle = '#2C3E35'
      ctx.font = '600 22px "PingFang SC","Noto Sans SC",sans-serif'
      ctx.fillText(greeting, 28, 52)

      const heroX = 24
      const heroY = 96
      const heroW = canvasWidth - 48
      const heroH = 188
      ctx.save()
      ctx.shadowColor = 'rgba(132,169,140,0.25)'
      ctx.shadowBlur = 22
      ctx.shadowOffsetY = 10
      drawRoundedRect(ctx, heroX, heroY, heroW, heroH, 24)
      const heroFill = ctx.createLinearGradient(heroX, heroY, heroX + heroW, heroY + heroH)
      heroFill.addColorStop(0, 'rgba(255,255,255,0.95)')
      heroFill.addColorStop(1, 'rgba(132,169,140,0.2)')
      ctx.fillStyle = heroFill
      ctx.fill()
      ctx.restore()

      const orbCx = heroX + heroW - 56
      const orbCy = heroY + 60
      ctx.save()
      ctx.beginPath()
      ctx.arc(orbCx, orbCy, 32, 0, Math.PI * 2)
      ctx.fillStyle = 'rgba(132,169,140,0.22)'
      ctx.fill()
      ctx.beginPath()
      ctx.arc(orbCx, orbCy, 22, 0, Math.PI * 2)
      const orbFill = ctx.createLinearGradient(orbCx - 22, orbCy - 22, orbCx + 22, orbCy + 22)
      orbFill.addColorStop(0, '#FFFFFF')
      orbFill.addColorStop(1, '#D4E1DA')
      ctx.fillStyle = orbFill
      ctx.fill()
      ctx.fillStyle = '#6B9080'
      ctx.font = '500 22px "PingFang SC","Noto Sans SC",sans-serif'
      ctx.textAlign = 'center'
      ctx.textBaseline = 'middle'
      ctx.fillText('♪', orbCx, orbCy)
      ctx.restore()

      ctx.textAlign = 'left'
      ctx.textBaseline = 'top'
      ctx.fillStyle = '#7B8F84'
      ctx.font = '400 12px "PingFang SC","Noto Sans SC",sans-serif'
      ctx.fillText('本周累计陪伴', heroX + 24, heroY + 24)

      const numberBaseY = heroY + 110
      ctx.fillStyle = '#84A98C'
      ctx.font = '300 56px "PingFang SC","Noto Sans SC",sans-serif'
      ctx.textBaseline = 'alphabetic'
      const minutesText = String(minutes)
      ctx.fillText(minutesText, heroX + 24, numberBaseY)
      const minutesWidth = ctx.measureText(minutesText).width

      ctx.fillStyle = '#2C3E35'
      ctx.font = '500 15px "PingFang SC","Noto Sans SC",sans-serif'
      ctx.fillText('分钟', heroX + 24 + minutesWidth + 8, numberBaseY - 6)

      ctx.fillStyle = '#7B8F84'
      ctx.font = '400 12px "PingFang SC","Noto Sans SC",sans-serif'
      ctx.fillText(`${seconds < 10 ? '0' + seconds : seconds} 秒`, heroX + 24 + minutesWidth + 8, numberBaseY + 14)

      ctx.fillStyle = '#F4A261'
      ctx.font = '500 12px "PingFang SC","Noto Sans SC",sans-serif'
      ctx.textBaseline = 'top'
      const subSafe = clipText(ctx, subLine, heroW - 48)
      ctx.fillText(subSafe, heroX + 24, heroY + heroH - 36)

      const songY = heroY + heroH + 24
      const songH = 116
      ctx.save()
      ctx.shadowColor = 'rgba(44,62,53,0.12)'
      ctx.shadowBlur = 18
      ctx.shadowOffsetY = 8
      drawRoundedRect(ctx, heroX, songY, heroW, songH, 22)
      ctx.fillStyle = 'rgba(255,255,255,0.85)'
      ctx.fill()
      ctx.restore()

      const coverX = heroX + 18
      const coverY = songY + 22
      drawRoundedRect(ctx, coverX, coverY, 72, 72, 18)
      const coverFill = ctx.createLinearGradient(coverX, coverY, coverX + 72, coverY + 72)
      coverFill.addColorStop(0, '#2C3E35')
      coverFill.addColorStop(1, '#435B4D')
      ctx.fillStyle = coverFill
      ctx.fill()
      ctx.fillStyle = 'rgba(255,255,255,0.82)'
      ctx.font = '500 28px "PingFang SC","Noto Sans SC",sans-serif'
      ctx.textAlign = 'center'
      ctx.textBaseline = 'middle'
      ctx.fillText('♪', coverX + 36, coverY + 36)
      ctx.textAlign = 'left'
      ctx.textBaseline = 'top'

      const songTextX = coverX + 90
      const songTextMax = heroX + heroW - songTextX - 18

      ctx.fillStyle = '#7B8F84'
      ctx.font = '400 11px "PingFang SC","Noto Sans SC",sans-serif'
      ctx.fillText('NOW PLAYING', songTextX, songY + 26)

      ctx.fillStyle = '#2C3E35'
      ctx.font = '600 17px "PingFang SC","Noto Sans SC",sans-serif'
      const nowSong = lastSong || this.data.roomSongName || FEATURED_TRACK.songName
      ctx.fillText(clipText(ctx, nowSong, songTextMax), songTextX, songY + 48)

      ctx.fillStyle = '#6B9080'
      ctx.font = '400 12px "PingFang SC","Noto Sans SC",sans-serif'
      const subSong = lastArtist
        ? `${lastArtist} · 网易云音乐`
        : `房间：${this.data.roomName}`
      ctx.fillText(clipText(ctx, subSong, songTextMax), songTextX, songY + 76)

      const footerH = 60
      const footerY = canvasHeight - footerH - 24
      drawRoundedRect(ctx, heroX, footerY, heroW, footerH, 18)
      ctx.fillStyle = 'rgba(255,255,255,0.85)'
      ctx.fill()

      ctx.fillStyle = '#2C3E35'
      ctx.font = '500 13px "PingFang SC","Noto Sans SC",sans-serif'
      ctx.fillText('扫码加入声盒 Mini · 一起听', heroX + 22, footerY + 14)
      ctx.fillStyle = '#7B8F84'
      ctx.font = '400 11px "PingFang SC","Noto Sans SC",sans-serif'
      ctx.fillText('让每一首歌都可以被共享', heroX + 22, footerY + 36)

      ctx.save()
      ctx.beginPath()
      ctx.arc(heroX + heroW - 30, footerY + footerH / 2, 16, 0, Math.PI * 2)
      ctx.fillStyle = '#84A98C'
      ctx.fill()
      ctx.fillStyle = '#FFFFFF'
      ctx.font = '500 14px "PingFang SC","Noto Sans SC",sans-serif'
      ctx.textAlign = 'center'
      ctx.textBaseline = 'middle'
      ctx.fillText('♪', heroX + heroW - 30, footerY + footerH / 2)
      ctx.restore()

      const tempFilePath = await new Promise<string>((resolve, reject) => {
        wx.canvasToTempFilePath({
          canvas: node,
          x: 0,
          y: 0,
          width: canvasWidth,
          height: canvasHeight,
          destWidth: canvasWidth * dpr,
          destHeight: canvasHeight * dpr,
          fileType: 'png',
          quality: 1,
          success: (res) => resolve(res.tempFilePath),
          fail: (err) => reject(err),
        })
      })

      this.setData({ shareCardPath: tempFilePath })
      return tempFilePath
    },
    async copyShareLink() {
      try {
        if (!this.data.shareCardPath) {
          await this.buildShareCardImage()
        }

        const link = this.data.sharePreviewUrl || `shenghe://share/${Date.now()}`
        wx.setClipboardData({
          data: link,
          success: () => {
            wx.showToast({ title: '分享链接已复制', icon: 'success' })
          },
        })
      } catch (error) {
        wx.showToast({ title: '请先生成分享卡片', icon: 'none' })
      }
    },
    async previewShareCard() {
      try {
        wx.showLoading({ title: '正在生成卡片', mask: true })
        const tempFilePath = await this.buildShareCardImage()
        wx.hideLoading()
        wx.previewImage({
          urls: [tempFilePath],
          current: tempFilePath,
        })
      } catch (error) {
        wx.hideLoading()
        wx.showToast({ title: '卡片生成失败', icon: 'none' })
      }
    },
    copyRoomName() {
      wx.setClipboardData({
        data: this.data.roomName,
        success: () => {
          wx.showToast({ title: '房间名已复制', icon: 'success' })
        },
      })
    },
    refreshPage() {
      this.loadPage()
      wx.showToast({ title: '好友动态已刷新', icon: 'none' })
    },
  },
})

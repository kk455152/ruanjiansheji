import {
  generateListeningCard,
  getListeningSummary,
  getPlayHistory,
  getWeeklyReport,
  playSong,
} from '../../services/api'
import { sourceLabel } from '../../utils/display'
import { getWeekAggregates, ArtistAggregate } from '../../utils/listening-stats'

type HistoryPreview = {
  artist: string
  historyId: string
  songId: string
  songName: string
  source: string
  sourceText: string
}

type ArtistRow = {
  artist: string
  playCount: number
  totalMinutes: number
  isTop: boolean
  shortName: string
}

type CanvasContext2D = CanvasRenderingContext2D & {
  roundRect?: (x: number, y: number, w: number, h: number, r: number) => void
}

let tickTimer: ReturnType<typeof setInterval> | null = null

function firstChar(text: string) {
  return text ? Array.from(text)[0] : '·'
}

function drawRoundedRect(
  ctx: CanvasContext2D,
  x: number,
  y: number,
  w: number,
  h: number,
  r: number,
) {
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
    activeTime: '--',
    cardImageUrl: '',
    cardImagePath: '',
    compareLastWeek: '',
    favoriteStyle: '--',
    historyPreview: [] as HistoryPreview[],
    isGenerating: false,
    isLoading: false,
    minutes: 0,
    minutesSeconds: 0,
    weekPlayCount: 0,
    liveNote: '',
    lastSongName: '',
    lastArtist: '',
    lastSource: '',
    artistRows: [] as ArtistRow[],
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
    detached() {
      this.stopLiveTick()
    },
  },
  pageLifetimes: {
    show() {
      this.syncTabBar()
      void this.loadPage()
      this.startLiveTick()
    },
    hide() {
      this.stopLiveTick()
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
    startLiveTick() {
      this.stopLiveTick()
      tickTimer = setInterval(() => {
        this.refreshLocalStats()
      }, 1000)
    },
    stopLiveTick() {
      if (tickTimer) {
        clearInterval(tickTimer)
        tickTimer = null
      }
    },
    refreshLocalStats() {
      const aggregate = getWeekAggregates()
      const topArtists: ArtistAggregate[] = aggregate.artists.slice(0, 4)
      const topCount = topArtists[0] ? topArtists[0].playCount : 0
      const artistRows: ArtistRow[] = topArtists.map((item, index) => ({
        artist: item.artist,
        playCount: item.playCount,
        totalMinutes: Math.max(1, Math.round(item.totalMs / 60000)),
        isTop: index === 0,
        shortName: firstChar(item.artist),
      }))

      const totalSeconds = Math.floor(aggregate.weekMs / 1000)
      const minutesInt = Math.floor(totalSeconds / 60)
      const minutesSecs = totalSeconds % 60

      const topArtistName = aggregate.topArtist ? aggregate.topArtist.artist : this.data.topArtistName
      const topArtistSongCount = aggregate.topArtist ? aggregate.topArtist.playCount : this.data.topArtistSongCount

      const liveNote = aggregate.lastSong
        ? `正在陪伴你 · ${aggregate.lastSong} · ${aggregate.lastArtist || '未知艺人'}`
        : '还没有播放记录，播放几首歌后这里会实时更新。'

      this.setData({
        minutes: minutesInt,
        minutesSeconds: minutesSecs,
        weekPlayCount: aggregate.playCount,
        artistRows,
        lastSongName: aggregate.lastSong || '',
        lastArtist: aggregate.lastArtist || '',
        lastSource: aggregate.lastSource || '',
        liveNote,
        topArtistName: topArtistName || '--',
        topArtistSongCount: topArtistSongCount || 0,
      })

      return { aggregate, topArtistName, topCount }
    },
    async loadPage() {
      this.setData({ isLoading: true })

      try {
        const [summary, weeklyReport, historyResult] = await Promise.all([
          getListeningSummary().catch(() => null),
          getWeeklyReport().catch(() => null),
          getPlayHistory({ pageSize: 3 }).catch(() => ({ list: [] as any[] })),
        ])

        const historyPreview = (historyResult.list || []).map((item: any) => ({
          artist: item.artist,
          historyId: item.historyId,
          songId: item.songId,
          songName: item.songName,
          source: item.source,
          sourceText: `${sourceLabel(item.source)} · ${item.artist}`,
        }))

        this.setData({
          activeTime: summary ? summary.activeTime : '21:00 - 23:00',
          compareLastWeek: weeklyReport ? weeklyReport.compareLastWeek : '',
          favoriteStyle: summary ? summary.favoriteStyle : '民谣 / 轻音乐',
          historyPreview,
          songCount: summary ? summary.songCount : 0,
          summaryText: weeklyReport ? weeklyReport.summaryText : '本周已累计听歌时长来自本地真实播放记录',
          topPercent: summary ? summary.topPercent : '本地实时统计',
          topPlaylistName: weeklyReport ? weeklyReport.topPlaylist.playlistName : '网易云日推',
          topPlaylistPlayCount: weeklyReport ? weeklyReport.topPlaylist.playCount : 0,
          weeklyTitle: weeklyReport ? `${weeklyReport.year} 第 ${weeklyReport.week} 周` : '本周',
        })
      } finally {
        this.setData({ isLoading: false })
        this.refreshLocalStats()
      }
    },
    async generateCard() {
      this.setData({ isGenerating: true })

      try {
        const tempFilePath = await this.buildSummaryCard()
        wx.showToast({ title: '总结卡片已生成', icon: 'success' })
        this.setData({ cardImagePath: tempFilePath })

        try {
          const card = await generateListeningCard()
          if (card && card.imageUrl) {
            this.setData({ cardImageUrl: card.imageUrl })
          }
        } catch (error) {
          // 后端失败不影响本地卡片
        }
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
    async previewGeneratedCard() {
      try {
        wx.showLoading({ title: '正在生成卡片', mask: true })
        const tempFilePath = await this.buildSummaryCard()
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
    async copyCardLink() {
      try {
        if (!this.data.cardImagePath) {
          await this.buildSummaryCard()
        }
        const link = this.data.cardImageUrl || `shenghe://card/${Date.now()}`
        wx.setClipboardData({
          data: link,
          success: () => wx.showToast({ title: '卡片链接已复制', icon: 'success' }),
        })
      } catch (error) {
        wx.showToast({ title: '请先生成总结卡片', icon: 'none' })
      }
    },
    getCanvasNode() {
      return new Promise<{ node: any; dpr: number; width: number; height: number }>((resolve, reject) => {
        const query = this.createSelectorQuery()
        query
          .select('#summaryCanvas')
          .fields({ node: true, size: true })
          .exec((res) => {
            if (!res || !res[0] || !res[0].node) {
              reject(new Error('canvas 未就绪'))
              return
            }
            const info = wx.getSystemInfoSync()
            const dpr = Math.min(info.pixelRatio || 2, 3)
            resolve({
              node: res[0].node,
              dpr,
              width: res[0].width || 300,
              height: res[0].height || 520,
            })
          })
      })
    },
    async buildSummaryCard() {
      const { node, dpr, width, height } = await this.getCanvasNode()
      node.width = width * dpr
      node.height = height * dpr
      const ctx = node.getContext('2d') as CanvasContext2D
      ctx.scale(dpr, dpr)
      ctx.clearRect(0, 0, width, height)

      const padX = 24
      const innerX = padX + 4
      const innerW = width - (padX + 4) * 2

      const bg = ctx.createLinearGradient(0, 0, width, height)
      bg.addColorStop(0, '#EAEFEA')
      bg.addColorStop(0.55, '#D7E4DB')
      bg.addColorStop(1, '#C4D6CA')
      ctx.fillStyle = bg
      ctx.fillRect(0, 0, width, height)

      const glowA = ctx.createRadialGradient(
        width * 0.15,
        height * 0.05,
        8,
        width * 0.15,
        height * 0.05,
        width * 0.75,
      )
      glowA.addColorStop(0, 'rgba(255,255,255,0.85)')
      glowA.addColorStop(1, 'rgba(255,255,255,0)')
      ctx.fillStyle = glowA
      ctx.fillRect(0, 0, width, height)

      const glowB = ctx.createRadialGradient(
        width * 0.92,
        height * 0.1,
        6,
        width * 0.92,
        height * 0.1,
        width * 0.6,
      )
      glowB.addColorStop(0, 'rgba(244,162,97,0.28)')
      glowB.addColorStop(1, 'rgba(244,162,97,0)')
      ctx.fillStyle = glowB
      ctx.fillRect(0, 0, width, height)

      ctx.textAlign = 'left'
      ctx.textBaseline = 'alphabetic'

      let cursorY = 36

      ctx.fillStyle = 'rgba(44,62,53,0.6)'
      ctx.font = '500 12px "PingFang SC","Noto Sans SC",sans-serif'
      ctx.fillText('声盒 Mini · 听歌总结', innerX, cursorY)
      cursorY += 24

      ctx.fillStyle = '#2C3E35'
      ctx.font = '600 22px "PingFang SC","Noto Sans SC",sans-serif'
      ctx.fillText(this.data.weeklyTitle || '本周陪伴', innerX, cursorY)
      cursorY += 22

      const dateStr = new Date().toLocaleDateString('zh-CN', {
        month: 'long',
        day: 'numeric',
        weekday: 'short',
      })
      ctx.fillStyle = '#7B8F84'
      ctx.font = '400 11px "PingFang SC","Noto Sans SC",sans-serif'
      ctx.fillText(dateStr, innerX, cursorY)
      cursorY += 22

      const heroX = padX
      const heroY = cursorY
      const heroW = width - padX * 2
      const heroH = 156
      ctx.save()
      ctx.shadowColor = 'rgba(132,169,140,0.24)'
      ctx.shadowBlur = 22
      ctx.shadowOffsetY = 10
      drawRoundedRect(ctx, heroX, heroY, heroW, heroH, 22)
      const heroFill = ctx.createLinearGradient(heroX, heroY, heroX + heroW, heroY + heroH)
      heroFill.addColorStop(0, 'rgba(255,255,255,0.95)')
      heroFill.addColorStop(1, 'rgba(132,169,140,0.18)')
      ctx.fillStyle = heroFill
      ctx.fill()
      ctx.restore()

      const heroPad = 22
      const heroTextX = heroX + heroPad
      const orbCx = heroX + heroW - heroPad - 30
      const orbCy = heroY + 60
      const heroTextMaxW = orbCx - 32 - heroTextX

      ctx.fillStyle = '#7B8F84'
      ctx.font = '400 12px "PingFang SC","Noto Sans SC",sans-serif'
      ctx.textBaseline = 'alphabetic'
      ctx.fillText('本周累计陪伴', heroTextX, heroY + 32)

      const numBaseline = heroY + 88
      ctx.fillStyle = '#84A98C'
      ctx.font = '300 50px "PingFang SC","Noto Sans SC",sans-serif'
      const minutesText = String(this.data.minutes)
      ctx.fillText(minutesText, heroTextX, numBaseline)
      const minutesW = ctx.measureText(minutesText).width

      ctx.fillStyle = '#2C3E35'
      ctx.font = '500 14px "PingFang SC","Noto Sans SC",sans-serif'
      const minUnit = '分'
      const minUnitX = heroTextX + minutesW + 6
      ctx.fillText(minUnit, minUnitX, numBaseline - 6)
      const minUnitW = ctx.measureText(minUnit).width

      ctx.fillStyle = '#6B9080'
      ctx.font = '400 28px "PingFang SC","Noto Sans SC",sans-serif'
      const secondsText = this.data.minutesSeconds < 10 ? '0' + this.data.minutesSeconds : String(this.data.minutesSeconds)
      const secondsX = minUnitX + minUnitW + 14
      ctx.fillText(secondsText, secondsX, numBaseline)
      const secondsW = ctx.measureText(secondsText).width

      ctx.fillStyle = '#2C3E35'
      ctx.font = '500 14px "PingFang SC","Noto Sans SC",sans-serif'
      ctx.fillText('秒', secondsX + secondsW + 6, numBaseline - 6)

      ctx.fillStyle = '#F4A261'
      ctx.font = '500 12px "PingFang SC","Noto Sans SC",sans-serif'
      const tag = clipText(ctx, `共 ${this.data.weekPlayCount} 次播放 · ${this.data.topPercent}`, heroTextMaxW + 30)
      ctx.fillText(tag, heroTextX, heroY + heroH - 22)

      ctx.save()
      ctx.beginPath()
      ctx.arc(orbCx, orbCy, 30, 0, Math.PI * 2)
      ctx.fillStyle = 'rgba(132,169,140,0.25)'
      ctx.fill()
      ctx.beginPath()
      ctx.arc(orbCx, orbCy, 20, 0, Math.PI * 2)
      const orbFill = ctx.createLinearGradient(orbCx - 20, orbCy - 20, orbCx + 20, orbCy + 20)
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
      ctx.textBaseline = 'alphabetic'

      cursorY = heroY + heroH + 28

      ctx.fillStyle = '#2C3E35'
      ctx.font = '600 15px "PingFang SC","Noto Sans SC",sans-serif'
      ctx.fillText('本周常听艺人', heroX, cursorY)

      ctx.fillStyle = '#7B8F84'
      ctx.font = '400 11px "PingFang SC","Noto Sans SC",sans-serif'
      const subText = '按播放次数'
      const subW = ctx.measureText(subText).width
      ctx.fillText(subText, heroX + heroW - subW, cursorY)

      cursorY += 18

      const rows = this.data.artistRows
      const maxRows = Math.min(rows.length, 3)
      const rowH = 56
      const listStart = cursorY

      if (!maxRows) {
        ctx.fillStyle = '#7B8F84'
        ctx.font = '400 12px "PingFang SC","Noto Sans SC",sans-serif'
        ctx.fillText('播放几首歌后，这里会出现常听艺人榜。', heroX, listStart + 24)
        cursorY = listStart + 48
      } else {
        for (let i = 0; i < maxRows; i += 1) {
          const row = rows[i]
          const top = listStart + i * rowH
          const center = top + 22

          ctx.save()
          ctx.beginPath()
          ctx.arc(heroX + 18, center, 16, 0, Math.PI * 2)
          if (i === 0) {
            const topFill = ctx.createLinearGradient(heroX, top, heroX + 36, top + 36)
            topFill.addColorStop(0, '#84A98C')
            topFill.addColorStop(1, '#6B9080')
            ctx.fillStyle = topFill
          } else {
            ctx.fillStyle = 'rgba(132,169,140,0.2)'
          }
          ctx.fill()
          ctx.fillStyle = i === 0 ? '#FFFFFF' : '#6B9080'
          ctx.font = '600 13px "PingFang SC","Noto Sans SC",sans-serif'
          ctx.textAlign = 'center'
          ctx.textBaseline = 'middle'
          ctx.fillText(String(i + 1), heroX + 18, center)
          ctx.restore()
          ctx.textAlign = 'left'
          ctx.textBaseline = 'alphabetic'

          const textLeft = heroX + 46
          const meta = `${row.playCount} 次 · ${row.totalMinutes} 分`
          ctx.font = '500 11px "PingFang SC","Noto Sans SC",sans-serif'
          const metaW = ctx.measureText(meta).width
          const nameMaxW = heroW - 46 - metaW - 18

          ctx.fillStyle = '#2C3E35'
          ctx.font = '500 14px "PingFang SC","Noto Sans SC",sans-serif'
          const nameText = clipText(ctx, row.artist, nameMaxW)
          ctx.fillText(nameText, textLeft, top + 16)

          ctx.fillStyle = '#6B9080'
          ctx.font = '500 11px "PingFang SC","Noto Sans SC",sans-serif'
          ctx.fillText(meta, heroX + heroW - metaW, top + 16)

          const barX = textLeft
          const barY = top + 28
          const barW = heroW - 46
          const barH = 8
          drawRoundedRect(ctx, barX, barY, barW, barH, barH / 2)
          ctx.fillStyle = 'rgba(255,255,255,0.85)'
          ctx.fill()

          const topCount = rows[0] ? rows[0].playCount : 1
          const ratio = topCount > 0 ? row.playCount / topCount : 0
          const fillW = Math.max(14, barW * ratio)
          drawRoundedRect(ctx, barX, barY, fillW, barH, barH / 2)
          if (i === 0) {
            const fillGrad = ctx.createLinearGradient(barX, barY, barX + fillW, barY)
            fillGrad.addColorStop(0, '#84A98C')
            fillGrad.addColorStop(1, '#6B9080')
            ctx.fillStyle = fillGrad
          } else {
            const fillGrad = ctx.createLinearGradient(barX, barY, barX + fillW, barY)
            fillGrad.addColorStop(0, '#F4A261')
            fillGrad.addColorStop(1, '#E76F51')
            ctx.fillStyle = fillGrad
          }
          ctx.fill()
        }
        cursorY = listStart + maxRows * rowH + 4
      }

      cursorY += 18

      const footerH = 96
      const footerY = cursorY
      ctx.save()
      ctx.shadowColor = 'rgba(44,62,53,0.14)'
      ctx.shadowBlur = 18
      ctx.shadowOffsetY = 8
      drawRoundedRect(ctx, heroX, footerY, heroW, footerH, 22)
      ctx.fillStyle = 'rgba(255,255,255,0.86)'
      ctx.fill()
      ctx.restore()

      const coverSize = 56
      const coverX = heroX + 18
      const coverY = footerY + (footerH - coverSize) / 2
      drawRoundedRect(ctx, coverX, coverY, coverSize, coverSize, 14)
      const coverFill = ctx.createLinearGradient(coverX, coverY, coverX + coverSize, coverY + coverSize)
      coverFill.addColorStop(0, '#2C3E35')
      coverFill.addColorStop(1, '#435B4D')
      ctx.fillStyle = coverFill
      ctx.fill()
      ctx.fillStyle = 'rgba(255,255,255,0.86)'
      ctx.font = '500 24px "PingFang SC","Noto Sans SC",sans-serif'
      ctx.textAlign = 'center'
      ctx.textBaseline = 'middle'
      ctx.fillText('♪', coverX + coverSize / 2, coverY + coverSize / 2)
      ctx.textAlign = 'left'
      ctx.textBaseline = 'alphabetic'

      const textX = coverX + coverSize + 16
      const textMaxW = heroX + heroW - textX - 18

      ctx.fillStyle = '#7B8F84'
      ctx.font = '400 10px "PingFang SC","Noto Sans SC",sans-serif'
      ctx.fillText('NOW PLAYING', textX, footerY + 26)

      ctx.fillStyle = '#2C3E35'
      ctx.font = '600 14px "PingFang SC","Noto Sans SC",sans-serif'
      const lastName = clipText(ctx, this.data.lastSongName || '还没有开始播放', textMaxW)
      ctx.fillText(lastName, textX, footerY + 48)

      ctx.fillStyle = '#6B9080'
      ctx.font = '400 11px "PingFang SC","Noto Sans SC",sans-serif'
      const lastMeta = this.data.lastArtist
        ? `${this.data.lastArtist} · ${sourceLabel(this.data.lastSource || 'netease')}`
        : '播放任意一首歌后这里会同步更新'
      ctx.fillText(clipText(ctx, lastMeta, textMaxW), textX, footerY + 70)

      cursorY = footerY + footerH + 26

      ctx.fillStyle = 'rgba(44,62,53,0.55)'
      ctx.font = '400 10px "PingFang SC","Noto Sans SC",sans-serif'
      ctx.textAlign = 'center'
      const brand = '声盒 Mini · 数据基于本地真实播放'
      ctx.fillText(brand, width / 2, cursorY)
      ctx.textAlign = 'left'

      const finalHeight = Math.min(height, cursorY + 24)

      const tempFilePath = await new Promise<string>((resolve, reject) => {
        wx.canvasToTempFilePath({
          canvas: node,
          x: 0,
          y: 0,
          width,
          height: finalHeight,
          destWidth: width * dpr,
          destHeight: finalHeight * dpr,
          fileType: 'png',
          quality: 1,
          success: (res) => resolve(res.tempFilePath),
          fail: (err) => reject(err),
        })
      })

      this.setData({ cardImagePath: tempFilePath })
      return tempFilePath
    },
    openHistory() {
      wx.navigateTo({ url: '/pages/history/index' })
    },
  },
})

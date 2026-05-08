import { reportSongInfo } from '../../services/secure-request'

Component({
  data: {
    keyword: '',
    histories: [
      { name: '城市夜航', source: '网易云音乐 · 今天 22:14' },
      { name: '雨后电台', source: 'QQ 音乐 · 今天 21:37' },
      { name: '晨光', source: '网易云音乐 · 昨天 19:42' },
    ],
  },
  methods: {
    inputKeyword(event: WechatMiniprogram.Input) {
      this.setData({ keyword: event.detail.value })
    },
    async replay(event: WechatMiniprogram.TouchEvent) {
      const name = event.currentTarget.dataset.name as string
      try {
        await reportSongInfo(name)
        wx.showToast({ title: '已重新播放', icon: 'success' })
      } catch (error) {
        wx.showToast({ title: '播放失败', icon: 'error' })
      }
    },
  },
})

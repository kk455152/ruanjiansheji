Component({
  data: {
    minutes: 428,
    songs: 96,
    top: 'Top 12%',
    histories: [
      { name: '城市夜航', source: '网易云音乐 · 22:14' },
      { name: '雨后电台', source: 'QQ 音乐 · 21:37' },
      { name: '晨光', source: '网易云音乐 · 昨天 19:42' },
    ],
  },
  methods: {
    openHistory() {
      wx.navigateTo({ url: '/pages/history/index' })
    },
    saveSummary() {
      wx.showToast({ title: '总结卡片已生成', icon: 'success' })
    },
  },
})

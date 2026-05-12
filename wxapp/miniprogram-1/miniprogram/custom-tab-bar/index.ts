type TabItem = {
  icon: string
  pagePath: string
  text: string
}

Component({
  data: {
    selected: 'pages/index/index',
    list: [
      { pagePath: 'pages/index/index', text: '首页', icon: '♫' },
      { pagePath: 'pages/friends/index', text: '好友', icon: '◌' },
      { pagePath: 'pages/data/index', text: '数据', icon: '▥' },
      { pagePath: 'pages/device/index', text: '设备', icon: '▣' },
    ] as TabItem[],
  },
  lifetimes: {
    attached() {
      this.syncWithCurrentRoute()
    },
  },
  pageLifetimes: {
    show() {
      this.syncWithCurrentRoute()
    },
  },
  methods: {
    syncWithCurrentRoute() {
      const pages = getCurrentPages()
      const current = pages[pages.length - 1]

      if (current && current.route) {
        this.setData({ selected: current.route })
      }
    },
    switchTab(event: WechatMiniprogram.TouchEvent) {
      const path = String(event.currentTarget.dataset.path || '')

      if (!path || path === this.data.selected) {
        return
      }

      this.setData({ selected: path })
      wx.switchTab({ url: `/${path}` })
    },
  },
})

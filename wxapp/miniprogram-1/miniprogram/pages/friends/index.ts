import { reportLikeStatus, reportSongInfo } from '../../services/secure-request'

Component({
  data: {
    roomName: '雨后电台',
    members: [
      { short: '我', name: '我' },
      { short: '青', name: '阿青' },
      { short: '北', name: '小北' },
    ],
    friends: [
      { short: '青', name: '阿青', desc: '刚分享了《晨光》' },
      { short: '北', name: '小北', desc: '正在听轻音乐歌单' },
    ],
    sharing: false,
  },
  methods: {
    async joinListen() {
      try {
        await reportSongInfo('雨后电台')
        wx.showToast({ title: '已加入一起听', icon: 'success' })
      } catch (error) {
        wx.showToast({ title: '加入失败', icon: 'error' })
      }
    },
    async shareSong() {
      this.setData({ sharing: true })
      try {
        await reportLikeStatus(true)
        wx.showShareMenu({ withShareTicket: true })
        wx.showToast({ title: '分享卡片已生成', icon: 'success' })
      } catch (error) {
        wx.showToast({ title: '分享失败', icon: 'error' })
      } finally {
        this.setData({ sharing: false })
      }
    },
  },
})

import { reportConnection } from '../../services/secure-request'

Page({
  data: {
    service: '网易云音乐',
    slogan: '同步私人 FM、喜欢的音乐和每日推荐到智能音箱。',
    permissions: ['读取收藏歌单与推荐歌曲', '同步播放历史到音箱', '生成个人听歌总结'],
    binding: false,
  },
  onLoad(query: Record<string, string | undefined>) {
    if (query.service === 'qq') {
      this.setData({
        service: 'QQ 音乐',
        slogan: '用于播放会员曲库、同步收藏歌单和最近播放。',
      })
    }
  },
  async bindService() {
    this.setData({ binding: true })
    try {
      await reportConnection(true)
      wx.showToast({ title: '绑定成功', icon: 'success' })
      setTimeout(() => wx.navigateBack(), 700)
    } catch (error) {
      wx.showToast({ title: '绑定失败', icon: 'error' })
    } finally {
      this.setData({ binding: false })
    }
  },
  skip() {
    wx.navigateBack()
  },
})

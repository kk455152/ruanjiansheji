import { setLoginSession, getLoginSession } from '../../utils/auth'

type UserInfoDetail = WechatMiniprogram.GetUserInfoSuccessCallbackResult

function persistSession(userInfo: { nickName?: string; avatarUrl?: string }, code: string) {
  setLoginSession({
    nickname: (userInfo && userInfo.nickName) || '声盒用户',
    avatarUrl: (userInfo && userInfo.avatarUrl) || '',
    loginAt: Date.now(),
    code,
  })
}

function loginCode() {
  return new Promise<string>((resolve) => {
    wx.login({
      success: (res) => resolve(res.code || ''),
      fail: () => resolve(''),
    })
  })
}

Page({
  data: {
    loading: false,
  },
  onLoad() {
    if (getLoginSession()) {
      wx.switchTab({ url: '/pages/index/index' })
    }
  },
  async onGetUserInfo(event: { detail: UserInfoDetail & { errMsg?: string } }) {
    const detail = event && event.detail
    if (!detail || !detail.userInfo) {
      return
    }
    this.setData({ loading: true })
    try {
      const code = await loginCode()
      persistSession(detail.userInfo, code)
      wx.showToast({ title: '登录成功', icon: 'success' })
      setTimeout(() => {
        wx.switchTab({ url: '/pages/index/index' })
      }, 500)
    } finally {
      this.setData({ loading: false })
    }
  },
  async onQuickLogin() {
    if (this.data.loading) return
    this.setData({ loading: true })
    try {
      const code = await loginCode()

      let nickName = ''
      let avatarUrl = ''
      try {
        const profile = await wx.getUserProfile({ desc: '用于展示登录信息' })
        nickName = profile.userInfo.nickName
        avatarUrl = profile.userInfo.avatarUrl
      } catch (error) {
        nickName = '声盒用户'
      }

      persistSession({ nickName, avatarUrl }, code)
      wx.showToast({ title: '登录成功', icon: 'success' })
      setTimeout(() => {
        wx.switchTab({ url: '/pages/index/index' })
      }, 500)
    } finally {
      this.setData({ loading: false })
    }
  },
})

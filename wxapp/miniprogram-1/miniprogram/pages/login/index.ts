import { setLoginSession, getLoginSession } from '../../utils/auth'

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
    confirmed: false,
    nickName: '',
    avatarUrl: '',
    manualMode: false,
    manualAvatar: '',
    manualNick: '',
  },
  onLoad() {
    if (getLoginSession()) {
      wx.switchTab({ url: '/pages/index/index' })
    }
  },
  async onQuickLogin() {
    if (this.data.loading) return
    this.setData({ loading: true })

    const canUseProfile = typeof wx.getUserProfile === 'function'

    if (canUseProfile) {
      try {
        const profile = await wx.getUserProfile({
          desc: '用于在声盒 Mini 中展示你的头像和昵称',
          lang: 'zh_CN',
        })
        await this.finalizeLogin(profile.userInfo.nickName, profile.userInfo.avatarUrl)
        return
      } catch (error) {
        const errMsg = error && (error as any).errMsg ? String((error as any).errMsg) : ''
        if (errMsg.indexOf('cancel') >= 0 || errMsg.indexOf('deny') >= 0) {
          this.setData({ loading: false })
          wx.showToast({ title: '已取消登录', icon: 'none' })
          return
        }
        // getUserProfile 在新基础库被禁用，降级到 chooseAvatar + nickname
      }
    }

    this.setData({ manualMode: true, loading: false })
  },
  onChooseAvatar(event: WechatMiniprogram.CustomEvent<{ avatarUrl: string }>) {
    const url = event && event.detail && event.detail.avatarUrl
    if (url) {
      this.setData({ manualAvatar: url })
    }
  },
  onNickInput(event: WechatMiniprogram.Input) {
    this.setData({ manualNick: event.detail.value })
  },
  async confirmManualLogin() {
    const nick = (this.data.manualNick || '').trim() || '声盒用户'
    const avatar = this.data.manualAvatar || ''
    this.setData({ loading: true, manualMode: false })
    await this.finalizeLogin(nick, avatar)
  },
  closeManual() {
    this.setData({ manualMode: false, loading: false })
  },
  async finalizeLogin(nickName: string, avatarUrl: string) {
    const code = await loginCode()
    const finalNick = (nickName || '').trim() || '声盒用户'

    setLoginSession({
      nickname: finalNick,
      avatarUrl: avatarUrl || '',
      loginAt: Date.now(),
      code,
    })

    this.setData({
      confirmed: true,
      loading: false,
      nickName: finalNick,
      avatarUrl: avatarUrl || '',
    })

    wx.showToast({ title: '登录成功', icon: 'success' })
    setTimeout(() => {
      wx.switchTab({ url: '/pages/index/index' })
    }, 900)
  },
})

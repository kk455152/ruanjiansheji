// app.ts
import { isLoggedIn } from './utils/auth'

App<IAppOption>({
  globalData: {},
  onLaunch() {
    const logs = wx.getStorageSync('logs') || []
    logs.unshift(Date.now())
    wx.setStorageSync('logs', logs)

    wx.login({
      success: res => {
        console.log(res.code)
      },
    })

    if (!isLoggedIn()) {
      // 未登录时强制进入登录页
      wx.reLaunch({ url: '/pages/login/index' })
    }
  },
})

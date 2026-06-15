import { submitFeedback } from '../../services/api'
import { ensureAuthenticated } from '../../utils/auth'

type FeedbackType = 'suggestion' | 'bug' | 'experience' | 'other'

Component({
  data: {
    contact: '',
    content: '',
    isSubmitting: false,
    selectedType: 'suggestion' as FeedbackType,
    typeOptions: [
      { key: 'suggestion', label: '功能建议' },
      { key: 'bug', label: '问题反馈' },
      { key: 'experience', label: '体验吐槽' },
      { key: 'other', label: '其他' },
    ],
  },
  pageLifetimes: {
    show() {
      if (!ensureAuthenticated('pages/feedback/index')) return
    },
  },
  methods: {
    selectType(event: WechatMiniprogram.TouchEvent) {
      const key = String(event.currentTarget.dataset.key || 'suggestion') as FeedbackType
      this.setData({ selectedType: key })
    },
    inputContent(event: WechatMiniprogram.Input) {
      this.setData({ content: event.detail.value })
    },
    inputContact(event: WechatMiniprogram.Input) {
      this.setData({ contact: event.detail.value })
    },
    async submitFeedback() {
      const content = this.data.content.trim()

      if (content.length < 5) {
        wx.showToast({ title: '请至少输入 5 个字的描述', icon: 'none' })
        return
      }

      this.setData({ isSubmitting: true })

      try {
        await submitFeedback({
          contact: this.data.contact.trim(),
          content,
          type: this.data.selectedType,
        })
        wx.showToast({ title: '反馈已提交，谢谢你！', icon: 'success' })
        this.setData({ contact: '', content: '', selectedType: 'suggestion' })
        setTimeout(() => wx.navigateBack(), 1200)
      } catch (error) {
        wx.showToast({ title: '提交失败，请稍后再试', icon: 'none' })
      } finally {
        this.setData({ isSubmitting: false })
      }
    },
  },
})

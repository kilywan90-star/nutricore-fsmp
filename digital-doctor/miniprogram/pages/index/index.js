// pages/index/index.js — Patient Home (WebView → /patient)
const app = getApp();

Page({
  data: {
    webviewUrl: '',
  },

  onLoad() {
    this._initWebView();
  },

  onShow() {
    // Re-init if token changed (e.g. after login)
    const url = this._buildUrl();
    if (url !== this.data.webviewUrl) {
      this.setData({ webviewUrl: url });
    }
  },

  _initWebView() {
    if (!app.isLoggedIn()) {
      app.wechatLogin()
        .then(() => this.setData({ webviewUrl: this._buildUrl() }))
        .catch((err) => {
          console.error('WeChat login failed:', err);
          wx.showToast({ title: '登录失败，请重试', icon: 'none' });
        });
    } else {
      this.setData({ webviewUrl: this._buildUrl() });
    }
  },

  _buildUrl() {
    const baseUrl = app.globalData.baseUrl;
    const token = app.globalData.token || '';
    return `${baseUrl}/patient?token=${encodeURIComponent(token)}`;
  },

  /** Receive messages from the WebView H5 page. */
  onWebViewMessage(e) {
    const messages = e.detail?.data || [];
    for (const msg of messages) {
      if (msg.type === 'subscribeReminder') {
        wx.requestSubscribeMessage({
          tmplIds: [msg.templateId || 'medication_reminder'],
          success: () => wx.showToast({ title: '已订阅提醒', icon: 'success' }),
        });
      }
    }
  },
});

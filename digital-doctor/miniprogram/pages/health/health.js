// pages/health/health.js — Health Coach (WebView → /patient/coach)
const app = getApp();

Page({
  data: {
    webviewUrl: '',
  },

  onLoad() {
    this._initWebView();
  },

  onShow() {
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
    return `${baseUrl}/patient/coach?token=${encodeURIComponent(token)}`;
  },

  onWebViewMessage(e) {
    // Forward H5 messages from the health coach page
  },
});

// pages/mine/mine.js — Native "我的" page showing profile and health summary
const app = getApp();

Page({
  data: {
    isLoggedIn: false,
    user: null,
    metrics: {
      hba1c: null,
      avgGlucose: null,
    },
    loading: true,
  },

  onShow() {
    this.setData({ isLoggedIn: app.isLoggedIn() });
    if (app.isLoggedIn()) {
      this.setData({ user: app.globalData.userInfo });
      this._fetchHealthMetrics();
    } else {
      this.setData({ loading: false });
    }
  },

  /** Fetch latest health metrics from backend. */
  _fetchHealthMetrics() {
    const token = app.globalData.token;
    wx.request({
      url: `${app.globalData.baseUrl}/api/v1/patient/glucose-stats`,
      method: 'POST',
      header: { Authorization: `Bearer ${token}` },
      data: [],
      success: (res) => {
        if (res.statusCode === 200) {
          this.setData({
            metrics: {
              hba1c: null, // HbA1c is from lab reports endpoint
              avgGlucose: res.data.avg || null,
            },
            loading: false,
          });
        } else {
          this.setData({ loading: false });
        }
      },
      fail: () => {
        this.setData({ loading: false });
      },
    });
  },

  /** Handle logout. */
  handleLogout() {
    wx.showModal({
      title: '确认退出',
      content: '退出后需要重新登录',
      success: (res) => {
        if (res.confirm) {
          app.logout();
          this.setData({
            isLoggedIn: false,
            user: null,
            metrics: { hba1c: null, avgGlucose: null },
          });
          wx.reLaunch({ url: '/pages/index/index' });
        }
      },
    });
  },

  /** Trigger WeChat login. */
  handleLogin() {
    app.wechatLogin()
      .then(() => {
        this.setData({
          isLoggedIn: true,
          user: app.globalData.userInfo,
        });
        this._fetchHealthMetrics();
      })
      .catch((err) => {
        console.error('Login failed:', err);
        wx.showToast({ title: '登录失败', icon: 'none' });
      });
  },
});

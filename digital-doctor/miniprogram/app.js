// app.js — 数字医生分身 微信小程序入口
const BASE_URL = 'https://your-domain.com';

App({
  globalData: {
    userInfo: null,
    token: null,
    baseUrl: BASE_URL,
  },

  onLaunch() {
    this._restoreSession();
  },

  /** Restore JWT from local storage if available. */
  _restoreSession() {
    try {
      const token = wx.getStorageSync('access_token');
      const userInfo = wx.getStorageSync('user_info');
      if (token) {
        this.globalData.token = token;
        this.globalData.userInfo = userInfo || null;
      }
    } catch (e) {
      console.warn('Failed to restore session:', e);
    }
  },

  /** wx.login → send code to backend → get JWT → store. */
  wechatLogin() {
    return new Promise((resolve, reject) => {
      wx.login({
        success: (loginRes) => {
          if (!loginRes.code) {
            reject(new Error('wx.login returned no code'));
            return;
          }
          this._exchangeCode(loginRes.code)
            .then((data) => {
              this._persistSession(data);
              resolve(data);
            })
            .catch(reject);
        },
        fail: (err) => reject(err),
      });
    });
  },

  /** POST code to backend /api/v1/auth/wechat-login. */
  _exchangeCode(code) {
    return new Promise((resolve, reject) => {
      wx.request({
        url: `${this.globalData.baseUrl}/api/v1/auth/wechat-login`,
        method: 'POST',
        data: { code },
        success: (res) => {
          if (res.statusCode === 200 && res.data.access_token) {
            resolve(res.data);
          } else {
            reject(new Error(res.data.detail || 'WeChat login failed'));
          }
        },
        fail: (err) => reject(err),
      });
    });
  },

  /** Persist token and user info to storage. */
  _persistSession(data) {
    this.globalData.token = data.access_token;
    this.globalData.userInfo = data.user;
    try {
      wx.setStorageSync('access_token', data.access_token);
      wx.setStorageSync('refresh_token', data.refresh_token);
      wx.setStorageSync('user_info', data.user);
    } catch (e) {
      console.warn('Failed to persist session:', e);
    }
  },

  /** Clear session on logout. */
  logout() {
    this.globalData.token = null;
    this.globalData.userInfo = null;
    try {
      wx.removeStorageSync('access_token');
      wx.removeStorageSync('refresh_token');
      wx.removeStorageSync('user_info');
    } catch (e) {
      console.warn('Failed to clear session:', e);
    }
  },

  /** Check if user is logged in. */
  isLoggedIn() {
    return !!this.globalData.token;
  },
});

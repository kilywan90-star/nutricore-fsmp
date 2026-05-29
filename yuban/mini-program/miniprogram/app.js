// 渔伴 - 钓鱼社交小程序
const API_BASE = 'http://localhost:8000/api';

App({
  globalData: {
    userInfo: null,
    location: null, // {lat, lng}
    apiBase: API_BASE,
  },

  onLaunch() {
    this.getLocation();
  },

  getLocation() {
    wx.getLocation({
      type: 'gcj02',
      success: (res) => {
        this.globalData.location = {
          lat: res.latitude,
          lng: res.longitude,
        };
      },
      fail: () => {
        // 默认北京坐标
        this.globalData.location = { lat: 39.9042, lng: 116.4074 };
      },
    });
  },

  request(url, method = 'GET', data = {}) {
    return new Promise((resolve, reject) => {
      wx.request({
        url: API_BASE + url,
        method,
        data,
        header: { 'Content-Type': 'application/json' },
        success: (res) => {
          if (res.statusCode === 200) {
            resolve(res.data);
          } else {
            reject(res);
          }
        },
        fail: reject,
      });
    });
  },
});

const api = require('../../utils/api');
const app = getApp();

Page({
  data: {
    userInfo: null,
    orders: [],
  },

  onShow() {
    this.loadUserInfo();
    this.loadOrders();
  },

  async loadUserInfo() {
    try {
      const res = await api.getProfile();
      if (res.status === 'success') {
        this.setData({ userInfo: res.data });
      }
    } catch (err) { /* 未登录 */ }
  },

  async loadOrders() {
    try {
      const res = await api.getOrders(1);
      if (res.status === 'success') {
        this.setData({ orders: res.data.orders || [] });
      }
    } catch (err) { /* 静默 */ }
  },

  goToPlans() {
    wx.navigateTo({ url: '/pages/plans/plans' });
  },

  async login() {
    try {
      const { code } = await wx.login();
      const res = await api.login(code);
      if (res.status === 'success') {
        wx.setStorageSync('token', res.data.token);
        app.globalData.token = res.data.token;
        this.loadUserInfo();
        wx.showToast({ title: '登录成功', icon: 'success' });
      }
    } catch (err) {
      wx.showToast({ title: '登录失败', icon: 'error' });
    }
  },

  onShareAppMessage() {
    return {
      title: 'AI智能标书助手 — 快速生成专业投标文件',
      path: '/pages/index/index'
    };
  }
});

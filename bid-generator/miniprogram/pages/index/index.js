const api = require('../../utils/api');
const app = getApp();

Page({
  data: {
    industries: [],
    bidTypes: [],
    currentIndustry: '',
    currentType: '',
    projects: [],
    industryIcons: {
      '政府采购': '🏛️', '工程建设': '🏗️', 'IT服务': '💻',
      '物业服务': '🏢', '医疗设备': '🏥', '通用': '📋'
    }
  },

  async onLoad() {
    // 微信一键登录
    try {
      const { code } = await wx.login();
      const res = await api.login(code);
      if (res.status === 'success') {
        wx.setStorageSync('token', res.data.token);
        app.globalData.token = res.data.token;
        app.globalData.userInfo = res.data;
      }
    } catch (err) {
      console.log('登录跳过（开发模式）', err);
    }

    this.loadIndustries();
    this.loadProjects();
  },

  async onShow() {
    this.loadProjects();
  },

  async loadIndustries() {
    try {
      const res = await api.getIndustries();
      if (res.status === 'success') {
        const industries = Object.keys(res.data);
        this.setData({ industries });
      }
    } catch (err) {
      this.setData({ industries: ['政府采购', '工程建设', 'IT服务', '物业服务', '医疗设备', '通用'] });
    }
  },

  selectIndustry(e) {
    const industry = e.currentTarget.dataset.industry;
    this.setData({ currentIndustry: industry, currentType: '' });
    this.loadBidTypes(industry);
  },

  async loadBidTypes(industry) {
    try {
      const res = await api.getIndustries();
      if (res.status === 'success') {
        this.setData({ bidTypes: res.data[industry] || ['通用'] });
      }
    } catch (err) {
      this.setData({ bidTypes: ['通用'] });
    }
  },

  selectType(e) {
    this.setData({ currentType: e.currentTarget.dataset.type });
  },

  async loadProjects() {
    try {
      const res = await api.getProjects();
      if (res.status === 'success') {
        this.setData({ projects: res.data.slice(0, 5) });
      }
    } catch (err) { /* 静默失败 */ }
  },

  startGenerate() {
    if (!this.data.currentIndustry) {
      wx.showToast({ title: '请选择行业', icon: 'none' });
      return;
    }
    wx.navigateTo({
      url: `/pages/generate/generate?industry=${this.data.currentIndustry}&type=${this.data.currentType || '通用'}`
    });
  },

  openProject(e) {
    const id = e.currentTarget.dataset.id;
    wx.navigateTo({ url: `/pages/edit/edit?projectId=${id}` });
  }
});

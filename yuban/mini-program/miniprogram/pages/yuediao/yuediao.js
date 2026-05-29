const app = getApp();

Page({
  data: {
    activeTab: 'buddies',
    sessions: [],
    companions: [],
    showCreateModal: false,
    createForm: { spotName: '', date: '', maxParticipants: '2', requirements: '' },
  },

  onShow() {
    this.loadSessions();
    this.loadCompanions();
  },

  switchTab(e) {
    const tab = e.currentTarget.dataset.tab;
    this.setData({ activeTab: tab });
    if (tab === 'buddies') this.loadSessions();
    else this.loadCompanions();
  },

  // ===== 找钓友 =====
  async loadSessions() {
    try {
      const sessions = await app.request('/booking/yuediao?status=招募中&page=1&page_size=20');
      this.setData({ sessions });
    } catch (e) {
      console.log('加载约钓失败', e);
    }
  },

  loadMoreSessions() { /* 分页加载 */ },

  showCreateSession() { this.setData({ showCreateModal: true }); },
  hideCreateSession() { this.setData({ showCreateModal: false }); },

  onSpotInput(e) { this.setData({ 'createForm.spotName': e.detail.value }); },
  onDateInput(e) { this.setData({ 'createForm.date': e.detail.value }); },
  onMaxInput(e) { this.setData({ 'createForm.maxParticipants': e.detail.value }); },
  onReqInput(e) { this.setData({ 'createForm.requirements': e.detail.value }); },

  async submitSession() {
    const f = this.data.createForm;
    if (!f.date) {
      wx.showToast({ title: '请输入日期', icon: 'none' });
      return;
    }
    try {
      await app.request('/booking/yuediao', 'POST', {
        spot_id: 1,
        target_date: f.date,
        max_participants: parseInt(f.maxParticipants) || 2,
        requirements: f.requirements,
      });
      wx.showToast({ title: '发布成功!', icon: 'success' });
      this.setData({ showCreateModal: false });
      this.loadSessions();
    } catch (e) {
      wx.showToast({ title: '发布失败', icon: 'none' });
    }
  },

  async joinSession(e) {
    const id = e.currentTarget.dataset.id;
    wx.showToast({ title: `已申请加入 #${id}`, icon: 'success' });
  },

  // ===== 陪钓服务 =====
  async loadCompanions() {
    try {
      const companions = await app.request('/booking/companions?page=1&page_size=20');
      this.setData({ companions });
    } catch (e) {
      console.log('加载陪钓服务者失败', e);
    }
  },

  async bookCompanion(e) {
    const id = e.currentTarget.dataset.id;
    try {
      await app.request('/booking/orders', 'POST', {
        companion_id: id,
        spot_id: 1,
        service_date: '2026-06-01T08:00:00',
        duration: 2.0,
      });
      wx.showToast({ title: '预约成功!', icon: 'success' });
    } catch (e) {
      wx.showToast({ title: '预约失败', icon: 'none' });
    }
  },

  showRegisterCompanion() {
    wx.showToast({ title: '功能开发中...', icon: 'none' });
  },
});

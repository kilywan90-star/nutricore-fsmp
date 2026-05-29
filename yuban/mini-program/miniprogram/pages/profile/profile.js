const app = getApp();

Page({
  data: {
    user: null,
    remainingDays: 90,
  },

  onShow() {
    this.loadProfile();
  },

  async loadProfile() {
    try {
      const user = await app.request('/users/profile');
      this.setData({
        user,
        remainingDays: user.is_member ? '已' : Math.max(0, 90 - Math.floor((Date.now() - new Date(user.created_at).getTime()) / 86400000)),
      });
    } catch (e) {
      console.log('加载用户信息失败', e);
      this.setData({
        user: {
          nickname: '钓鱼佬',
          level: 1,
          total_catches: 0,
          max_record: 0,
          favorite_methods: ['台钓'],
          is_member: false,
        },
      });
    }
  },

  upgradeMember() {
    wx.showModal({
      title: '升级会员',
      content: '会员功能开发中，敬请期待！\n\n会员价: ¥19.9/月\n\n特权:\n· 无限查看钓点详情\n· 优先约钓匹配\n· 陪钓服务8折\n· 专属AI装备推荐',
      showCancel: true,
      confirmText: '知道了',
    });
  },

  goToOrders() { wx.navigateTo({ url: '/pages/profile/orders' }); },
  goToCollections() { wx.showToast({ title: '功能开发中', icon: 'none' }); },
  goToFishingLog() { wx.showToast({ title: '功能开发中', icon: 'none' }); },
  goToAchievements() { wx.showToast({ title: '功能开发中', icon: 'none' }); },
  goToCompanionProfile() { wx.showToast({ title: '功能开发中', icon: 'none' }); },
  goToSettings() { wx.showToast({ title: '功能开发中', icon: 'none' }); },
  goToAbout() {
    wx.showModal({
      title: '关于渔伴',
      content: '渔伴 v0.1.0\n\n钓鱼社交小程序，让每个钓鱼佬不再孤单。\n\n核心功能:\n· 全维度钓点情报\n· 智能钓鱼指数+蚊虫预报\n· 社区分享鱼获风景\n· 约钓匹配+陪钓服务',
      showCancel: false,
    });
  },
});

const app = getApp();

Page({
  data: {
    weather: { temp: 25, humidity: 65, wind_speed: 8, wind_direction: '南风' },
    insect: { level: 2, advice: '偶有蚊虫，基本不影响', description: '偶有蚊虫' },
    fishingIndex: { score: 78, summary: '今天是个钓鱼的好日子!' },
    indexClass: 'index-good',
    feedList: [],
    gearData: '',
  },

  onLoad() {
    this.loadFishingIndex();
    this.loadFeed();
  },

  onShow() {
    if (app.globalData.location) {
      this.loadFishingIndex();
    }
  },

  async loadFishingIndex() {
    const loc = app.globalData.location || { lat: 39.9042, lng: 116.4074 };
    try {
      const data = await app.request(
        `/weather/fishing-index?lat=${loc.lat}&lng=${loc.lng}&spot_type=黑坑`
      );
      const idx = data.fishing_index;
      let indexClass = 'index-good';
      if (idx.score >= 80) indexClass = 'index-excellent';
      else if (idx.score >= 60) indexClass = 'index-good';
      else if (idx.score >= 40) indexClass = 'index-ok';
      else indexClass = 'index-bad';

      this.setData({
        weather: data.weather,
        insect: data.insect,
        fishingIndex: idx,
        indexClass,
        gearData: JSON.stringify(idx.gear_recommendations),
      });
    } catch (e) {
      console.log('加载钓鱼指数失败，使用默认值', e);
    }
  },

  async loadFeed() {
    try {
      const data = await app.request('/social/feed?page=1&page_size=5');
      this.setData({ feedList: data });
    } catch (e) {
      console.log('加载动态失败', e);
    }
  },

  onPullDownRefresh() {
    this.loadFishingIndex();
    this.loadFeed();
    wx.stopPullDownRefresh();
  },

  goToSpots() { wx.switchTab({ url: '/pages/spots/spots' }); },
  goToYuediao() { wx.switchTab({ url: '/pages/yuediao/yuediao' }); },
  goToWeather() {
    const loc = app.globalData.location || { lat: 39.9042, lng: 116.4074 };
    wx.navigateTo({ url: `/pages/index/weather?lat=${loc.lat}&lng=${loc.lng}` });
  },
  goToCompanion() {
    wx.navigateTo({ url: '/pages/yuediao/companions' });
  },
});

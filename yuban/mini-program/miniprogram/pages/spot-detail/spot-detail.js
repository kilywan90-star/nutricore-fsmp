const app = getApp();

Page({
  data: {
    spot: {},
    weather: null,
    insect: { level: 0 },
    fishingIndex: null,
    indexClass: 'index-good',
  },

  onLoad(options) {
    const id = options.id;
    if (id) {
      this.loadSpotDetail(id);
      this.loadFishingIndex(id);
    }
  },

  async loadSpotDetail(id) {
    const loc = app.globalData.location || {};
    let url = `/spots/${id}`;
    if (loc.lat) url += `?lat=${loc.lat}&lng=${loc.lng}`;
    try {
      const spot = await app.request(url);
      this.setData({ spot });
    } catch (e) {
      console.log('加载钓点详情失败', e);
    }
  },

  async loadFishingIndex(spotId) {
    try {
      const spot = this.data.spot;
      const lat = spot.lat;
      const lng = spot.lng;
      const data = await app.request(
        `/weather/fishing-index?lat=${lat}&lng=${lng}&spot_type=${spot.type || '黑坑'}`
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
      });
    } catch (e) {
      console.log('加载钓鱼指数失败', e);
    }
  },

  callTel() {
    const tel = this.data.spot.tel;
    if (tel) {
      wx.makePhoneCall({ phoneNumber: tel });
    }
  },

  openNavigation() {
    const spot = this.data.spot;
    wx.openLocation({
      latitude: spot.lat,
      longitude: spot.lng,
      name: spot.name,
      address: spot.address,
      scale: 16,
    });
  },

  goToYuediao() {
    wx.navigateTo({ url: `/pages/yuediao/create?spotId=${this.data.spot.id}` });
  },
});

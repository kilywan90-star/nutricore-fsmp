const app = getApp();

Page({
  data: {
    keyword: '',
    currentType: '',
    currentCity: '',
    typeFilters: ['全部类型', '黑坑', '野钓', '水库', '海钓', '溪流', '路亚基地'],
    cityFilters: ['当前城市', '北京', '上海', '广州', '深圳', '成都', '武汉', '杭州', '南京'],
    sortBy: 'distance',
    sortLabel: '距离优先',
    centerLat: 39.9042,
    centerLng: 116.4074,
    markers: [],
    spots: [],
    drawerExpanded: false,
    loading: false,
  },

  onLoad() {
    const loc = app.globalData.location || { lat: 39.9042, lng: 116.4074 };
    this.setData({ centerLat: loc.lat, centerLng: loc.lng });
  },

  onShow() {
    this.loadSpots();
  },

  async loadSpots() {
    this.setData({ loading: true });
    const loc = app.globalData.location || { lat: 39.9042, lng: 116.4074 };
    let url = `/spots/list?lat=${loc.lat}&lng=${loc.lng}&page=1&page_size=50&sort_by=${this.data.sortBy}`;

    if (this.data.keyword) url += `&keyword=${this.data.keyword}`;
    if (this.data.currentType) url += `&type=${this.data.currentType}`;
    if (this.data.currentCity) url += `&city=${this.data.currentCity}`;

    try {
      const spots = await app.request(url);
      this.setData({ spots, loading: false });
      this.updateMarkers(spots);
    } catch (e) {
      console.log('加载钓点失败', e);
      this.setData({ loading: false });
    }
  },

  updateMarkers(spots) {
    const markers = spots.map(s => ({
      id: s.id,
      latitude: s.lat,
      longitude: s.lng,
      title: s.name,
      iconPath: this.getMarkerIcon(s.type),
      width: 32,
      height: 32,
      callout: {
        content: s.name,
        fontSize: 12,
        borderRadius: 4,
        padding: 4,
        display: 'BYCLICK',
      },
    }));
    this.setData({ markers });
  },

  getMarkerIcon(type) {
    // MVP阶段使用统一图标，后续可替换
    return '/static/icons/marker-fishing.png';
  },

  onSearchInput(e) { this.setData({ keyword: e.detail.value }); },

  onSearch() { this.loadSpots(); },

  onTypeChange(e) {
    const idx = parseInt(e.detail.value);
    const type = idx === 0 ? '' : this.data.typeFilters[idx];
    this.setData({ currentType: type });
    this.loadSpots();
  },

  onCityChange(e) {
    const idx = parseInt(e.detail.value);
    const city = idx === 0 ? '' : this.data.cityFilters[idx];
    this.setData({ currentCity: city });
    this.loadSpots();
  },

  toggleSort() {
    const next = this.data.sortBy === 'distance' ? 'rating' : 'distance';
    const label = next === 'distance' ? '距离优先' : '评分优先';
    this.setData({ sortBy: next, sortLabel: label });
    this.loadSpots();
  },

  toggleDrawer() {
    this.setData({ drawerExpanded: !this.data.drawerExpanded });
  },

  onMarkerTap(e) {
    wx.navigateTo({ url: `/pages/spot-detail/spot-detail?id=${e.markerId}` });
  },

  goToDetail(e) {
    wx.navigateTo({ url: `/pages/spot-detail/spot-detail?id=${e.currentTarget.dataset.id}` });
  },
});

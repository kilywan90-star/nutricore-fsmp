const app = getApp();

Page({
  data: {
    currentTab: 'all',
    posts: [],
    loading: false,
    page: 1,
    showPublishModal: false,
    postTypes: ['鱼获', '风景', '经验', '求助'],
    publishForm: { type: '鱼获', content: '' },
  },

  onShow() { this.loadPosts(); },

  switchTab(e) {
    const tab = e.currentTarget.dataset.tab;
    this.setData({ currentTab: tab, page: 1, posts: [] });
    this.loadPosts();
  },

  async loadPosts() {
    this.setData({ loading: true });
    const typeMap = { yuhuo: '鱼获', fengjing: '风景', jingyan: '经验' };
    let url = `/social/feed?page=${this.data.page}&page_size=20`;
    if (typeMap[this.data.currentTab]) {
      url += `&post_type=${typeMap[this.data.currentTab]}`;
    }

    try {
      const posts = await app.request(url);
      if (this.data.page === 1) {
        this.setData({ posts, loading: false });
      } else {
        this.setData({
          posts: [...this.data.posts, ...posts],
          loading: false,
        });
      }
    } catch (e) {
      console.log('加载动态失败', e);
      this.setData({ loading: false });
    }
  },

  loadMore() {
    this.setData({ page: this.data.page + 1 });
    this.loadPosts();
  },

  showPublish() { this.setData({ showPublishModal: true }); },
  hidePublish() { this.setData({ showPublishModal: false }); },

  onPostTypeChange(e) {
    const idx = parseInt(e.detail.value);
    this.setData({ 'publishForm.type': this.data.postTypes[idx] });
  },

  onContentInput(e) {
    this.setData({ 'publishForm.content': e.detail.value });
  },

  async submitPost() {
    if (!this.data.publishForm.content.trim()) {
      wx.showToast({ title: '请输入内容', icon: 'none' });
      return;
    }

    try {
      await app.request('/social/posts', 'POST', this.data.publishForm);
      wx.showToast({ title: '发布成功!', icon: 'success' });
      this.setData({
        showPublishModal: false,
        page: 1, posts: [],
        publishForm: { type: '鱼获', content: '' },
      });
      this.loadPosts();
    } catch (e) {
      wx.showToast({ title: '发布失败', icon: 'none' });
    }
  },

  onLike(e) {
    const id = e.currentTarget.dataset.id;
    const posts = this.data.posts.map(p => {
      if (p.id === id) p.likes_count += 1;
      return p;
    });
    this.setData({ posts });
    wx.showToast({ title: '已点赞', icon: 'none', duration: 500 });
  },
});

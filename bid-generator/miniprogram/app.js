// 小程序入口
App({
  globalData: {
    token: '',
    userInfo: null,
    apiBase: 'https://your-domain.com/api',  // 替换为实际域名
  },

  onLaunch() {
    // 检查本地 token
    const token = wx.getStorageSync('token');
    if (token) {
      this.globalData.token = token;
      this.loadUserInfo();
    }
  },

  async loadUserInfo() {
    try {
      const res = await this.request('/auth/profile');
      if (res.status === 'success') {
        this.globalData.userInfo = res.data;
      }
    } catch (err) {
      console.error('加载用户信息失败', err);
    }
  },

  request(path, options = {}) {
    return new Promise((resolve, reject) => {
      const header = { ...options.header };
      if (this.globalData.token) {
        header['Authorization'] = `Bearer ${this.globalData.token}`;
      }

      wx.request({
        url: this.globalData.apiBase + path,
        method: options.method || 'GET',
        data: options.data,
        header,
        timeout: options.timeout || 120000,
        success(res) {
          if (res.statusCode === 401) {
            wx.removeStorageSync('token');
            wx.navigateTo({ url: '/pages/index/index' });
            reject(new Error('登录已过期'));
          } else if (res.statusCode >= 400) {
            reject(new Error(res.data?.detail || '请求失败'));
          } else {
            resolve(res.data);
          }
        },
        fail(err) {
          reject(new Error('网络请求失败: ' + err.errMsg));
        }
      });
    });
  },

  // SSE 流式请求
  streamRequest(path, data, onChunk, onDone, onError) {
    const token = this.globalData.token;
    const requestTask = wx.request({
      url: this.globalData.apiBase + path,
      method: 'POST',
      data,
      header: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json',
      },
      enableChunked: true,
      timeout: 300000,
      success() {},
      fail(err) {
        if (onError) onError(err);
      }
    });

    let buffer = '';
    requestTask.onChunkReceived((chunk) => {
      buffer += new TextDecoder().decode(chunk.data);
      const lines = buffer.split('\n');
      buffer = lines.pop() || '';

      for (const line of lines) {
        if (line.startsWith('data: ')) {
          const data = line.slice(6);
          if (data === '[DONE]') {
            if (onDone) onDone();
            return;
          }
          try {
            const parsed = JSON.parse(data);
            if (parsed.error) {
              if (onError) onError(new Error(parsed.error));
              return;
            }
            if (parsed.done) {
              if (onDone) onDone(parsed.usage);
              return;
            }
            if (parsed.content && onChunk) {
              onChunk(parsed.content);
            }
          } catch (e) {}
        }
      }
    });

    return requestTask;
  }
});

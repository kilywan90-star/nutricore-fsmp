const api = require('../../utils/api');

Page({
  data: {
    projectId: null,
    project: null,
    bidContent: '',
    editableHtml: '',
    isValidating: false,
    validationResult: null,
    isExporting: false,
  },

  onLoad(options) {
    const projectId = parseInt(options.projectId);
    this.setData({ projectId });
    this.loadProject(projectId);
  },

  async loadProject(id) {
    try {
      const res = await api.getProject(id);
      if (res.status === 'success') {
        const project = res.data;
        this.setData({
          project,
          bidContent: project.bid_content || '',
        });
      }
    } catch (err) {
      wx.showToast({ title: '加载失败', icon: 'error' });
    }
  },

  // ── 校验 ────────────────────────────────────

  async validateBid() {
    this.setData({ isValidating: true });
    try {
      const res = await api.validateBid({
        project_id: this.data.projectId,
        check_types: ['completeness', 'scoring', 'format', 'risk']
      });
      if (res.status === 'success') {
        this.setData({ validationResult: res.data });
        const { errors, warnings } = res.data;
        const msg = `检查完成：${errors.length} 个错误，${warnings.length} 个警告`;
        wx.showModal({ title: '智能校验结果', content: msg, showCancel: false });
      }
    } catch (err) {
      wx.showToast({ title: '校验失败', icon: 'error' });
    }
    this.setData({ isValidating: false });
  },

  // ── 导出 ────────────────────────────────────

  async exportDocx() {
    this.setData({ isExporting: true });
    try {
      const res = await api.exportDocx(this.data.projectId);
      wx.showToast({ title: '导出成功（文件下载功能需在真机调试）', icon: 'success' });
    } catch (err) {
      wx.showToast({ title: '导出失败', icon: 'error' });
    }
    this.setData({ isExporting: false });
  },

  // ── 章节重生成 ──────────────────────────────

  async regenerateSection() {
    wx.showActionSheet({
      itemList: ['投标函', '技术方案', '商务标', '价格标', '售后服务'],
      success: async (res) => {
        const sections = ['投标函', '技术方案', '商务标', '价格标', '售后服务'];
        const section = sections[res.tapIndex];
        try {
          const result = await api.regenerateSection(section, {
            project_id: this.data.projectId,
            section_name: section,
            feedback: '请优化此章节内容'
          });
          if (result.status === 'success') {
            wx.showToast({ title: `${section} 已重新生成`, icon: 'success' });
            this.loadProject(this.data.projectId);
          }
        } catch (err) {
          wx.showToast({ title: '重新生成失败', icon: 'error' });
        }
      }
    });
  },

  // ── 分享 ────────────────────────────────────

  onShareAppMessage() {
    return {
      title: `${this.data.project?.name || '标书'} - AI智能标书助手`,
      path: `/pages/edit/edit?projectId=${this.data.projectId}`
    };
  }
});

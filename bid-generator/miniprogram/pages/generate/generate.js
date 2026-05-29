const api = require('../../utils/api');

Page({
  data: {
    step: 1,
    industry: '通用',
    bidType: '通用',

    // 步骤1
    fileName: '',
    fileSize: '',
    parseStatus: '',
    parseStatusText: '',
    parsedData: null,
    projectId: null,

    // 步骤2
    companyName: '',
    companyInfo: '',
    keyPoints: '',
    additionalRequirements: '',

    // 步骤3
    isGenerating: false,
    generatedContent: '',
    generatedChars: 0,
    formattedContent: '',
  },

  onLoad(options) {
    this.setData({
      industry: options.industry || '通用',
      bidType: options.type || '通用'
    });
  },

  // ── 步骤1：上传 ──────────────────────────────────

  async uploadFile() {
    const that = this;
    wx.chooseMessageFile({
      count: 1,
      type: 'file',
      extension: ['pdf', 'doc', 'docx', 'xls', 'xlsx'],
      success(res) {
        const file = res.tempFiles[0];
        that.setData({
          fileName: file.name,
          fileSize: (file.size / 1024).toFixed(1) + ' KB',
          parseStatus: 'parsing',
          parseStatusText: '正在解析...'
        });
        that.parseFile(file);
      }
    });
  },

  async parseFile(file) {
    try {
      // 上传并解析文件
      const uploadRes = await wx.uploadFile({
        url: getApp().globalData.apiBase + '/parser/upload_tender?project_id=' + (this.data.projectId || 0),
        filePath: file.path,
        name: 'file',
        header: { 'Authorization': `Bearer ${getApp().globalData.token}` }
      });

      const uploadData = JSON.parse(uploadRes.data);

      // 先创建项目（如果还没创建）
      if (!this.data.projectId) {
        const projRes = await api.createProject({
          name: this.data.fileName.replace(/\.[^.]+$/, ''),
          type: this.data.bidType,
          industry: this.data.industry,
          deadline: '',
          description: uploadData.data?.content_preview || ''
        });
        this.setData({ projectId: projRes.data.id });
      }

      // AI 智能解析招标文件
      const parseRes = await api.parseTender({
        project_id: this.data.projectId,
        tender_content: uploadData.data?.content_preview || ''
      });

      if (parseRes.status === 'success') {
        this.setData({
          parsedData: parseRes.data.parsed,
          parseStatus: 'done',
          parseStatusText: '解析完成'
        });
      }

    } catch (err) {
      this.setData({ parseStatus: 'error', parseStatusText: '解析失败: ' + err.message });
    }
  },

  // ── 步骤导航 ─────────────────────────────────────

  nextStep() {
    if (!this.data.parsedData) {
      wx.showToast({ title: '请先上传并解析招标文件', icon: 'none' });
      return;
    }
    this.setData({ step: 2 });
  },

  prevStep() {
    this.setData({ step: 1 });
  },

  // ── 表单输入 ─────────────────────────────────────

  onFieldInput(e) {
    const field = e.currentTarget.dataset.field;
    this.setData({ [field]: e.detail.value });
  },

  // ── AI 生成 ──────────────────────────────────────

  startGenerate() {
    if (!this.data.companyName) {
      wx.showToast({ title: '请输入公司名称', icon: 'none' });
      return;
    }

    this.setData({ step: 3, isGenerating: true, generatedContent: '', generatedChars: 0, formattedContent: '' });

    const that = this;
    const decoder = new TextDecoder();

    api.generateStream({
      project_id: this.data.projectId,
      industry: this.data.industry,
      bid_type: this.data.bidType,
      company_name: this.data.companyName,
      company_info: this.data.companyInfo,
      key_points: this.data.keyPoints,
      additional_requirements: this.data.additionalRequirements,
    },
    // onChunk
    (chunk) => {
      const content = that.data.generatedContent + chunk;
      that.setData({
        generatedContent: content,
        generatedChars: content.length,
        formattedContent: that.markdownToHtml(content),
      });
    },
    // onDone
    (usage) => {
      that.setData({ isGenerating: false });
      wx.showToast({ title: '标书生成完成！', icon: 'success' });
      if (usage) {
        console.log('Token用量:', usage);
      }
    },
    // onError
    (err) => {
      that.setData({ isGenerating: false });
      wx.showToast({ title: '生成失败: ' + err.message, icon: 'error' });
    });
  },

  // 简单的 Markdown → HTML（生产环境推荐用 wxParser 或 towxml 插件）
  markdownToHtml(md) {
    let html = md
      .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
      .replace(/^### (.+)$/gm, '<h3>$1</h3>')
      .replace(/^## (.+)$/gm, '<h2>$1</h2>')
      .replace(/^# (.+)$/gm, '<h1>$1</h1>')
      .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
      .replace(/\n---\n/g, '<hr/>')
      .replace(/\n\n/g, '<br/><br/>')
      .replace(/\n/g, '<br/>');
    return html;
  },

  regenerate() {
    this.setData({ step: 3, isGenerating: true, generatedContent: '', generatedChars: 0 });
    this.startGenerate();
  },

  goEdit() {
    wx.navigateTo({
      url: `/pages/edit/edit?projectId=${this.data.projectId}`
    });
  }
});

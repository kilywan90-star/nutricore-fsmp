const api = require('../../utils/api');

Page({
  data: {
    industries: [],
    templates: [],
    currentIndustry: '',
  },

  async onLoad() {
    try {
      const res = await api.getIndustries();
      if (res.status === 'success') {
        const industries = Object.keys(res.data);
        this.setData({ industries, currentIndustry: industries[0] || '' });
        this.loadTemplates();
      }
    } catch (err) {
      this.setData({ industries: ['政府采购', '工程建设', 'IT服务', '物业服务', '医疗设备'] });
    }
  },

  async loadTemplates() {
    // 模板从 industries API 获取（每个行业对应模板）
    const templates = [
      { name: '政府采购货物类', industry: '政府采购', type: '货物采购', desc: '含完整报价表和偏离表模板' },
      { name: '政府采购服务类', industry: '政府采购', type: '服务采购', desc: '含服务方案和人员配置模板' },
      { name: '建筑工程施工类', industry: '工程建设', type: '施工总承包', desc: '含施工组织设计和工程量清单' },
      { name: 'IT软件开发类', industry: 'IT服务', type: '软件开发', desc: '含技术方案和架构设计模板' },
      { name: 'IT系统集成类', industry: 'IT服务', type: '系统集成', desc: '含系统架构和实施计划模板' },
      { name: '物业管理类', industry: '物业服务', type: '物业管理', desc: '含各专项服务方案模板' },
      { name: '医疗设备采购类', industry: '医疗设备', type: '设备采购', desc: '含技术参数响应表模板' },
    ];

    const filtered = this.data.currentIndustry
      ? templates.filter(t => t.industry === this.data.currentIndustry)
      : templates;

    this.setData({ templates: filtered });
  },

  selectIndustry(e) {
    this.setData({ currentIndustry: e.currentTarget.dataset.industry }, () => {
      this.loadTemplates();
    });
  },

  useTemplate(e) {
    const t = e.currentTarget.dataset.template;
    wx.navigateTo({
      url: `/pages/generate/generate?industry=${t.industry}&type=${t.type}`
    });
  }
});

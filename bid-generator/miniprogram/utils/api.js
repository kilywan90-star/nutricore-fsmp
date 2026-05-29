// API 工具封装
const app = getApp();

const api = {
  // 用户
  login(code, nickname, avatarUrl) {
    return app.request('/auth/login/wechat', {
      method: 'POST',
      data: { code, nickname, avatar_url: avatarUrl }
    });
  },
  getProfile() {
    return app.request('/auth/profile');
  },

  // 项目
  getProjects() {
    return app.request('/project/');
  },
  createProject(data) {
    return app.request('/project/', { method: 'POST', data });
  },
  getProject(id) {
    return app.request(`/project/${id}`);
  },
  deleteProject(id) {
    return app.request(`/project/${id}`, { method: 'DELETE' });
  },

  // 生成
  generate(data) {
    return app.request('/generator/generate', { method: 'POST', data, timeout: 180000 });
  },
  generateStream(data, onChunk, onDone, onError) {
    return app.streamRequest('/generator/generate/stream', data, onChunk, onDone, onError);
  },
  regenerateSection(sectionName, data) {
    return app.request(`/generator/regenerate/${sectionName}`, { method: 'POST', data });
  },
  parseTender(data) {
    return app.request('/generator/parse-tender', { method: 'POST', data });
  },
  getIndustries() {
    return app.request('/generator/industries');
  },

  // 校验
  validateBid(data) {
    return app.request('/validator/validate', { method: 'POST', data });
  },

  // 导出
  exportDocx(projectId) {
    return app.request('/export/docx', { method: 'POST', data: { project_id: projectId, format: 'docx' } });
  },

  // 支付
  getPlans() {
    return app.request('/payment/plans');
  },
  getCountPacks() {
    return app.request('/payment/count-packs');
  },
  createOrder(data) {
    return app.request('/payment/create-order', { method: 'POST', data });
  },
  getOrders(page = 1) {
    return app.request(`/payment/orders?page=${page}`);
  },
};

module.exports = api;

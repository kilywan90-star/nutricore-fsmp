import axios from 'axios'
// 创建axios实例
const api = axios.create({
  baseURL: '/api',
  timeout: 60000
})
// 请求拦截器
api.interceptors.request.use(
  (config) => {
    return config
  },
  (error) => {
    return Promise.reject(error)
  }
)
// 响应拦截器
api.interceptors.response.use(
  (response) => {
    return response.data
  },
  (error) => {
    console.error('API请求错误:', error)
    return Promise.reject(error)
  }
)
// 项目相关API
export const projectApi = {
  // 获取项目列表
  getProjects: () => api.get('/project'),
  // 获取项目详情
  getProject: (id: number) => api.get(`/project/${id}`),
  // 创建项目
  createProject: (data: any) => api.post('/project', data),
  // 更新项目
  updateProject: (id: number, data: any) => api.put(`/project/${id}`, data),
  // 删除项目
  deleteProject: (id: number) => api.delete(`/project/${id}`),
  // 上传招标文件
  uploadTender: (projectId: number, file: File) => {
    const formData = new FormData()
    formData.append('file', file)
    return api.post(`/parser/upload_tender?project_id=${projectId}`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' }
    })
  }
}
// 知识库相关API
export const knowledgeApi = {
  // 获取知识库列表
  getKnowledgeList: () => api.get('/knowledge'),
  // 上传文件
  uploadFile: (file: File) => {
    const formData = new FormData()
    formData.append('file', file)
    return api.post('/knowledge/upload', formData, {
      headers: { 'Content-Type': 'multipart/form-data' }
    })
  },
  // 删除文件
  deleteKnowledge: (id: number) => api.delete(`/knowledge/${id}`)
}
// 生成相关API
export const generatorApi = {
  // 一键生成标书
  generateBid: (projectId: number) => api.post('/generator/generate_bid', { project_id: projectId }),
  // 重新生成章节
  regenerateSection: (projectId: number, sectionId: string) =>
    api.post('/generator/regenerate_section', { project_id: projectId, section_id: sectionId })
}
// 校验相关API
export const validatorApi = {
  // 校验标书
  validateBid: (projectId: number) => api.post('/validator/validate', { project_id: projectId })
}
// 导出相关API
export const exportApi = {
  // 导出Word
  exportDocx: (projectId: number) => api.post('/export/docx', { project_id: projectId }, { responseType: 'blob' }),
  // 导出PDF
  exportPdf: (projectId: number) => api.post('/export/pdf', { project_id: projectId }, { responseType: 'blob' })
}
// 健康检查
export const healthCheck = () => api.get('/health')
export default api

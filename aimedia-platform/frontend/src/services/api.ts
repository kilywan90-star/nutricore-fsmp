import axios from 'axios'

const api = axios.create({ baseURL: '/api' })

api.interceptors.request.use((config) => {
  const token = localStorage.getItem('token')
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

api.interceptors.response.use(
  (res) => res,
  (err) => {
    if (err.response?.status === 401) {
      localStorage.removeItem('token')
      window.location.href = '/login'
    }
    return Promise.reject(err)
  },
)

export const authApi = {
  login: (username: string, password: string) =>
    api.post('/auth/login', { username, password }).then(r => r.data),
}

export const contentApi = {
  create: (data: Record<string, unknown>) =>
    api.post('/content', data).then(r => r.data),
  list: (params?: Record<string, unknown>) =>
    api.get('/content', { params }).then(r => r.data),
  get: (id: string) =>
    api.get(`/content/${id}`).then(r => r.data),
  complianceCheck: (id: string) =>
    api.post(`/content/${id}/compliance-check`).then(r => r.data),
}

export const reviewApi = {
  submit: (data: Record<string, unknown>) =>
    api.post('/review/submit', data).then(r => r.data),
  getRecords: (contentId: string) =>
    api.get(`/review/records/${contentId}`).then(r => r.data),
}

export const publishApi = {
  submit: (data: Record<string, unknown>) =>
    api.post('/publish/submit', data).then(r => r.data),
  listTasks: () => api.get('/publish/tasks').then(r => r.data),
  retract: (taskId: string) =>
    api.post(`/publish/${taskId}/retract`).then(r => r.data),
}

export const aigcApi = {
  generateArticle: (data: Record<string, unknown>) =>
    api.post('/aigc/article', data).then(r => r.data),
  optimizeTitles: (data: Record<string, unknown>) =>
    api.post('/aigc/titles', data).then(r => r.data),
  generateScript: (data: Record<string, unknown>) =>
    api.post('/aigc/script', data).then(r => r.data),
}

export default api

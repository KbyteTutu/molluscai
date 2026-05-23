import axios from 'axios'
import { toast } from 'vue-sonner'
import { useAuthStore } from '@/stores/auth'

const apiClient = axios.create({
  baseURL: '/api/v1',
  headers: { 'Content-Type': 'application/json' }
})

apiClient.interceptors.request.use(
  (config) => {
    const authStore = useAuthStore()
    if (authStore.token) config.headers.Authorization = `Bearer ${authStore.token}`
    return config
  },
  (error) => Promise.reject(error)
)

let isRefreshing = false
let failedQueue = []

function processQueue(error, token = null) {
  failedQueue.forEach(({ resolve, reject }) => (error ? reject(error) : resolve(token)))
  failedQueue = []
}

function formatQuotaToast(detail) {
  if (!detail || typeof detail !== 'object') return '请求过于频繁，请稍后再试'
  const typeLabel = { ai: '智能检索', auction: '拍卖检索', taxa: '物种检索' }[detail.query_type] || detail.query_type || '查询'
  const windowLabel = detail.window === 'hourly' ? '本小时' : detail.window === 'daily' ? '今日' : '当前'
  const mins = Math.max(1, Math.round((detail.retry_after_seconds || 60) / 60))
  return `${typeLabel}${windowLabel}配额已用尽（${detail.used}/${detail.limit}），约 ${mins} 分钟后重置`
}

apiClient.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config
    const status = error.response?.status

    if (status === 429) {
      const detail = error.response?.data?.detail
      const friendly = formatQuotaToast(detail)
      toast.error(friendly)
      if (error.response?.data) error.response.data.detail = friendly
      try {
        const authStore = useAuthStore()
        if (authStore.isAuthenticated) authStore.refreshQuota?.()
      } catch (_) {}
      return Promise.reject(error)
    }

    if (status === 401 && !originalRequest._retry) {
      if (isRefreshing) {
        return new Promise((resolve, reject) => failedQueue.push({ resolve, reject }))
          .then((token) => {
            originalRequest.headers.Authorization = `Bearer ${token}`
            return apiClient(originalRequest)
          })
          .catch((err) => Promise.reject(err))
      }
      originalRequest._retry = true
      isRefreshing = true
      try {
        const authStore = useAuthStore()
        const newToken = await authStore.refreshAccessToken()
        processQueue(null, newToken)
        originalRequest.headers.Authorization = `Bearer ${newToken}`
        return apiClient(originalRequest)
      } catch (refreshError) {
        processQueue(refreshError, null)
        const authStore = useAuthStore()
        authStore.logout()
        window.location.href = '/login'
        return Promise.reject(refreshError)
      } finally {
        isRefreshing = false
      }
    }
    return Promise.reject(error)
  }
)

export const authApi = {
  login: (data) => apiClient.post('/auth/login', data),
  register: (data) => apiClient.post('/auth/register', data),
  refresh: (data) => apiClient.post('/auth/refresh', data),
  me: () => apiClient.get('/auth/me'),
  changePassword: (data) => apiClient.post('/auth/change-password', data),
}

export const auctionApi = {
  search: (params) => apiClient.post('/auction/search', params),
  recent: () => apiClient.get('/auction/recent'),
  getDetail: (itemNo) => apiClient.get(`/auction/${itemNo}`),
  taxonMatch: (itemNo) => apiClient.get(`/auction/${itemNo}/taxon-match`),
  families: (q = '') => apiClient.get('/auction/families', { params: { q } })
}

export const taxaApi = {
  search: (params) => apiClient.get('/taxa/search', { params }),
  getDetail: (aphiaId) => apiClient.get(`/taxa/${aphiaId}`),
  getSynonyms: (aphiaId) => apiClient.get(`/taxa/${aphiaId}/synonyms`),
  getVernaculars: (aphiaId) => apiClient.get(`/taxa/${aphiaId}/vernaculars`),
  getDistributions: (aphiaId) => apiClient.get(`/taxa/${aphiaId}/distributions`),
  getChildren: (aphiaId, params) => apiClient.get(`/taxa/${aphiaId}/children`, { params }),
  getClassification: (aphiaId) => apiClient.get(`/taxa/${aphiaId}/classification`),
  getExternalIds: (aphiaId) => apiClient.get(`/taxa/${aphiaId}/external-ids`),
  rankNamesZh: () => apiClient.get('/taxa/rank-names-zh'),
}

export const adminApi = {
  runScraper: (data) => apiClient.post('/admin/scraper/run', data),
  downloadImages: (data) => apiClient.post('/admin/scraper/download-images', data),
  scraperStats: () => apiClient.get('/admin/scraper/stats'),
  listTasks: (limit = 50) => apiClient.get('/admin/tasks', { params: { limit } }),
  getTask: (id) => apiClient.get(`/admin/tasks/${id}`),
  revokeTask: (id) => apiClient.post(`/admin/tasks/${id}/revoke`),
  runEmbed: (data) => apiClient.post('/admin/embed/run', data),
  cancelEmbed: () => apiClient.post('/admin/embed/cancel'),
  runAuctionEmbed: (data) => apiClient.post('/admin/embed/auction/run', data),
  cancelAuctionEmbed: () => apiClient.post('/admin/embed/auction/cancel'),
  listModels: (params) => apiClient.get('/admin/models', { params }),
  createModel: (data) => apiClient.post('/admin/models', data),
  updateModel: (id, data) => apiClient.patch(`/admin/models/${id}`, data),
  deleteModel: (id) => apiClient.delete(`/admin/models/${id}`),
  testModel: (id) => apiClient.post(`/admin/models/${id}/test`),
  usageSummary: (days = 30) => apiClient.get('/admin/models/usage/summary', { params: { days } }),
  usageRecent: (limit = 50) => apiClient.get('/admin/models/usage/recent', { params: { limit } }),
  embeddingsStatus: () => apiClient.get('/admin/models/embeddings/status'),
  auctionEmbeddingsStatus: () => apiClient.get('/admin/models/auction-embeddings/status'),
  listQuotas: () => apiClient.get('/admin/quotas'),
  updateQuota: (role, data) => apiClient.patch(`/admin/quotas/${role}`, data),
  queryStats: (days = 7) => apiClient.get('/admin/queries/stats', { params: { days } }),
  recentQueries: (limit = 100, q = '') => apiClient.get('/admin/queries/recent', { params: { limit, q } }),
  listUsers: (params) => apiClient.get('/admin/users', { params }),
  updateUser: (id, data) => apiClient.patch(`/admin/users/${id}`, data),
  resetUserPassword: (id, newPassword) => apiClient.post(`/admin/users/${id}/reset-password`, { new_password: newPassword }),
  listFeedbacks: (params) => apiClient.get('/admin/feedbacks', { params }),
  updateFeedback: (id, data) => apiClient.patch(`/admin/feedbacks/${id}`, data)
}

export const userApi = {
  myQuota: () => apiClient.get('/users/me/quota')
}

export const feedbackApi = {
  create: (data) => apiClient.post('/feedback', data),
  mine: (params) => apiClient.get('/feedback/me', { params })
}

export default apiClient

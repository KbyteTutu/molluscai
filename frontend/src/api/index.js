import axios from 'axios'
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

apiClient.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config
    if (error.response?.status === 401 && !originalRequest._retry) {
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
  me: () => apiClient.get('/auth/me')
}

export const auctionApi = {
  search: (params) => apiClient.post('/auction/search', params),
  getDetail: (itemNo) => apiClient.get(`/auction/${itemNo}`),
  taxonMatch: (itemNo) => apiClient.get(`/auction/${itemNo}/taxon-match`)
}

export const taxaApi = {
  search: (params) => apiClient.get('/taxa/search', { params }),
  getDetail: (aphiaId) => apiClient.get(`/taxa/${aphiaId}`)
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
  listModels: (params) => apiClient.get('/admin/models', { params }),
  createModel: (data) => apiClient.post('/admin/models', data),
  updateModel: (id, data) => apiClient.patch(`/admin/models/${id}`, data),
  deleteModel: (id) => apiClient.delete(`/admin/models/${id}`),
  testModel: (id) => apiClient.post(`/admin/models/${id}/test`),
  usageSummary: (days = 30) => apiClient.get('/admin/models/usage/summary', { params: { days } }),
  usageRecent: (limit = 50) => apiClient.get('/admin/models/usage/recent', { params: { limit } }),
  embeddingsStatus: () => apiClient.get('/admin/models/embeddings/status')
}

export default apiClient

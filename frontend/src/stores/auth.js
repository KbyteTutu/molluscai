import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { authApi, userApi } from '@/api'

export const useAuthStore = defineStore('auth', () => {
  const token = ref(localStorage.getItem('access_token') || null)
  const refreshToken = ref(localStorage.getItem('refresh_token') || null)
  const user = ref(JSON.parse(localStorage.getItem('user') || 'null'))
  const quota = ref(null)

  const now = ref(Date.now())
  setInterval(() => { now.value = Date.now() }, 30000)

  function base64UrlDecode(str) {
    let base64 = str.replace(/-/g, '+').replace(/_/g, '/')
    while (base64.length % 4) base64 += '='
    return atob(base64)
  }

  function isTokenExpired(token) {
    if (!token) return true
    try {
      const payload = JSON.parse(base64UrlDecode(token.split('.')[1]))
      return payload.exp * 1000 < now.value
    } catch {
      return true
    }
  }
  const isAuthenticated = computed(() => !!token.value && !isTokenExpired(token.value))
  const currentUser = computed(() => user.value)
  const isSuperadmin = computed(() => user.value?.role === 'superadmin')

  function persistTokens() {
    if (token.value) {
      localStorage.setItem('access_token', token.value)
    } else {
      localStorage.removeItem('access_token')
    }
    if (refreshToken.value) {
      localStorage.setItem('refresh_token', refreshToken.value)
    } else {
      localStorage.removeItem('refresh_token')
    }
    if (user.value) {
      localStorage.setItem('user', JSON.stringify(user.value))
    } else {
      localStorage.removeItem('user')
    }
  }

  async function refreshQuota() {
    if (!token.value) {
      quota.value = null
      return null
    }
    try {
      const response = await userApi.myQuota()
      quota.value = response.data
      return response.data
    } catch (e) {
      return null
    }
  }

  async function login(username, password) {
    const response = await authApi.login({ username, password })
    token.value = response.data.access_token
    refreshToken.value = response.data.refresh_token
    user.value = response.data.user
    persistTokens()
    refreshQuota()
  }

  async function register(username, email, password) {
    const response = await authApi.register({ username, email, password })
    token.value = response.data.access_token
    refreshToken.value = response.data.refresh_token
    user.value = response.data.user
    persistTokens()
    refreshQuota()
  }

  async function refreshAccessToken() {
    if (!refreshToken.value) {
      throw new Error('No refresh token available')
    }
    const response = await authApi.refresh({ refresh_token: refreshToken.value })
    token.value = response.data.access_token
    refreshToken.value = response.data.refresh_token
    persistTokens()
    return response.data.access_token
  }

  function logout() {
    token.value = null
    refreshToken.value = null
    user.value = null
    quota.value = null
    persistTokens()
  }

  return {
    token,
    refreshToken,
    user,
    quota,
    isAuthenticated,
    currentUser,
    isSuperadmin,
    login,
    register,
    refreshAccessToken,
    refreshQuota,
    logout
  }
})

import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { authApi } from '@/api'

export const useAuthStore = defineStore('auth', () => {
  const token = ref(localStorage.getItem('access_token') || null)
  const refreshToken = ref(localStorage.getItem('refresh_token') || null)
  const user = ref(JSON.parse(localStorage.getItem('user') || 'null'))

  const isAuthenticated = computed(() => !!token.value)
  const currentUser = computed(() => user.value)

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

  async function login(username, password) {
    const response = await authApi.login({ username, password })
    token.value = response.data.access_token
    refreshToken.value = response.data.refresh_token
    user.value = response.data.user
    persistTokens()
  }

  async function register(username, email, password) {
    const response = await authApi.register({ username, email, password })
    token.value = response.data.access_token
    refreshToken.value = response.data.refresh_token
    user.value = response.data.user
    persistTokens()
  }

  async function refreshAccessToken() {
    if (!refreshToken.value) {
      throw new Error('No refresh token available')
    }
    const response = await authApi.refresh({ refresh_token: refreshToken.value })
    token.value = response.data.access_token
    refreshToken.value = response.data.refresh_token || response.data.refresh_token
    persistTokens()
    return response.data.access_token
  }

  function logout() {
    token.value = null
    refreshToken.value = null
    user.value = null
    persistTokens()
  }

  return {
    token,
    refreshToken,
    user,
    isAuthenticated,
    currentUser,
    login,
    register,
    refreshAccessToken,
    logout
  }
})

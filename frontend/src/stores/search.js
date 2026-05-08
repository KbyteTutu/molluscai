import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { auctionApi } from '@/api'

export const useSearchStore = defineStore('search', () => {
  const results = ref([])
  const loading = ref(false)
  const error = ref(null)
  const total = ref(0)
  const currentPage = ref(1)
  const pageSize = ref(50)

  const hasResults = computed(() => results.value.length > 0)

  async function searchAuctions(params) {
    loading.value = true
    error.value = null
    try {
      const response = await auctionApi.search(params)
      results.value = response.data.items || []
      total.value = response.data.total || 0
    } catch (err) {
      error.value = err.response?.data?.detail || err.message || '搜索失败'
      results.value = []
      total.value = 0
    } finally {
      loading.value = false
    }
  }

  function clearResults() {
    results.value = []
    error.value = null
    total.value = 0
    currentPage.value = 1
  }

  return {
    results,
    loading,
    error,
    total,
    currentPage,
    pageSize,
    hasResults,
    searchAuctions,
    clearResults
  }
})

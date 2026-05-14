import { defineStore } from 'pinia'
import { ref } from 'vue'
import { auctionApi } from '@/api'

export const useTaxonMatchStore = defineStore('taxonMatch', () => {
  const cache = ref(new Map())
  const loading = ref(new Set())
  const errors = ref(new Map())

  function get(itemNo) {
    return cache.value.get(itemNo) || null
  }

  function isLoading(itemNo) {
    return loading.value.has(itemNo)
  }

  function getError(itemNo) {
    return errors.value.get(itemNo) || null
  }

  async function fetch(itemNo, { force = false } = {}) {
    if (!force && cache.value.has(itemNo)) return cache.value.get(itemNo)
    if (loading.value.has(itemNo)) return null
    loading.value.add(itemNo)
    errors.value.delete(itemNo)
    try {
      const { data } = await auctionApi.taxonMatch(itemNo)
      cache.value.set(itemNo, data)
      return data
    } catch (e) {
      const msg = e.response?.data?.detail || e.message || '匹配失败'
      errors.value.set(itemNo, msg)
      throw e
    } finally {
      loading.value.delete(itemNo)
    }
  }

  function clear(itemNo) {
    if (itemNo === undefined) {
      cache.value.clear()
      loading.value.clear()
      errors.value.clear()
    } else {
      cache.value.delete(itemNo)
      loading.value.delete(itemNo)
      errors.value.delete(itemNo)
    }
  }

  return { get, isLoading, getError, fetch, clear }
})

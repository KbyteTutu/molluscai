import { defineStore } from 'pinia'
import { ref, computed } from 'vue'

const STORAGE_KEY = 'malaco-compare'
const MAX_ITEMS = 6

function loadInitial() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    if (!raw) return []
    const parsed = JSON.parse(raw)
    return Array.isArray(parsed) ? parsed.slice(0, MAX_ITEMS) : []
  } catch {
    return []
  }
}

export const useCompareStore = defineStore('compare', () => {
  const items = ref(loadInitial())

  function persist() {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(items.value))
    } catch {}
  }

  const count = computed(() => items.value.length)
  const isFull = computed(() => items.value.length >= MAX_ITEMS)

  function has(itemNo) {
    return items.value.some((it) => it.item_no === itemNo)
  }

  function add(item) {
    if (!item || !item.item_no) return false
    if (has(item.item_no)) return true
    if (isFull.value) return false
    items.value = [...items.value, { ...item }]
    persist()
    return true
  }

  function remove(itemNo) {
    items.value = items.value.filter((it) => it.item_no !== itemNo)
    persist()
  }

  function toggle(item) {
    if (has(item.item_no)) {
      remove(item.item_no)
      return false
    }
    return add(item)
  }

  function clear() {
    items.value = []
    persist()
  }

  return { items, count, isFull, has, add, remove, toggle, clear, MAX_ITEMS }
})

export { MAX_ITEMS }

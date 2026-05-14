<script setup>
import { computed } from 'vue'
import { Check, Plus } from 'lucide-vue-next'
import { useCompareStore } from '@/stores/compare'
import { cn } from '@/lib/utils'
import { toast } from 'vue-sonner'

const props = defineProps({
  item: { type: Object, required: true },
  class: { type: null, default: '' }
})

const store = useCompareStore()
const active = computed(() => store.has(props.item.item_no))

function onClick(e) {
  e.stopPropagation()
  e.preventDefault()
  if (active.value) {
    store.remove(props.item.item_no)
    return
  }
  const ok = store.add(props.item)
  if (!ok) toast.error(`对比列表已满（最多 ${store.MAX_ITEMS} 项）`)
}
</script>

<template>
  <button
    type="button"
    :aria-pressed="active"
    :aria-label="active ? '从对比移除' : '加入对比'"
    :title="active ? '从对比移除' : '加入对比'"
    :class="cn(
      'inline-flex items-center justify-center size-7 rounded-md border transition-colors',
      active
        ? 'bg-primary text-primary-foreground border-primary'
        : 'bg-background/90 backdrop-blur border-border text-muted-foreground hover:text-foreground hover:border-foreground/40',
      props.class
    )"
    @click="onClick"
  >
    <Check v-if="active" class="size-4" />
    <Plus v-else class="size-4" />
  </button>
</template>

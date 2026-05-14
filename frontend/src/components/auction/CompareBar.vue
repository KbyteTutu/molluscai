<script setup>
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import { GitCompareArrows, X } from 'lucide-vue-next'
import { useCompareStore } from '@/stores/compare'
import Button from '@/components/ui/Button.vue'

const store = useCompareStore()
const route = useRoute()
const hidden = computed(() => route.name === 'Compare' || route.name === 'Login')
</script>

<template>
  <div
    v-if="store.count > 0 && !hidden"
    class="fixed bottom-4 left-1/2 -translate-x-1/2 z-40 w-[calc(100%-2rem)] max-w-xl"
  >
    <div class="flex items-center gap-3 rounded-full border bg-background/95 shadow-lg backdrop-blur px-4 py-2">
      <GitCompareArrows class="size-4 text-primary shrink-0" />
      <span class="text-sm">
        对比列表
        <span class="font-mono tabular-nums text-muted-foreground ml-1">{{ store.count }} / {{ store.MAX_ITEMS }}</span>
      </span>

      <div class="flex items-center gap-1 flex-1 overflow-x-auto scrollbar-none">
        <span
          v-for="it in store.items"
          :key="it.item_no"
          class="shrink-0 inline-flex items-center gap-1 rounded-full bg-secondary px-2 py-0.5 text-[11px] font-mono"
        >
          #{{ it.item_no }}
          <button
            type="button"
            class="text-muted-foreground hover:text-destructive"
            :aria-label="`移除 ${it.item_no}`"
            @click="store.remove(it.item_no)"
          >
            <X class="size-3" />
          </button>
        </span>
      </div>

      <Button variant="ghost" size="sm" class="shrink-0" @click="store.clear">清空</Button>
      <router-link to="/compare">
        <Button size="sm" class="shrink-0" :disabled="store.count < 2">对比 →</Button>
      </router-link>
    </div>
  </div>
</template>

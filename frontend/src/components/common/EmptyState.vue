<script setup>
import ShellLogo from '@/components/brand/ShellLogo.vue'

defineProps({
  title: { type: String, default: '未找到匹配记录' },
  description: { type: String, default: '试试调整筛选条件' }
})
</script>

<template>
  <div class="flex flex-col items-center justify-center py-16 text-center">
    <ShellLogo :size="56" class="text-muted-foreground/40 mb-4" />
    <p class="font-serif text-lg text-foreground/80">{{ title }}</p>
    <p class="mt-1.5 text-sm text-muted-foreground">{{ description }}</p>
    <slot />
  </div>
</template>

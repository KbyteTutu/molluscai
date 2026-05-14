<script setup>
import { computed } from 'vue'
import { cn } from '@/lib/utils'
const props = defineProps({ class: { type: null, default: '' } })
const klass = computed(() => cn('relative w-full overflow-auto', props.class))
</script>
<template>
  <div :class="klass">
    <table class="w-full caption-bottom text-sm">
      <slot />
    </table>
  </div>
</template>

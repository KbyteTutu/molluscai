<script setup>
import { computed } from 'vue'
import { cn } from '@/lib/utils'
const props = defineProps({ orientation: { type: String, default: 'horizontal' }, class: { type: null, default: '' } })
const klass = computed(() =>
  cn('shrink-0 bg-border', props.orientation === 'horizontal' ? 'h-px w-full' : 'h-full w-px', props.class)
)
</script>
<template><div :class="klass" role="separator" /></template>

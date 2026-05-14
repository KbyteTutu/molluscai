<script setup>
import { computed } from 'vue'
import { cn } from '@/lib/utils'
const props = defineProps({ class: { type: null, default: '' } })
const klass = computed(() => cn('relative flex h-10 w-10 shrink-0 overflow-hidden rounded-full bg-muted items-center justify-center', props.class))
</script>
<template><span :class="klass"><slot /></span></template>

<script setup>
import { computed } from 'vue'
import { cn } from '@/lib/utils'
const props = defineProps({ class: { type: null, default: '' } })
const klass = computed(() => cn('h-10 px-3 text-left align-middle text-xs font-medium text-muted-foreground uppercase tracking-wider [&:has([role=checkbox])]:pr-0', props.class))
</script>
<template><th :class="klass"><slot /></th></template>

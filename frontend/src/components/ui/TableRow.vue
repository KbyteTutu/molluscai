<script setup>
import { computed } from 'vue'
import { cn } from '@/lib/utils'
const props = defineProps({ class: { type: null, default: '' } })
const klass = computed(() => cn('border-b transition-colors hover:bg-muted/50 data-[state=selected]:bg-muted', props.class))
</script>
<template><tr :class="klass"><slot /></tr></template>

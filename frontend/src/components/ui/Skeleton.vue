<script setup>
import { computed } from 'vue'
import { cn } from '@/lib/utils'
const props = defineProps({ class: { type: null, default: '' } })
const klass = computed(() => cn('animate-pulse rounded-md bg-muted', props.class))
</script>
<template><div :class="klass" /></template>

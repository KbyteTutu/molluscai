<script setup>
import { computed } from 'vue'
import { cn } from '@/lib/utils'
const props = defineProps({ class: { type: null, default: '' } })
const klass = computed(() => cn('font-serif text-2xl font-semibold leading-none tracking-tight', props.class))
</script>
<template><h3 :class="klass"><slot /></h3></template>

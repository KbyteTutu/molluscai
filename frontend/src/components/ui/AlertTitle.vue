<script setup>
import { computed } from 'vue'
import { cn } from '@/lib/utils'
const props = defineProps({ class: { type: null, default: '' } })
const klass = computed(() => cn('mb-1 font-medium leading-none tracking-tight', props.class))
</script>
<template><h5 :class="klass"><slot /></h5></template>

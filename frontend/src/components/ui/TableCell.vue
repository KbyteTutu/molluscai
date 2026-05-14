<script setup>
import { computed } from 'vue'
import { cn } from '@/lib/utils'
const props = defineProps({ class: { type: null, default: '' } })
const klass = computed(() => cn('px-3 py-3 align-middle [&:has([role=checkbox])]:pr-0', props.class))
</script>
<template><td :class="klass"><slot /></td></template>

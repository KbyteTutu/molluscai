<script setup>
import { computed } from 'vue'
import { cn } from '@/lib/utils'
const props = defineProps({ class: { type: null, default: '' } })
const klass = computed(() => cn('flex items-center p-6 pt-0', props.class))
</script>
<template><div :class="klass"><slot /></div></template>

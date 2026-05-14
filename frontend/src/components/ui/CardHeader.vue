<script setup>
import { computed } from 'vue'
import { cn } from '@/lib/utils'
const props = defineProps({ class: { type: null, default: '' } })
const klass = computed(() => cn('flex flex-col space-y-1.5 p-6', props.class))
</script>
<template><div :class="klass"><slot /></div></template>

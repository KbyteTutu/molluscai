<script setup>
import { computed } from 'vue'
import { cn } from '@/lib/utils'
const props = defineProps({ class: { type: null, default: '' } })
const klass = computed(() => cn('text-sm [&_p]:leading-relaxed', props.class))
</script>
<template><div :class="klass"><slot /></div></template>

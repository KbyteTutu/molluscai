<script setup>
import { computed } from 'vue'
import { cn } from '@/lib/utils'
const props = defineProps({ class: { type: null, default: '' } })
const klass = computed(() => cn('text-sm text-muted-foreground', props.class))
</script>
<template><p :class="klass"><slot /></p></template>

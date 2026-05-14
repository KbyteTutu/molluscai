<script setup>
import { computed } from 'vue'
import { cn } from '@/lib/utils'
const props = defineProps({ class: { type: null, default: '' } })
const klass = computed(() => cn('rounded-lg border bg-card text-card-foreground shadow-sm', props.class))
</script>
<template><div :class="klass"><slot /></div></template>

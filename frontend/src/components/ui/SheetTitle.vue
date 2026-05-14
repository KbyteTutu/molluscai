<script setup>
import { DialogTitle } from 'reka-ui'
import { computed } from 'vue'
import { cn } from '@/lib/utils'
const props = defineProps({ class: { type: null, default: '' } })
const klass = computed(() => cn('font-serif text-2xl font-semibold leading-tight tracking-tight text-foreground', props.class))
</script>
<template><DialogTitle :class="klass"><slot /></DialogTitle></template>

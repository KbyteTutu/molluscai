<script setup>
import { DialogDescription } from 'reka-ui'
import { computed } from 'vue'
import { cn } from '@/lib/utils'
const props = defineProps({ class: { type: null, default: '' } })
const klass = computed(() => cn('text-sm text-muted-foreground', props.class))
</script>
<template><DialogDescription :class="klass"><slot /></DialogDescription></template>

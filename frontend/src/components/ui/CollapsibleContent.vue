<script setup>
import { CollapsibleContent } from 'reka-ui'
import { computed } from 'vue'
import { cn } from '@/lib/utils'
const props = defineProps({ class: { type: null, default: '' } })
const klass = computed(() => cn('overflow-hidden data-[state=closed]:animate-collapsible-up data-[state=open]:animate-collapsible-down', props.class))
</script>
<template><CollapsibleContent :class="klass"><slot /></CollapsibleContent></template>

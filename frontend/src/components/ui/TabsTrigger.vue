<script setup>
import { TabsTrigger } from 'reka-ui'
import { computed } from 'vue'
import { cn } from '@/lib/utils'
const props = defineProps({ value: { type: String, required: true }, class: { type: null, default: '' } })
const klass = computed(() => cn('inline-flex items-center justify-center whitespace-nowrap rounded-md px-3 py-1 text-sm font-medium ring-offset-background transition-all focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50 data-[state=active]:bg-background data-[state=active]:text-foreground data-[state=active]:shadow', props.class))
</script>
<template><TabsTrigger :value="value" :class="klass"><slot /></TabsTrigger></template>

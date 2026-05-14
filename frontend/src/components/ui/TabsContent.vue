<script setup>
import { TabsContent } from 'reka-ui'
import { computed } from 'vue'
import { cn } from '@/lib/utils'
const props = defineProps({ value: { type: String, required: true }, class: { type: null, default: '' } })
const klass = computed(() => cn('mt-2 ring-offset-background focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2', props.class))
</script>
<template><TabsContent :value="value" :class="klass"><slot /></TabsContent></template>

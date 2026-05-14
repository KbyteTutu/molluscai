<script setup>
import { computed } from 'vue'
import { Label as LabelPrimitive } from 'reka-ui'
import { cn } from '@/lib/utils'

const props = defineProps({ class: { type: null, default: '' }, for: { type: String, default: undefined } })
const klass = computed(() => cn('text-sm font-medium leading-none peer-disabled:cursor-not-allowed peer-disabled:opacity-70', props.class))
</script>

<template>
  <LabelPrimitive :for="for" :class="klass"><slot /></LabelPrimitive>
</template>

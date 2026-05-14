<script setup>
import { computed } from 'vue'
import { cn } from '@/lib/utils'
const props = defineProps({
  variant: { type: String, default: 'default' },
  class: { type: null, default: '' }
})
const klass = computed(() =>
  cn(
    'relative w-full rounded-lg border p-4 [&>svg~*]:pl-7 [&>svg+div]:translate-y-[-3px] [&>svg]:absolute [&>svg]:left-4 [&>svg]:top-4 [&>svg]:text-foreground',
    props.variant === 'destructive' && 'border-destructive/50 text-destructive [&>svg]:text-destructive bg-destructive/5',
    props.class
  )
)
</script>
<template><div role="alert" :class="klass"><slot /></div></template>

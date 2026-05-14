<script setup>
import { computed, useAttrs } from 'vue'
import { cn } from '@/lib/utils'

const props = defineProps({
  modelValue: { type: [String, Number], default: '' },
  class: { type: null, default: '' }
})
const emit = defineEmits(['update:modelValue'])
defineOptions({ inheritAttrs: false })
const attrs = useAttrs()

const klass = computed(() =>
  cn(
    'flex h-9 w-full rounded-md border border-input bg-transparent px-3 py-1 text-sm shadow-sm transition-colors file:border-0 file:bg-transparent file:text-sm file:font-medium placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background disabled:cursor-not-allowed disabled:opacity-50',
    props.class
  )
)
</script>

<template>
  <input
    :class="klass"
    :value="modelValue"
    v-bind="attrs"
    @input="emit('update:modelValue', $event.target.value)"
  />
</template>

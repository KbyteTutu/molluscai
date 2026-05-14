<script setup>
import { DropdownMenuItem } from 'reka-ui'
import { computed } from 'vue'
import { cn } from '@/lib/utils'
const props = defineProps({ class: { type: null, default: '' }, disabled: { type: Boolean, default: false } })
const emit = defineEmits(['select'])
const klass = computed(() =>
  cn(
    'relative flex cursor-default select-none items-center rounded-sm px-2 py-1.5 text-sm outline-none transition-colors gap-2 focus:bg-accent focus:text-accent-foreground data-[disabled]:pointer-events-none data-[disabled]:opacity-50',
    props.class
  )
)
</script>
<template>
  <DropdownMenuItem :class="klass" :disabled="disabled" @select="emit('select', $event)">
    <slot />
  </DropdownMenuItem>
</template>

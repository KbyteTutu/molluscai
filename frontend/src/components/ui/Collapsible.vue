<script setup>
import { CollapsibleRoot } from 'reka-ui'
const props = defineProps({ open: { type: Boolean, default: undefined }, defaultOpen: { type: Boolean, default: undefined } })
const emit = defineEmits(['update:open'])
</script>
<template>
  <CollapsibleRoot :open="open" :default-open="defaultOpen" @update:open="emit('update:open', $event)">
    <slot />
  </CollapsibleRoot>
</template>

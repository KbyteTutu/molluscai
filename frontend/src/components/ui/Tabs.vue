<script setup>
import { TabsRoot } from 'reka-ui'
import { computed } from 'vue'
import { cn } from '@/lib/utils'

const props = defineProps({
  modelValue: { type: String, default: undefined },
  defaultValue: { type: String, default: undefined },
  class: { type: null, default: '' }
})
const emit = defineEmits(['update:modelValue'])
const klass = computed(() => cn('', props.class))
</script>
<template>
  <TabsRoot
    :model-value="modelValue"
    :default-value="defaultValue"
    :class="klass"
    @update:model-value="emit('update:modelValue', $event)"
  >
    <slot />
  </TabsRoot>
</template>

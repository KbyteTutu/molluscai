<script setup>
import { DropdownMenuPortal, DropdownMenuContent } from 'reka-ui'
import { computed } from 'vue'
import { cn } from '@/lib/utils'
const props = defineProps({
  align: { type: String, default: 'end' },
  sideOffset: { type: Number, default: 4 },
  class: { type: null, default: '' }
})
const klass = computed(() =>
  cn(
    'z-50 min-w-[10rem] overflow-hidden rounded-md border bg-popover p-1 text-popover-foreground shadow-md data-[state=open]:animate-in data-[state=closed]:animate-out data-[state=closed]:fade-out-0 data-[state=open]:fade-in-0 data-[state=closed]:zoom-out-95 data-[state=open]:zoom-in-95',
    props.class
  )
)
</script>
<template>
  <DropdownMenuPortal>
    <DropdownMenuContent :align="align" :side-offset="sideOffset" :class="klass">
      <slot />
    </DropdownMenuContent>
  </DropdownMenuPortal>
</template>

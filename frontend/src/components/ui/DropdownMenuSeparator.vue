<script setup>
import { DropdownMenuSeparator } from 'reka-ui'
import { computed } from 'vue'
import { cn } from '@/lib/utils'
const props = defineProps({ class: { type: null, default: '' } })
const klass = computed(() => cn('-mx-1 my-1 h-px bg-muted', props.class))
</script>
<template><DropdownMenuSeparator :class="klass" /></template>

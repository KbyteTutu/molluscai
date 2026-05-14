<script setup>
import { computed } from 'vue'
import { cn } from '@/lib/utils'
const props = defineProps({ class: { type: null, default: '' } })
const klass = computed(() => cn('[&_tr:last-child]:border-0', props.class))
</script>
<template><tbody :class="klass"><slot /></tbody></template>

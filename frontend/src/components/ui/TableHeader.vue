<script setup>
import { computed } from 'vue'
import { cn } from '@/lib/utils'
const props = defineProps({ class: { type: null, default: '' } })
const klass = computed(() => cn('[&_tr]:border-b', props.class))
</script>
<template><thead :class="klass"><slot /></thead></template>

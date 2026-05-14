<script setup>
const props = defineProps({
  name: { type: String, default: '' },
  italic: { type: Boolean, default: true }
})
</script>

<template>
  <span class="font-serif" :class="italic ? 'italic' : ''">{{ name }}</span>
</template>

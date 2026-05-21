<script setup>
const props = defineProps({
  size: { type: Number, default: 24 },
  class: { type: String, default: '' }
})
</script>

<template>
  <img
    src="/logo.png"
    :width="size"
    :height="size"
    :style="{ width: size + 'px', height: size + 'px' }"
    :class="['object-contain shrink-0 select-none', props.class]"
    alt="MolluscAI"
    draggable="false"
  />
</template>

<script setup>
const props = defineProps({
  size: { type: Number, default: 24 },
  class: { type: String, default: '' }
})
</script>

<template>
  <!-- Placeholder logo: logarithmic-spiral shell mark, single stroke, currentColor. Replace later. -->
  <svg
    :width="size"
    :height="size"
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    stroke-width="1.4"
    stroke-linecap="round"
    stroke-linejoin="round"
    :class="props.class"
    aria-hidden="true"
  >
    <path d="M12 21c-4.97 0-9-4.03-9-9s4.03-9 9-9 9 4.03 9 9" />
    <path d="M12 17.5c-3.04 0-5.5-2.46-5.5-5.5S8.96 6.5 12 6.5 17.5 8.96 17.5 12" />
    <path d="M12 14.5c-1.38 0-2.5-1.12-2.5-2.5s1.12-2.5 2.5-2.5 2.5 1.12 2.5 2.5" />
    <path d="M12 12 L21 12" stroke-opacity="0.3" />
  </svg>
</template>

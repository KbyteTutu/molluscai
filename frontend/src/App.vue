<script setup>
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import AppShell from '@/components/layout/AppShell.vue'
import Sonner from '@/components/ui/Sonner.vue'

const route = useRoute()
const isAuthLayout = computed(() => route.meta.requiresGuest)
</script>

<template>
  <Sonner />
  <router-view v-if="isAuthLayout" />
  <AppShell v-else />
</template>

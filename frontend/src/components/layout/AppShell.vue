<script setup>
import { ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import AppSidebar from '@/components/layout/AppSidebar.vue'
import Sheet from '@/components/ui/Sheet.vue'
import SheetContent from '@/components/ui/SheetContent.vue'
import Button from '@/components/ui/Button.vue'
import { Menu } from 'lucide-vue-next'
import ShellLogo from '@/components/brand/ShellLogo.vue'
import CompareBar from '@/components/auction/CompareBar.vue'

const mobileOpen = ref(false)
const route = useRoute()
watch(() => route.fullPath, () => { mobileOpen.value = false })
</script>

<template>
  <div class="flex min-h-screen bg-background text-foreground">
    <div class="hidden md:block sticky top-0 h-screen shrink-0">
      <AppSidebar />
    </div>

    <Sheet v-model:open="mobileOpen">
      <SheetContent side="left" class="p-0 w-64 sm:max-w-none">
        <AppSidebar />
      </SheetContent>
    </Sheet>

    <div class="flex-1 min-w-0 flex flex-col">
      <header class="md:hidden sticky top-0 z-30 flex items-center gap-3 border-b bg-background/95 px-4 py-3 backdrop-blur supports-[backdrop-filter]:bg-background/80">
        <Button variant="ghost" size="icon" aria-label="打开菜单" @click="mobileOpen = true">
          <Menu class="size-5" />
        </Button>
        <div class="flex items-center gap-2">
          <ShellLogo :size="20" class="text-primary" />
          <span class="font-serif text-base font-semibold tracking-tight">MolluscAI</span>
        </div>
      </header>

      <main class="flex-1 min-w-0">
        <div class="mx-auto w-full max-w-6xl px-4 sm:px-6 md:px-8 py-6 md:py-10 pb-24 md:pb-24">
          <router-view />
        </div>
      </main>
    </div>

    <CompareBar />
  </div>
</template>

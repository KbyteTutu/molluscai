<script setup>
import { useColorMode } from '@vueuse/core'
import { Sun, Moon, Monitor } from 'lucide-vue-next'
import Button from '@/components/ui/Button.vue'
import DropdownMenu from '@/components/ui/DropdownMenu.vue'
import DropdownMenuTrigger from '@/components/ui/DropdownMenuTrigger.vue'
import DropdownMenuContent from '@/components/ui/DropdownMenuContent.vue'
import DropdownMenuItem from '@/components/ui/DropdownMenuItem.vue'

const mode = useColorMode({
  storageKey: 'mollusc-theme',
  selector: 'html',
  attribute: 'class',
  modes: { light: '', dark: 'dark' }
})
</script>

<template>
  <DropdownMenu>
    <DropdownMenuTrigger>
      <Button variant="ghost" size="icon" aria-label="切换主题">
        <Sun v-if="mode === 'light'" />
        <Moon v-else-if="mode === 'dark'" />
        <Monitor v-else />
      </Button>
    </DropdownMenuTrigger>
    <DropdownMenuContent align="end">
      <DropdownMenuItem @select="mode = 'light'"><Sun class="size-4" />明亮</DropdownMenuItem>
      <DropdownMenuItem @select="mode = 'dark'"><Moon class="size-4" />深色</DropdownMenuItem>
      <DropdownMenuItem @select="mode = 'auto'"><Monitor class="size-4" />跟随系统</DropdownMenuItem>
    </DropdownMenuContent>
  </DropdownMenu>
</template>

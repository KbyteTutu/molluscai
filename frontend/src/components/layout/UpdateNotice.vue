<script setup>
import { onMounted, ref } from 'vue'
import { Bell, Dot } from 'lucide-vue-next'
import { publicApi } from '@/api'
import Button from '@/components/ui/Button.vue'
import Badge from '@/components/ui/Badge.vue'
import Sheet from '@/components/ui/Sheet.vue'
import SheetContent from '@/components/ui/SheetContent.vue'
import SheetHeader from '@/components/ui/SheetHeader.vue'
import SheetTitle from '@/components/ui/SheetTitle.vue'
import SheetDescription from '@/components/ui/SheetDescription.vue'
import Separator from '@/components/ui/Separator.vue'

const open = ref(false)

const fallbackUpdates = [
  { date: '2026-07-07', title: '匿名检索开放', text: '未登录也可使用拍卖与物种词法查询。' },
  { date: '2026-07-07', title: '匿名访问限流', text: '匿名搜索每分钟 20 次，登录后可继续使用。' },
  { date: '2026-07-07', title: '安全加固', text: '模型密钥加密存储，生产弱密钥会阻止启动。' }
]
const updates = ref(fallbackUpdates)

onMounted(async () => {
  try {
    const { data } = await publicApi.updateNotices()
    if (Array.isArray(data?.items) && data.items.length) {
      updates.value = data.items
    }
  } catch (_) {
    updates.value = fallbackUpdates
  }
})
</script>

<template>
  <div class="fixed bottom-4 left-4 z-40 print:hidden">
    <Button
      variant="outline"
      size="sm"
      class="h-8 gap-1.5 border-border/80 bg-background/90 px-2.5 text-[11px] shadow-sm backdrop-blur hover:bg-accent"
      aria-label="查看功能更新"
      @click="open = true"
    >
      <Bell class="size-3.5" />
      更新
      <span class="ml-0.5 h-1.5 w-1.5 rounded-full bg-primary" aria-hidden="true"></span>
    </Button>
  </div>

  <Sheet v-model:open="open">
    <SheetContent side="left" class="w-[22rem] max-w-[calc(100vw-2rem)] sm:max-w-sm">
      <SheetHeader>
        <div class="flex items-center gap-2">
          <SheetTitle class="text-xl">功能更新</SheetTitle>
          <Badge variant="secondary" class="text-[10px]">简讯</Badge>
        </div>
        <SheetDescription>仅列出最近重要变化。</SheetDescription>
      </SheetHeader>

      <Separator class="my-4" />

      <div class="space-y-4">
        <article v-for="item in updates" :key="`${item.date}-${item.title}`" class="space-y-1.5">
          <div class="flex items-center gap-2 text-[11px] text-muted-foreground">
            <Dot class="size-4 text-primary" />
            <time>{{ item.date }}</time>
          </div>
          <h3 class="text-sm font-medium leading-tight">{{ item.title }}</h3>
          <p class="text-xs leading-relaxed text-muted-foreground">{{ item.text }}</p>
        </article>
      </div>
    </SheetContent>
  </Sheet>
</template>

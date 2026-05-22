<script setup>
import { ref } from 'vue'
import { MessageSquarePlus, X } from 'lucide-vue-next'
import { feedbackApi } from '@/api'
import Button from '@/components/ui/Button.vue'
import Sheet from '@/components/ui/Sheet.vue'
import SheetContent from '@/components/ui/SheetContent.vue'
import SheetHeader from '@/components/ui/SheetHeader.vue'
import SheetTitle from '@/components/ui/SheetTitle.vue'
import SheetDescription from '@/components/ui/SheetDescription.vue'
import { toast } from 'vue-sonner'
import { cn } from '@/lib/utils'

const CATEGORIES = [
  { value: 'bug', label: '问题反馈' },
  { value: 'feature', label: '功能建议' },
  { value: 'other', label: '其他' }
]

const open = ref(false)
const category = ref('feature')
const content = ref('')
const submitting = ref(false)

const charCount = () => content.value.length
const charTooMany = () => charCount() > 2000
const canSubmit = () => content.value.trim().length >= 5 && content.value.length <= 2000 && !submitting.value

async function submit() {
  if (!canSubmit()) return
  submitting.value = true
  try {
    await feedbackApi.create({ category: category.value, content: content.value.trim() })
    toast.success('感谢反馈！')
    category.value = 'feature'
    content.value = ''
    open.value = false
  } catch (e) {
    toast.error(e.response?.data?.detail || '提交失败')
  } finally {
    submitting.value = false
  }
}
</script>

<template>
  <div class="px-3 mt-2 mb-auto">
    <Button
      variant="ghost"
      size="sm"
      class="w-full justify-start gap-2 text-xs text-muted-foreground hover:text-foreground"
      @click="open = true"
    >
      <MessageSquarePlus class="size-3.5" />
      反馈建议
    </Button>

    <Sheet :open="open" @update:open="open = $event">
      <SheetContent side="bottom" class="h-auto max-h-[65vh] rounded-t-xl">
        <SheetHeader class="text-left mb-4">
          <SheetTitle>反馈建议</SheetTitle>
          <SheetDescription>帮助我们改进 MolluscAI</SheetDescription>
        </SheetHeader>

        <form class="space-y-4" @submit.prevent="submit">
          <div>
            <label class="text-sm font-medium mb-1.5 block">类型</label>
            <div class="flex gap-2">
              <button
                v-for="opt in CATEGORIES"
                :key="opt.value"
                type="button"
                :class="cn(
                  'rounded-md px-3 py-1.5 text-sm border transition-colors',
                  category === opt.value
                    ? 'border-primary bg-primary/10 text-primary'
                    : 'border-border hover:bg-accent'
                )"
                @click="category = opt.value"
              >{{ opt.label }}</button>
            </div>
          </div>

          <div>
            <label class="text-sm font-medium mb-1.5 block">内容</label>
            <textarea
              v-model="content"
              :maxlength="2000"
              rows="5"
              class="flex w-full rounded-md border border-input bg-transparent px-3 py-2 text-sm shadow-sm placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background disabled:cursor-not-allowed disabled:opacity-50 resize-none"
              placeholder="请描述您的建议或遇到的问题..."
            />
            <div :class="cn('text-xs mt-1 text-right', charTooMany() ? 'text-destructive' : 'text-muted-foreground')">
              {{ charCount() }} / 2000
            </div>
          </div>

          <Button type="submit" class="w-full" :disabled="!canSubmit()" :loading="submitting">
            {{ submitting ? '提交中...' : '提交反馈' }}
          </Button>
        </form>
      </SheetContent>
    </Sheet>
  </div>
</template>

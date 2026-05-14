<script setup>
import { ref } from 'vue'
import { Database, ImageDown, Loader2 } from 'lucide-vue-next'
import { adminApi } from '@/api'
import Card from '@/components/ui/Card.vue'
import CardHeader from '@/components/ui/CardHeader.vue'
import CardTitle from '@/components/ui/CardTitle.vue'
import CardDescription from '@/components/ui/CardDescription.vue'
import CardContent from '@/components/ui/CardContent.vue'
import CardFooter from '@/components/ui/CardFooter.vue'
import Input from '@/components/ui/Input.vue'
import Label from '@/components/ui/Label.vue'
import Button from '@/components/ui/Button.vue'
import { toast } from 'vue-sonner'

const scrapeBatch = ref(200)
const scrapeStartId = ref('')
const scrapeLoading = ref(false)

const imageBatch = ref(50)
const imageLoading = ref(false)

async function runScrape() {
  scrapeLoading.value = true
  try {
    const payload = { batch_size: scrapeBatch.value }
    if (scrapeStartId.value) payload.start_id = Number(scrapeStartId.value)
    const { data } = await adminApi.runScraper(payload)
    toast.success(`已派发任务 · ${data.task_id.slice(0, 8)}…`, { description: data.task_name })
  } catch (e) {
    toast.error(e.response?.data?.detail || '派发失败')
  } finally {
    scrapeLoading.value = false
  }
}

async function runImages() {
  imageLoading.value = true
  try {
    const { data } = await adminApi.downloadImages({ batch_size: imageBatch.value })
    toast.success(`已派发任务 · ${data.task_id.slice(0, 8)}…`, { description: data.task_name })
  } catch (e) {
    toast.error(e.response?.data?.detail || '派发失败')
  } finally {
    imageLoading.value = false
  }
}
</script>

<template>
  <div class="max-w-3xl space-y-6">
    <header class="space-y-2">
      <h1 class="font-serif text-3xl font-semibold tracking-tight">数据采集</h1>
      <p class="text-sm text-muted-foreground">手动触发后台 Celery 任务 · 仅超级管理员可见</p>
    </header>

    <div class="grid grid-cols-1 md:grid-cols-2 gap-5">
      <Card>
        <CardHeader>
          <div class="flex items-center gap-2 text-primary">
            <Database class="size-5" />
            <CardTitle class="text-lg">拍卖数据采集</CardTitle>
          </div>
          <CardDescription>从 shellauction.net 拉取增量记录写入数据库</CardDescription>
        </CardHeader>
        <CardContent class="space-y-3">
          <div class="space-y-1.5">
            <Label for="s-batch">批量大小 (1–2000)</Label>
            <Input id="s-batch" type="number" :model-value="scrapeBatch" @update:modelValue="scrapeBatch = Number($event)" />
          </div>
          <div class="space-y-1.5">
            <Label for="s-start">起始 ID <span class="text-muted-foreground text-xs ml-1">可选</span></Label>
            <Input id="s-start" type="number" v-model="scrapeStartId" placeholder="留空则从最大 item_no+1 开始" />
          </div>
        </CardContent>
        <CardFooter>
          <Button class="w-full" :disabled="scrapeLoading" @click="runScrape">
            <Loader2 v-if="scrapeLoading" class="size-4 animate-spin" />
            执行采集
          </Button>
        </CardFooter>
      </Card>

      <Card>
        <CardHeader>
          <div class="flex items-center gap-2 text-primary">
            <ImageDown class="size-5" />
            <CardTitle class="text-lg">图片下载</CardTitle>
          </div>
          <CardDescription>下载已成交拍品的原图至 MinIO 对象存储</CardDescription>
        </CardHeader>
        <CardContent class="space-y-3">
          <div class="space-y-1.5">
            <Label for="i-batch">批量大小 (1–500)</Label>
            <Input id="i-batch" type="number" :model-value="imageBatch" @update:modelValue="imageBatch = Number($event)" />
          </div>
        </CardContent>
        <CardFooter>
          <Button class="w-full" variant="secondary" :disabled="imageLoading" @click="runImages">
            <Loader2 v-if="imageLoading" class="size-4 animate-spin" />
            执行下载
          </Button>
        </CardFooter>
      </Card>
    </div>
  </div>
</template>

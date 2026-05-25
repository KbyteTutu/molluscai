<script setup>
import { ref, onMounted, onBeforeUnmount } from 'vue'
import { Database, ImageDown, Loader2, RefreshCw } from 'lucide-vue-next'
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
import { formatNumber, formatDate } from '@/lib/utils'

const scrapeBatch = ref(200)
const scrapeStartId = ref('')
const scrapeLoading = ref(false)

const imageBatch = ref(50)
const imageFrom = ref('')
const imageTo = ref('')
const imageLoading = ref(false)

const stats = ref(null)
const statsLoading = ref(false)

async function loadStats() {
  statsLoading.value = true
  try {
    const { data } = await adminApi.scraperStats()
    stats.value = data
  } catch (e) {
    console.error('Failed to load scraper stats', e)
  } finally {
    statsLoading.value = false
  }
}

async function runScrape() {
  scrapeLoading.value = true
  try {
    const payload = { batch_size: scrapeBatch.value }
    if (scrapeStartId.value) payload.start_id = Number(scrapeStartId.value)
    const { data } = await adminApi.runScraper(payload)
    toast.success(`已派发任务 · ${data.task_id.slice(0, 8)}…`, { description: data.task_name })
    loadStats()
  } catch (e) {
    toast.error(e.response?.data?.detail || '派发失败')
  } finally {
    scrapeLoading.value = false
  }
}

async function runImages() {
  imageLoading.value = true
  try {
    const payload = { batch_size: imageBatch.value }
    if (imageFrom.value) payload.item_no_from = Number(imageFrom.value)
    if (imageTo.value) payload.item_no_to = Number(imageTo.value)
    const { data } = await adminApi.downloadImages(payload)
    toast.success(`已派发任务 · ${data.task_id.slice(0, 8)}…`, { description: data.task_name })
    loadStats()
  } catch (e) {
    toast.error(e.response?.data?.detail || '派发失败')
  } finally {
    imageLoading.value = false
  }
}

const REFRESH_INTERVAL = 15000
let pollTimer = null

function startPolling() {
  stopPolling()
  pollTimer = setInterval(loadStats, REFRESH_INTERVAL)
}
function stopPolling() {
  if (pollTimer) { clearInterval(pollTimer); pollTimer = null }
}

onMounted(() => { loadStats(); startPolling() })
onBeforeUnmount(stopPolling)
</script>

<template>
  <div class="max-w-3xl space-y-6">
    <header class="flex items-center justify-between gap-3 flex-wrap">
      <div class="space-y-1">
        <h1 class="font-serif text-3xl font-semibold tracking-tight">数据采集</h1>
        <p class="text-sm text-muted-foreground">手动触发后台 Celery 任务 · 仅超级管理员可见</p>
      </div>
      <Button variant="outline" size="sm" :disabled="statsLoading" @click="loadStats">
        <RefreshCw :class="['size-4', statsLoading && 'animate-spin']" />
      </Button>
    </header>

    <section class="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
      <Card v-for="card in [
        { label: '记录总数', value: formatNumber(stats?.total_records) },
        { label: '最大编号', value: stats?.max_item_no ?? '—' },
        { label: '最后记录', value: formatDate(stats?.last_end_date) },
        { label: '图片已下载', value: formatNumber(stats?.images_downloaded) },
        { label: '待下载', value: formatNumber(stats?.images_pending) },
        { label: '存储占用', value: stats?.storage_size_mb != null ? stats.storage_size_mb + ' MB' : '—' },
      ]" :key="card.label" class="p-3 text-center">
        <div class="text-[10px] uppercase tracking-widest text-muted-foreground">{{ card.label }}</div>
        <div class="font-serif text-base tabular-nums mt-0.5">{{ card.value }}</div>
      </Card>
    </section>

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
          <div class="grid grid-cols-2 gap-3">
            <div class="space-y-1.5">
              <Label for="i-from">编号从 <span class="text-muted-foreground text-xs ml-1">可选</span></Label>
              <Input id="i-from" type="number" v-model="imageFrom" placeholder="item_no ≥" />
            </div>
            <div class="space-y-1.5">
              <Label for="i-to">编号至 <span class="text-muted-foreground text-xs ml-1">可选</span></Label>
              <Input id="i-to" type="number" v-model="imageTo" placeholder="item_no ≤" />
            </div>
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

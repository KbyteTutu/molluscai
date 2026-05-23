<script setup>
import { ref, computed, onMounted, onBeforeUnmount } from 'vue'
import { adminApi } from '@/api'
import { RefreshCw, Loader2, Zap, AlertTriangle, CheckCircle2, Clock, Database } from 'lucide-vue-next'
import Card from '@/components/ui/Card.vue'
import CardHeader from '@/components/ui/CardHeader.vue'
import CardTitle from '@/components/ui/CardTitle.vue'
import CardDescription from '@/components/ui/CardDescription.vue'
import CardContent from '@/components/ui/CardContent.vue'
import CardFooter from '@/components/ui/CardFooter.vue'
import Button from '@/components/ui/Button.vue'
import Badge from '@/components/ui/Badge.vue'
import Alert from '@/components/ui/Alert.vue'
import AlertTitle from '@/components/ui/AlertTitle.vue'
import AlertDescription from '@/components/ui/AlertDescription.vue'
import Separator from '@/components/ui/Separator.vue'
import { formatNumber, cn } from '@/lib/utils'
import { toast } from 'vue-sonner'

const status = ref(null)
const auctionStatus = ref(null)
const loading = ref(false)
const dispatching = ref(false)
const cancelling = ref(false)
const auctionDispatching = ref(false)
const auctionCancelling = ref(false)
const autoRefresh = ref(true)
let pollTimer = null

async function load() {
  loading.value = true
  try {
    const [taxaRes, auctionRes] = await Promise.all([
      adminApi.embeddingsStatus(),
      adminApi.auctionEmbeddingsStatus(),
    ])
    status.value = taxaRes.data
    auctionStatus.value = auctionRes.data
  } catch (e) { toast.error(e.response?.data?.detail || '加载失败') }
  finally { loading.value = false }
}

function startPolling() {
  stopPolling()
  if (!autoRefresh.value) return
  pollTimer = setInterval(load, 5000)
}
function stopPolling() {
  if (pollTimer) { clearInterval(pollTimer); pollTimer = null }
}
function toggleAutoRefresh() {
  autoRefresh.value = !autoRefresh.value
  if (autoRefresh.value) startPolling()
  else stopPolling()
}

async function runEmbed(rebuild = false) {
  if (rebuild && !confirm('确认对全部物种重新生成向量？旧向量将被丢弃，按当前 tokens 计价会产生费用。')) return
  dispatching.value = true
  try {
    const { data } = await adminApi.runEmbed({ rebuild })
    toast.success(`任务已派发 · ${data.task_id.slice(0, 8)}…`, {
      description: rebuild ? '全量重建运行中，页面会每 5 秒刷新进度' : '增量嵌入运行中'
    })
    setTimeout(load, 1500)
  } catch (e) { toast.error(e.response?.data?.detail || '派发失败') }
  finally { dispatching.value = false }
}

async function cancelEmbed() {
  if (!confirm('确认停止当前嵌入任务？已完成的部分不会丢失。')) return
  cancelling.value = true
  try {
    await adminApi.cancelEmbed()
    toast.success('已发送停止信号，任务将在当前批次完成后停止')
    setTimeout(load, 2000)
  } catch (e) { toast.error(e.response?.data?.detail || '取消失败') }
  finally { cancelling.value = false }
}

async function runAuctionEmbed(rebuild = false) {
  if (rebuild && !confirm('确认对全部拍卖记录重新生成向量？旧向量将被丢弃，按当前 tokens 计价会产生费用。')) return
  auctionDispatching.value = true
  try {
    const { data } = await adminApi.runAuctionEmbed({ rebuild })
    toast.success(`拍卖嵌入任务已派发 · ${data.task_id.slice(0, 8)}…`, {
      description: rebuild ? '全量重建运行中' : '增量嵌入运行中'
    })
    setTimeout(load, 1500)
  } catch (e) { toast.error(e.response?.data?.detail || '派发失败') }
  finally { auctionDispatching.value = false }
}

async function cancelAuctionEmbed() {
  if (!confirm('确认停止拍卖嵌入任务？已完成的部分不会丢失。')) return
  auctionCancelling.value = true
  try {
    await adminApi.cancelAuctionEmbed()
    toast.success('已发送停止信号')
    setTimeout(load, 2000)
  } catch (e) { toast.error(e.response?.data?.detail || '取消失败') }
  finally { auctionCancelling.value = false }
}

const mainCoverage = computed(() => {
  if (!status.value?.active_model || !status.value.coverage) return null
  return status.value.coverage.find(c => c.model_name === status.value.active_model.model_name)
})

const pct = computed(() => mainCoverage.value?.pct ?? 0)
const embedded = computed(() => mainCoverage.value?.embedded ?? 0)
const total = computed(() => status.value?.total_taxa ?? 0)
const remaining = computed(() => Math.max(total.value - embedded.value, 0))

const isBusy = computed(() => {
  if (!status.value) return false
  return (status.value.throughput_1h?.calls ?? 0) > 0 && pct.value < 100
})

const auctionMainCoverage = computed(() => {
  if (!auctionStatus.value?.active_model || !auctionStatus.value.coverage) return null
  return auctionStatus.value.coverage.find(c => c.model_name === auctionStatus.value.active_model.model_name)
})
const auctionPct = computed(() => auctionMainCoverage.value?.pct ?? 0)
const auctionEmbedded = computed(() => auctionMainCoverage.value?.embedded ?? 0)
const auctionTotal = computed(() => auctionStatus.value?.total_auctions ?? 0)
const auctionRemaining = computed(() => Math.max(auctionTotal.value - auctionEmbedded.value, 0))

const etaLabel = computed(() => {
  const t = status.value?.throughput_1h
  if (!t || !t.calls || remaining.value === 0) return null
  const batchSize = 64
  const callsNeeded = Math.ceil(remaining.value / batchSize)
  const hoursRemaining = callsNeeded / Math.max(t.calls, 1)
  const minutes = Math.round(hoursRemaining * 60)
  if (minutes < 60) return `预计 ${minutes} 分钟`
  return `预计 ${Math.round(minutes / 60)} 小时`
})

function fmtTime(s) {
  try { return new Date(s).toLocaleString('zh-CN', { hour12: false }) } catch { return s }
}

onMounted(() => { load(); startPolling() })
onBeforeUnmount(stopPolling)
</script>

<template>
  <div class="space-y-6">
    <header class="flex items-end justify-between flex-wrap gap-3">
      <div class="space-y-1">
        <h1 class="font-serif text-3xl font-semibold tracking-tight">向量管理</h1>
        <p class="text-sm text-muted-foreground">监控物种 / 拍卖向量化进度、吞吐与错误 · 仅超级管理员可见</p>
      </div>
      <div class="flex items-center gap-2">
        <label class="inline-flex items-center gap-1.5 text-xs text-muted-foreground">
          <input type="checkbox" :checked="autoRefresh" @change="toggleAutoRefresh" />
          自动刷新 (5s)
        </label>
        <Button variant="outline" size="sm" @click="load" :disabled="loading">
          <Loader2 v-if="loading" class="size-4 animate-spin" />
          <RefreshCw v-else class="size-4" /> 刷新
        </Button>
      </div>
    </header>

    <Alert v-if="!status?.active_model" variant="destructive">
      <AlertTriangle class="size-4" />
      <AlertTitle>未启用 Embedding 模型</AlertTitle>
      <AlertDescription>
        请先在「模型配置」中添加并启用一个向量嵌入模型
      </AlertDescription>
    </Alert>

    <Card v-if="status?.active_model">
      <CardHeader>
        <div class="flex items-center justify-between flex-wrap gap-3">
          <div class="space-y-1">
            <CardTitle class="text-lg font-mono">{{ status.active_model.model_name }}</CardTitle>
            <CardDescription>
              {{ status.active_model.provider }} · {{ status.active_model.model_id }}
              <span v-if="isBusy" class="ml-2 inline-flex items-center gap-1 text-primary">
                <Loader2 class="size-3 animate-spin" /> 嵌入中
              </span>
            </CardDescription>
          </div>
          <div class="text-right">
            <div class="font-serif text-3xl tabular-nums">{{ pct.toFixed(1) }}<span class="text-lg text-muted-foreground">%</span></div>
            <div class="text-xs text-muted-foreground">
              {{ formatNumber(embedded) }} / {{ formatNumber(total) }}
              <span v-if="etaLabel" class="text-primary ml-1">· {{ etaLabel }}</span>
            </div>
          </div>
        </div>
      </CardHeader>
      <CardContent>
        <div class="h-2.5 bg-muted rounded-full overflow-hidden">
          <div
            class="h-full bg-primary transition-all duration-500"
            :style="{ width: pct + '%' }"
          />
        </div>
        <div class="flex items-center justify-between mt-3 text-xs text-muted-foreground">
          <span>剩余 {{ formatNumber(remaining) }} 条</span>
          <span v-if="mainCoverage?.last_at">最后一条: {{ fmtTime(mainCoverage.last_at) }}</span>
        </div>
      </CardContent>
      <Separator />
      <CardFooter class="gap-2 pt-6">
        <Button size="sm" :disabled="dispatching || remaining === 0" @click="runEmbed(false)">
          <Zap class="size-4" />
          {{ remaining === 0 ? '已全部嵌入' : `嵌入剩余 ${formatNumber(remaining)} 条` }}
        </Button>
        <Button size="sm" variant="destructive" :disabled="dispatching" @click="runEmbed(true)">
          全量重建
        </Button>
        <Button v-if="isBusy" size="sm" variant="outline" :disabled="cancelling" @click="cancelEmbed">
          <Loader2 v-if="cancelling" class="size-4 animate-spin" />
          停止任务
        </Button>
        <span v-if="isBusy && !cancelling" class="ml-auto text-xs text-muted-foreground">
          Worker 正在处理，无需重复派发
        </span>
      </CardFooter>
    </Card>

    <section class="grid grid-cols-2 md:grid-cols-4 gap-3">
      <Card class="p-4">
        <div class="flex items-center gap-1.5 text-[10px] uppercase tracking-widest text-muted-foreground">
          <Clock class="size-3" /> 最近 1 小时
        </div>
        <div class="font-serif text-2xl mt-1 tabular-nums">{{ formatNumber(status?.throughput_1h?.calls ?? 0) }}</div>
        <div class="text-[11px] text-muted-foreground mt-0.5">次调用</div>
      </Card>
      <Card class="p-4">
        <div class="text-[10px] uppercase tracking-widest text-muted-foreground">1h Tokens</div>
        <div class="font-serif text-2xl mt-1 tabular-nums">{{ formatNumber(status?.throughput_1h?.tokens ?? 0) }}</div>
        <div class="text-[11px] text-muted-foreground mt-0.5">
          ¥{{ Number(status?.throughput_1h?.cost ?? 0).toFixed(4) }}
        </div>
      </Card>
      <Card class="p-4">
        <div class="text-[10px] uppercase tracking-widest text-muted-foreground">24h Tokens</div>
        <div class="font-serif text-2xl mt-1 tabular-nums">{{ formatNumber(status?.throughput_24h?.tokens ?? 0) }}</div>
        <div class="text-[11px] text-muted-foreground mt-0.5">
          ¥{{ Number(status?.throughput_24h?.cost ?? 0).toFixed(4) }}
        </div>
      </Card>
      <Card class="p-4">
        <div class="flex items-center gap-1.5 text-[10px] uppercase tracking-widest text-muted-foreground">
          <Clock class="size-3" /> 平均延迟
        </div>
        <div class="font-serif text-2xl mt-1 tabular-nums">
          {{ status?.throughput_1h?.avg_latency_ms ?? status?.throughput_24h?.avg_latency_ms ?? '—' }}
          <span class="text-sm text-muted-foreground">ms</span>
        </div>
        <div class="text-[11px] text-muted-foreground mt-0.5">
          <span v-if="status?.throughput_24h?.errors">
            <AlertTriangle class="inline size-3 text-destructive" />
            24h {{ status.throughput_24h.errors }} 次错误
          </span>
          <span v-else class="inline-flex items-center gap-1 text-primary">
            <CheckCircle2 class="size-3" /> 24h 无错误
          </span>
        </div>
      </Card>
    </section>

    <!-- ── 拍卖记录嵌入 ── -->
    <Separator />

    <Card v-if="auctionStatus?.active_model">
      <CardHeader>
        <div class="flex items-center justify-between flex-wrap gap-3">
          <div class="space-y-1">
            <CardTitle class="text-lg flex items-center gap-2">
              <Database class="size-5" /> 拍卖记录嵌入
            </CardTitle>
            <CardDescription>
              {{ auctionStatus.active_model.model_name }}
              · {{ formatNumber(auctionTotal) }} 条拍卖记录
            </CardDescription>
          </div>
          <div class="text-right">
            <div class="font-serif text-3xl tabular-nums">{{ auctionPct.toFixed(1) }}<span class="text-lg text-muted-foreground">%</span></div>
            <div class="text-xs text-muted-foreground">
              {{ formatNumber(auctionEmbedded) }} / {{ formatNumber(auctionTotal) }}
            </div>
          </div>
        </div>
      </CardHeader>
      <CardContent>
        <div class="h-2.5 bg-muted rounded-full overflow-hidden">
          <div
            class="h-full bg-primary transition-all duration-500"
            :style="{ width: auctionPct + '%' }"
          />
        </div>
        <div class="flex items-center justify-between mt-3 text-xs text-muted-foreground">
          <span>剩余 {{ formatNumber(auctionRemaining) }} 条</span>
          <span v-if="auctionMainCoverage?.last_at">最后一条: {{ fmtTime(auctionMainCoverage.last_at) }}</span>
        </div>
      </CardContent>
      <Separator />
      <CardFooter class="gap-2 pt-6">
        <Button size="sm" :disabled="auctionDispatching || auctionRemaining === 0" @click="runAuctionEmbed(false)">
          <Zap class="size-4" />
          {{ auctionRemaining === 0 ? '已全部嵌入' : `嵌入剩余 ${formatNumber(auctionRemaining)} 条` }}
        </Button>
        <Button size="sm" variant="destructive" :disabled="auctionDispatching" @click="runAuctionEmbed(true)">
          全量重建
        </Button>
        <Button v-if="auctionCancelling || auctionDispatching" size="sm" variant="outline" :disabled="auctionCancelling" @click="cancelAuctionEmbed">
          <Loader2 v-if="auctionCancelling" class="size-4 animate-spin" />
          停止任务
        </Button>
      </CardFooter>
    </Card>

    <section v-if="status?.coverage?.length > 1" class="space-y-3">
      <h2 class="font-serif text-xl">所有模型的向量覆盖</h2>
      <Card class="divide-y overflow-hidden">
        <div v-for="c in status.coverage" :key="c.model_name" class="p-4 flex items-center gap-4">
          <div class="flex-1 min-w-0">
            <div class="flex items-center gap-2 flex-wrap">
              <span class="font-mono text-sm">{{ c.model_name }}</span>
              <Badge v-if="status.active_model?.model_name === c.model_name" variant="default" class="text-[10px]">
                ACTIVE
              </Badge>
            </div>
            <div class="mt-2 h-1.5 bg-muted rounded-full overflow-hidden">
              <div class="h-full bg-foreground/60" :style="{ width: c.pct + '%' }" />
            </div>
          </div>
          <div class="text-right shrink-0">
            <div class="font-mono text-sm tabular-nums">{{ formatNumber(c.embedded) }}</div>
            <div class="text-[11px] text-muted-foreground">{{ c.pct.toFixed(1) }}%</div>
          </div>
        </div>
      </Card>
    </section>

    <section v-if="status?.recent_errors?.length" class="space-y-3">
      <h2 class="font-serif text-xl flex items-center gap-2">
        <AlertTriangle class="size-5 text-destructive" /> 最近错误
      </h2>
      <Card class="divide-y overflow-hidden">
        <div v-for="err in status.recent_errors" :key="err.id" class="p-4">
          <div class="flex items-center justify-between gap-2 flex-wrap">
            <span class="font-mono text-xs">{{ err.model_name }}</span>
            <span class="text-[11px] text-muted-foreground">{{ fmtTime(err.created_at) }}</span>
          </div>
          <p class="mt-2 text-xs text-destructive break-words">{{ err.error_message }}</p>
        </div>
      </Card>
    </section>
  </div>
</template>

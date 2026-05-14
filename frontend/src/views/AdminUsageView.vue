<script setup>
import { ref, onMounted, computed } from 'vue'
import { adminApi } from '@/api'
import { RefreshCw } from 'lucide-vue-next'
import Card from '@/components/ui/Card.vue'
import Button from '@/components/ui/Button.vue'
import Badge from '@/components/ui/Badge.vue'
import Table from '@/components/ui/Table.vue'
import TableHeader from '@/components/ui/TableHeader.vue'
import TableBody from '@/components/ui/TableBody.vue'
import TableRow from '@/components/ui/TableRow.vue'
import TableHead from '@/components/ui/TableHead.vue'
import TableCell from '@/components/ui/TableCell.vue'
import EmptyState from '@/components/common/EmptyState.vue'
import { formatNumber } from '@/lib/utils'
import { toast } from 'vue-sonner'

const days = ref(30)
const summary = ref([])
const recent = ref([])
const loading = ref(false)

const totalCalls = computed(() => summary.value.reduce((a, r) => a + (r.calls || 0), 0))
const totalTokens = computed(() => summary.value.reduce((a, r) => a + (r.total_tokens || 0), 0))
const totalCost = computed(() => summary.value.reduce((a, r) => a + Number(r.cost || 0), 0))

async function load() {
  loading.value = true
  try {
    const [s, r] = await Promise.all([adminApi.usageSummary(days.value), adminApi.usageRecent(100)])
    summary.value = s.data
    recent.value = r.data
  } catch (e) { toast.error(e.response?.data?.detail || '加载失败') }
  finally { loading.value = false }
}

function fmtTime(s) {
  try { return new Date(s).toLocaleString('zh-CN', { hour12: false }) } catch { return s }
}

onMounted(load)
</script>

<template>
  <div class="space-y-6">
    <header class="flex items-end justify-between flex-wrap gap-3">
      <div class="space-y-1">
        <h1 class="font-serif text-3xl font-semibold tracking-tight">用量统计</h1>
        <p class="text-sm text-muted-foreground">模型调用次数、tokens 消耗与费用 · 仅超级管理员可见</p>
      </div>
      <div class="flex items-center gap-2">
        <select v-model.number="days" @change="load" class="h-9 rounded-md border border-input bg-background px-2 text-sm">
          <option :value="1">最近 1 天</option>
          <option :value="7">最近 7 天</option>
          <option :value="30">最近 30 天</option>
          <option :value="90">最近 90 天</option>
        </select>
        <Button variant="outline" size="sm" @click="load"><RefreshCw class="size-4" /> 刷新</Button>
      </div>
    </header>

    <section class="grid grid-cols-1 sm:grid-cols-3 gap-3">
      <Card class="p-4">
        <div class="text-[10px] uppercase tracking-widest text-muted-foreground">调用次数</div>
        <div class="font-serif text-2xl mt-1 tabular-nums">{{ formatNumber(totalCalls) }}</div>
      </Card>
      <Card class="p-4">
        <div class="text-[10px] uppercase tracking-widest text-muted-foreground">Tokens 总量</div>
        <div class="font-serif text-2xl mt-1 tabular-nums">{{ formatNumber(totalTokens) }}</div>
      </Card>
      <Card class="p-4">
        <div class="text-[10px] uppercase tracking-widest text-muted-foreground">费用 (¥)</div>
        <div class="font-serif text-2xl mt-1 tabular-nums">{{ totalCost.toFixed(4) }}</div>
      </Card>
    </section>

    <section class="space-y-3">
      <h2 class="font-serif text-xl">按模型汇总</h2>
      <Card v-if="!summary.length" class="p-8 text-center text-sm text-muted-foreground">暂无调用</Card>
      <Card v-else class="overflow-hidden">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>模型</TableHead>
              <TableHead>用途</TableHead>
              <TableHead class="text-right">调用</TableHead>
              <TableHead class="text-right">输入 tokens</TableHead>
              <TableHead class="text-right">合计 tokens</TableHead>
              <TableHead class="text-right">费用 (¥)</TableHead>
              <TableHead class="text-right">平均延迟 (ms)</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            <TableRow v-for="row in summary" :key="row.model_config_id + row.purpose">
              <TableCell class="font-mono text-xs">{{ row.model_name }}</TableCell>
              <TableCell>
                <Badge :variant="row.purpose === 'embedding' ? 'default' : 'secondary'" class="text-[10px] uppercase">
                  {{ row.purpose }}
                </Badge>
              </TableCell>
              <TableCell class="text-right font-mono tabular-nums">{{ formatNumber(row.calls) }}</TableCell>
              <TableCell class="text-right font-mono tabular-nums">{{ formatNumber(row.input_tokens) }}</TableCell>
              <TableCell class="text-right font-mono tabular-nums">{{ formatNumber(row.total_tokens) }}</TableCell>
              <TableCell class="text-right font-mono tabular-nums">{{ Number(row.cost).toFixed(4) }}</TableCell>
              <TableCell class="text-right font-mono tabular-nums">{{ row.avg_latency_ms || '—' }}</TableCell>
            </TableRow>
          </TableBody>
        </Table>
      </Card>
    </section>

    <section class="space-y-3">
      <h2 class="font-serif text-xl">近 100 次调用</h2>
      <EmptyState v-if="!recent.length" title="暂无调用记录" />
      <Card v-else class="overflow-hidden">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead class="w-[170px]">时间</TableHead>
              <TableHead>模型</TableHead>
              <TableHead>用途</TableHead>
              <TableHead class="text-right">输入 tokens</TableHead>
              <TableHead class="text-right">费用</TableHead>
              <TableHead class="text-right">延迟</TableHead>
              <TableHead>状态</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            <TableRow v-for="row in recent" :key="row.id">
              <TableCell class="text-xs text-muted-foreground">{{ fmtTime(row.created_at) }}</TableCell>
              <TableCell class="font-mono text-xs">{{ row.model_name }}</TableCell>
              <TableCell>
                <Badge :variant="row.purpose === 'embedding' ? 'default' : 'secondary'" class="text-[10px]">{{ row.purpose }}</Badge>
              </TableCell>
              <TableCell class="text-right font-mono tabular-nums">{{ row.input_tokens ?? '—' }}</TableCell>
              <TableCell class="text-right font-mono tabular-nums">{{ Number(row.cost).toFixed(6) }}</TableCell>
              <TableCell class="text-right font-mono tabular-nums">{{ row.latency_ms ?? '—' }}</TableCell>
              <TableCell>
                <Badge v-if="row.status === 'success'" variant="default" class="text-[10px]">OK</Badge>
                <Badge v-else variant="destructive" class="text-[10px]" :title="row.error_message">ERR</Badge>
              </TableCell>
            </TableRow>
          </TableBody>
        </Table>
      </Card>
    </section>
  </div>
</template>

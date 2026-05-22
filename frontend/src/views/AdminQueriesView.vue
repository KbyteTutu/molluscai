<script setup>
import { ref, onMounted, computed } from 'vue'
import { adminApi } from '@/api'
import { RefreshCw, AlertTriangle } from 'lucide-vue-next'
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
import Skeleton from '@/components/ui/Skeleton.vue'
import { formatNumber } from '@/lib/utils'
import { toast } from 'vue-sonner'

const TYPE_LABEL = { ai: '智能检索', auction: '拍卖', taxa: '物种' }
const TYPE_STROKE = {
  ai: 'stroke-primary',
  auction: 'stroke-amber-500',
  taxa: 'stroke-emerald-500'
}
const TYPE_FILL = {
  ai: 'fill-primary',
  auction: 'fill-amber-500',
  taxa: 'fill-emerald-500'
}
const TYPE_BG = {
  ai: 'bg-primary',
  auction: 'bg-amber-500',
  taxa: 'bg-emerald-500'
}

const days = ref(7)
const recentLimit = ref(100)
const q = ref('')
const stats = ref(null)
const recent = ref([])
const loading = ref(false)
const errored = ref(false)

const totalByType = computed(() => stats.value?.by_type?.reduce((a, r) => a + (r.count || 0), 0) || 0)

const typeKeys = computed(() => {
  const set = new Set()
  for (const r of (stats.value?.by_type || [])) set.add(r.query_type)
  for (const r of (stats.value?.by_day || [])) set.add(r.query_type)
  return [...set]
})

const chart = computed(() => {
  const byDay = stats.value?.by_day || []
  if (!byDay.length) return null

  const dayList = [...new Set(byDay.map(r => r.day))].sort()
  const series = {}
  for (const t of typeKeys.value) series[t] = dayList.map(() => 0)

  for (const r of byDay) {
    const di = dayList.indexOf(r.day)
    if (di === -1 || !series[r.query_type]) continue
    series[r.query_type][di] += r.count || 0
  }

  let maxY = 1
  for (const t of typeKeys.value) {
    for (const v of series[t]) if (v > maxY) maxY = v
  }

  const W = 800, H = 240, PAD_L = 40, PAD_R = 16, PAD_T = 16, PAD_B = 36
  const innerW = W - PAD_L - PAD_R
  const innerH = H - PAD_T - PAD_B

  const xAt = (i) => {
    if (dayList.length === 1) return PAD_L + innerW / 2
    return PAD_L + (i * innerW) / (dayList.length - 1)
  }
  const yAt = (v) => PAD_T + innerH - (v / maxY) * innerH

  const lines = {}
  for (const t of typeKeys.value) {
    lines[t] = series[t].map((v, i) => `${xAt(i).toFixed(1)},${yAt(v).toFixed(1)}`).join(' ')
  }

  const yTicks = []
  const tickCount = 4
  for (let i = 0; i <= tickCount; i++) {
    const v = Math.round((maxY * i) / tickCount)
    yTicks.push({ v, y: yAt(v) })
  }

  const labelStep = Math.max(1, Math.ceil(dayList.length / 8))
  const xLabels = dayList.map((d, i) => ({
    show: i % labelStep === 0 || i === dayList.length - 1,
    x: xAt(i),
    label: d.slice(5)
  }))

  return { W, H, lines, series, dayList, xLabels, yTicks, maxY, xAt, yAt }
})

async function load() {
  loading.value = true
  errored.value = false
  try {
    const [s, r] = await Promise.all([
      adminApi.queryStats(days.value),
      adminApi.recentQueries(recentLimit.value, q.value)
    ])
    stats.value = s.data
    recent.value = r.data || []
  } catch (e) {
    errored.value = true
    toast.error(e.response?.data?.detail || '加载查询统计失败')
  } finally {
    loading.value = false
  }
}

function fmtTime(s) {
  try { return new Date(s).toLocaleString('zh-CN', { hour12: false }) } catch { return s }
}

function typeLabel(t) { return TYPE_LABEL[t] || t }

function typeBadgeVariant(t) {
  if (t === 'ai') return 'default'
  if (t === 'auction' || t === 'taxa') return 'secondary'
  return 'outline'
}

function statusBadge(code) {
  if (code === 200) return { variant: 'default', label: 'OK', extra: '' }
  if (code === 429) return { variant: 'destructive', label: '限流', extra: '' }
  if (code >= 400 && code < 500) return { variant: 'outline', label: '拒', extra: 'border-red-500/60 text-red-600' }
  if (code >= 500) return { variant: 'destructive', label: '错', extra: '' }
  return { variant: 'outline', label: String(code ?? '—'), extra: '' }
}

function truncateText(s, n = 60) {
  if (!s) return ''
  return s.length > n ? s.slice(0, n) + '…' : s
}

function typeShare(count) {
  if (!totalByType.value) return 0
  return Math.max(2, Math.round((count / totalByType.value) * 100))
}

onMounted(load)
</script>

<template>
  <div class="space-y-6">
    <header class="flex items-end justify-between flex-wrap gap-3">
      <div class="space-y-1">
        <h1 class="font-serif text-3xl font-semibold tracking-tight">查询日志</h1>
        <p class="text-sm text-muted-foreground">全站检索请求统计与近期日志 · 仅超级管理员可见</p>
      </div>
      <div class="flex items-center gap-2">
        <select
          v-model.number="days"
          @change="load"
          class="h-9 rounded-md border border-input bg-background px-2 text-sm"
        >
          <option :value="1">最近 1 天</option>
          <option :value="7">最近 7 天</option>
          <option :value="30">最近 30 天</option>
          <option :value="90">最近 90 天</option>
        </select>
        <Button variant="outline" size="sm" @click="load" :disabled="loading">
          <RefreshCw class="size-4" :class="loading && 'animate-spin'" /> 刷新
        </Button>
      </div>
    </header>

    <section class="flex items-center gap-3 flex-wrap">
      <div class="flex items-center gap-2">
        <label class="text-xs text-muted-foreground whitespace-nowrap">最近</label>
        <select
          v-model.number="recentLimit"
          @change="load"
          class="h-8 rounded-md border border-input bg-background px-2 text-xs"
        >
          <option :value="50">50 条</option>
          <option :value="100">100 条</option>
          <option :value="200">200 条</option>
          <option :value="500">500 条</option>
        </select>
      </div>
      <div class="flex items-center gap-2 flex-1 max-w-sm">
        <label class="text-xs text-muted-foreground whitespace-nowrap">关键字</label>
        <input
          v-model.trim="q"
          @keydown.enter="load"
          placeholder="搜索查询内容…"
          class="h-8 flex-1 rounded-md border border-input bg-background px-2 text-xs placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
        />
        <Button variant="outline" size="sm" @click="load" :disabled="loading" class="h-8 text-xs">过滤</Button>
      </div>
    </section>

    <section class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
      <Card class="p-4">
        <div class="text-[10px] uppercase tracking-widest text-muted-foreground">总查询数</div>
        <div class="font-serif text-2xl mt-1 tabular-nums">
          <Skeleton v-if="loading && !stats" class="h-7 w-24" />
          <template v-else>{{ formatNumber(stats?.total ?? 0) }}</template>
        </div>
      </Card>
      <Card class="p-4">
        <div class="text-[10px] uppercase tracking-widest text-muted-foreground">命中限流 (429)</div>
        <div
          class="font-serif text-2xl mt-1 tabular-nums flex items-center gap-2"
          :class="(stats?.rate_limited_429 ?? 0) > 0 ? 'text-destructive' : ''"
        >
          <Skeleton v-if="loading && !stats" class="h-7 w-16" />
          <template v-else>
            <AlertTriangle v-if="(stats?.rate_limited_429 ?? 0) > 0" class="size-4" />
            {{ formatNumber(stats?.rate_limited_429 ?? 0) }}
          </template>
        </div>
      </Card>
      <Card class="p-4">
        <div class="text-[10px] uppercase tracking-widest text-muted-foreground">类型分布</div>
        <div v-if="loading && !stats" class="mt-2 space-y-1.5">
          <Skeleton class="h-3 w-full" />
          <Skeleton class="h-3 w-2/3" />
        </div>
        <div v-else-if="!stats?.by_type?.length" class="text-sm text-muted-foreground mt-2">—</div>
        <div v-else class="mt-2 space-y-1.5">
          <div
            v-for="r in stats.by_type"
            :key="r.query_type"
            class="flex items-center gap-2 text-xs"
          >
            <span class="size-2 rounded-full shrink-0" :class="TYPE_BG[r.query_type] || 'bg-muted-foreground/40'" />
            <span class="text-muted-foreground min-w-[56px]">{{ typeLabel(r.query_type) }}</span>
            <span class="font-mono tabular-nums ml-auto">{{ formatNumber(r.count) }}</span>
          </div>
        </div>
      </Card>
      <Card class="p-4">
        <div class="text-[10px] uppercase tracking-widest text-muted-foreground">时间范围</div>
        <div class="font-serif text-2xl mt-1 tabular-nums">
          <Skeleton v-if="loading && !stats" class="h-7 w-20" />
          <template v-else>最近 {{ stats?.range_days ?? days }} 天</template>
        </div>
      </Card>
    </section>

    <section class="space-y-3">
      <h2 class="font-serif text-xl">按类型分组</h2>
      <Card v-if="loading && !stats" class="p-4">
        <Skeleton class="h-6 w-full" />
      </Card>
      <Card v-else-if="!stats?.by_type?.length" class="p-8 text-center text-sm text-muted-foreground">
        暂无类型数据
      </Card>
      <Card v-else class="p-4 space-y-3">
        <div class="flex w-full h-3 rounded-full overflow-hidden bg-muted">
          <div
            v-for="r in stats.by_type"
            :key="r.query_type"
            :class="TYPE_BG[r.query_type] || 'bg-muted-foreground/40'"
            :style="{ width: typeShare(r.count) + '%' }"
            :title="`${typeLabel(r.query_type)}: ${formatNumber(r.count)}`"
          />
        </div>
        <div class="flex flex-wrap gap-x-4 gap-y-1.5 text-xs">
          <div v-for="r in stats.by_type" :key="r.query_type" class="flex items-center gap-1.5">
            <span class="size-2 rounded-full" :class="TYPE_BG[r.query_type] || 'bg-muted-foreground/40'" />
            <span class="text-muted-foreground">{{ typeLabel(r.query_type) }}</span>
            <span class="font-mono tabular-nums">{{ formatNumber(r.count) }}</span>
            <span class="text-muted-foreground">·</span>
            <span class="font-mono text-muted-foreground">{{ totalByType ? Math.round(r.count / totalByType * 100) : 0 }}%</span>
          </div>
        </div>
      </Card>
    </section>

    <section class="space-y-3">
      <h2 class="font-serif text-xl">每日趋势</h2>
      <Card v-if="loading && !stats" class="p-4">
        <Skeleton class="h-[240px] w-full" />
      </Card>
      <Card v-else-if="!chart" class="p-8 text-center text-sm text-muted-foreground">
        暂无趋势数据
      </Card>
      <Card v-else class="p-4 space-y-3 overflow-hidden">
        <div class="flex flex-wrap gap-x-3 gap-y-1.5">
          <Badge
            v-for="t in typeKeys"
            :key="t"
            variant="outline"
            class="text-[10px] gap-1.5"
          >
            <span class="size-2 rounded-full" :class="TYPE_BG[t] || 'bg-muted-foreground/40'" />
            {{ typeLabel(t) }}
          </Badge>
        </div>
        <div class="w-full overflow-x-auto">
          <svg
            :viewBox="`0 0 ${chart.W} ${chart.H}`"
            class="w-full h-auto min-w-[640px]"
            role="img"
            aria-label="每日查询趋势"
          >
            <g class="text-muted-foreground" font-size="10">
              <line
                v-for="(t, i) in chart.yTicks"
                :key="'g' + i"
                :x1="40" :x2="chart.W - 16"
                :y1="t.y" :y2="t.y"
                class="stroke-border"
                stroke-width="1"
                stroke-dasharray="2 3"
              />
              <text
                v-for="(t, i) in chart.yTicks"
                :key="'yt' + i"
                :x="36" :y="t.y + 3"
                text-anchor="end"
                fill="currentColor"
              >{{ formatNumber(t.v) }}</text>
            </g>

            <g>
              <polyline
                v-for="t in typeKeys"
                :key="'l' + t"
                :points="chart.lines[t]"
                fill="none"
                stroke-width="1.75"
                stroke-linejoin="round"
                stroke-linecap="round"
                :class="TYPE_STROKE[t] || 'stroke-muted-foreground'"
              />
              <template v-for="t in typeKeys" :key="'pts' + t">
                <circle
                  v-for="(v, i) in chart.series[t]"
                  :key="t + '-' + i"
                  :cx="chart.xAt(i)"
                  :cy="chart.yAt(v)"
                  r="2.5"
                  :class="TYPE_FILL[t] || 'fill-muted-foreground'"
                />
              </template>
            </g>

            <g class="text-muted-foreground" font-size="10">
              <text
                v-for="(l, i) in chart.xLabels"
                v-show="l.show"
                :key="'x' + i"
                :x="l.x" :y="chart.H - 14"
                text-anchor="middle"
                fill="currentColor"
              >{{ l.label }}</text>
            </g>
          </svg>
        </div>
      </Card>
    </section>

    <section class="grid grid-cols-1 lg:grid-cols-2 gap-3">
      <div class="space-y-3">
        <h2 class="font-serif text-xl">Top 用户</h2>
        <Card v-if="loading && !stats" class="p-4 space-y-2">
          <Skeleton v-for="i in 4" :key="i" class="h-6 w-full" />
        </Card>
        <Card v-else-if="!stats?.top_users?.length" class="p-8 text-center text-sm text-muted-foreground">
          暂无活跃用户
        </Card>
        <Card v-else class="overflow-hidden">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>用户名</TableHead>
                <TableHead>user_id</TableHead>
                <TableHead class="text-right">查询数</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              <TableRow v-for="u in stats.top_users" :key="u.user_id">
                <TableCell class="truncate max-w-[160px]">{{ u.username || '匿名' }}</TableCell>
                <TableCell class="font-mono text-xs text-muted-foreground truncate max-w-[120px]">{{ u.user_id }}</TableCell>
                <TableCell class="text-right font-mono tabular-nums">{{ formatNumber(u.count) }}</TableCell>
              </TableRow>
            </TableBody>
          </Table>
        </Card>
      </div>

      <div class="space-y-3">
        <h2 class="font-serif text-xl">Top 关键词</h2>
        <Card v-if="loading && !stats" class="p-4 space-y-2">
          <Skeleton v-for="i in 4" :key="i" class="h-6 w-full" />
        </Card>
        <Card v-else-if="!stats?.top_keywords?.length" class="p-8 text-center text-sm text-muted-foreground">
          暂无热词
        </Card>
        <Card v-else class="overflow-hidden">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>关键词</TableHead>
                <TableHead class="text-right">命中次数</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              <TableRow v-for="k in stats.top_keywords" :key="k.keyword">
                <TableCell class="truncate max-w-[280px]" :title="k.keyword">{{ truncateText(k.keyword, 60) }}</TableCell>
                <TableCell class="text-right font-mono tabular-nums">{{ formatNumber(k.count) }}</TableCell>
              </TableRow>
            </TableBody>
          </Table>
        </Card>
      </div>
    </section>

    <section class="space-y-3">
      <h2 class="font-serif text-xl">近 {{ recentLimit }} 条查询日志</h2>
      <Card v-if="loading && !recent.length" class="p-4 space-y-2">
        <Skeleton v-for="i in 6" :key="i" class="h-8 w-full" />
      </Card>
      <EmptyState
        v-else-if="!recent.length"
        title="暂无查询记录"
        description="此时间窗口内尚无任何检索请求"
      />
      <Card v-else class="overflow-hidden">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead class="w-[170px]">时间</TableHead>
              <TableHead>用户</TableHead>
              <TableHead>IP</TableHead>
              <TableHead>类型</TableHead>
              <TableHead>查询内容</TableHead>
              <TableHead class="text-right">结果数</TableHead>
              <TableHead>状态</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            <TableRow v-for="row in recent" :key="row.id">
              <TableCell class="text-xs text-muted-foreground whitespace-nowrap">{{ fmtTime(row.created_at) }}</TableCell>
              <TableCell class="text-xs">
                <span v-if="row.username" class="font-medium">{{ row.username }}</span>
                <span v-else-if="row.user_id" class="font-mono text-muted-foreground">{{ row.user_id }}</span>
                <span v-else class="text-muted-foreground italic">匿名</span>
              </TableCell>
              <TableCell class="font-mono text-xs text-muted-foreground">{{ row.display_ip || row.ip_address || '—' }}</TableCell>
              <TableCell>
                <Badge :variant="typeBadgeVariant(row.query_type)" class="text-[10px]">
                  {{ typeLabel(row.query_type) }}
                </Badge>
              </TableCell>
              <TableCell class="max-w-sm">
                <p
                  class="text-xs leading-snug line-clamp-2 break-words"
                  :title="row.query_text"
                >{{ row.query_text || '—' }}</p>
              </TableCell>
              <TableCell class="text-right font-mono tabular-nums">{{ row.result_count ?? '—' }}</TableCell>
              <TableCell>
                <Badge
                  :variant="statusBadge(row.status_code).variant"
                  :class="['text-[10px]', statusBadge(row.status_code).extra]"
                  :title="String(row.status_code)"
                >
                  {{ statusBadge(row.status_code).label }}
                </Badge>
              </TableCell>
            </TableRow>
          </TableBody>
        </Table>
      </Card>
    </section>
  </div>
</template>

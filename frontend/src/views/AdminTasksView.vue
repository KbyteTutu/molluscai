<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { ListTodo, Play, CheckCircle2, XCircle, Clock, RefreshCw, StopCircle, Loader2 } from 'lucide-vue-next'
import { adminApi } from '@/api'
import Card from '@/components/ui/Card.vue'
import CardHeader from '@/components/ui/CardHeader.vue'
import CardTitle from '@/components/ui/CardTitle.vue'
import CardContent from '@/components/ui/CardContent.vue'
import Badge from '@/components/ui/Badge.vue'
import Button from '@/components/ui/Button.vue'
import Skeleton from '@/components/ui/Skeleton.vue'
import { toast } from 'vue-sonner'

const tasks = ref([])
const workers = ref({ active: 0, scheduled: 0, reserved: 0 })
const loading = ref(true)
const autoRefresh = ref(true)
let timer = null

const STATE_META = {
  PENDING: { variant: 'secondary', icon: Clock, label: '等待中' },
  STARTED: { variant: 'default', icon: Play, label: '执行中' },
  RETRY: { variant: 'secondary', icon: RefreshCw, label: '重试中' },
  SUCCESS: { variant: 'default', icon: CheckCircle2, label: '成功' },
  FAILURE: { variant: 'destructive', icon: XCircle, label: '失败' },
  REVOKED: { variant: 'outline', icon: StopCircle, label: '已撤销' },
}

function stateMeta(s) {
  return STATE_META[s] || { variant: 'muted', icon: Clock, label: s || '未知' }
}

function shortId(id) {
  return id ? id.slice(0, 12) + '…' : '—'
}

function argsSummary(args) {
  if (!args || !Object.keys(args).length) return '—'
  return Object.entries(args)
    .map(([k, v]) => `${k}=${v}`)
    .join(', ')
}

function resultSummary(result) {
  if (!result) return '—'
  if (result.error) return result.error.slice(0, 60)
  return Object.entries(result)
    .filter(([k]) => k !== 'return_code')
    .map(([k, v]) => `${k}=${v}`)
    .join(', ') || '—'
}

async function load() {
  try {
    const { data } = await adminApi.listTasks(50)
    tasks.value = data.tasks || []
    workers.value = data.workers || { active: 0, scheduled: 0, reserved: 0 }
  } catch (e) {
    console.error('Failed to load tasks', e)
  } finally {
    loading.value = false
  }
}

async function revoke(taskId) {
  try {
    await adminApi.revokeTask(taskId)
    toast.success('已发送撤销指令')
    load()
  } catch (e) {
    toast.error(e.response?.data?.detail || '撤销失败')
  }
}

function toggleAuto() {
  autoRefresh.value = !autoRefresh.value
  if (autoRefresh.value) startTimer()
  else stopTimer()
}

function startTimer() {
  stopTimer()
  timer = setInterval(load, 5000)
}

function stopTimer() {
  if (timer) { clearInterval(timer); timer = null }
}

onMounted(() => { load(); startTimer() })
onUnmounted(stopTimer)
</script>

<template>
  <div class="max-w-4xl space-y-6">
    <header class="flex items-center justify-between gap-3 flex-wrap">
      <div class="space-y-1">
        <h1 class="font-serif text-3xl font-semibold tracking-tight">任务管理</h1>
        <p class="text-sm text-muted-foreground">监控 Celery 后台任务 · 取消正在执行的任务</p>
      </div>
      <div class="flex items-center gap-2">
        <Button
          :variant="autoRefresh ? 'default' : 'outline'"
          size="sm"
          @click="toggleAuto"
        >
          <RefreshCw :class="['size-4 mr-1', autoRefresh && 'animate-spin']" />
          {{ autoRefresh ? '自动刷新中' : '自动刷新' }}
        </Button>
        <Button variant="outline" size="sm" :disabled="loading" @click="load">
          <RefreshCw class="size-4" />
        </Button>
      </div>
    </header>

    <div class="grid grid-cols-3 gap-3">
      <Card class="p-4 text-center">
        <div class="text-[10px] uppercase tracking-widest text-muted-foreground">活跃任务</div>
        <div class="font-serif text-2xl tabular-nums mt-1 text-blue-500">{{ workers.active }}</div>
      </Card>
      <Card class="p-4 text-center">
        <div class="text-[10px] uppercase tracking-widest text-muted-foreground">计划中</div>
        <div class="font-serif text-2xl tabular-nums mt-1 text-amber-500">{{ workers.scheduled }}</div>
      </Card>
      <Card class="p-4 text-center">
        <div class="text-[10px] uppercase tracking-widest text-muted-foreground">已保留</div>
        <div class="font-serif text-2xl tabular-nums mt-1 text-muted-foreground">{{ workers.reserved }}</div>
      </Card>
    </div>

    <Card class="overflow-hidden">
      <CardHeader class="px-5 py-4">
        <div class="flex items-center gap-2">
          <ListTodo class="size-4 text-muted-foreground" />
          <CardTitle class="text-base">最近任务</CardTitle>
          <span class="text-xs text-muted-foreground ml-1">(最近 {{ tasks.length }} 条)</span>
        </div>
      </CardHeader>
      <CardContent class="p-0">
        <div v-if="loading" class="p-6 space-y-3">
          <Skeleton v-for="i in 6" :key="i" class="h-10" />
        </div>
        <div v-else-if="!tasks.length" class="p-10 text-center text-sm text-muted-foreground">
          还没有任务记录
        </div>
        <div v-else class="overflow-x-auto">
          <table class="w-full text-sm">
            <thead>
              <tr class="border-b bg-muted/40 text-left">
                <th class="px-4 py-2.5 text-[10px] uppercase tracking-wider text-muted-foreground font-medium">任务</th>
                <th class="px-4 py-2.5 text-[10px] uppercase tracking-wider text-muted-foreground font-medium">ID</th>
                <th class="px-4 py-2.5 text-[10px] uppercase tracking-wider text-muted-foreground font-medium">状态</th>
                <th class="px-4 py-2.5 text-[10px] uppercase tracking-wider text-muted-foreground font-medium hidden md:table-cell">参数</th>
                <th class="px-4 py-2.5 text-[10px] uppercase tracking-wider text-muted-foreground font-medium hidden lg:table-cell">结果</th>
                <th class="px-4 py-2.5 text-[10px] uppercase tracking-wider text-muted-foreground font-medium hidden lg:table-cell">完成时间</th>
                <th class="px-4 py-2.5 text-[10px] uppercase tracking-wider text-muted-foreground font-medium w-10"></th>
              </tr>
            </thead>
            <tbody class="divide-y">
              <tr
                v-for="t in tasks"
                :key="t.task_id"
                class="hover:bg-muted/30 transition-colors"
              >
                <td class="px-4 py-2.5 font-mono text-xs">{{ t.task_name }}</td>
                <td class="px-4 py-2.5 font-mono text-[11px] text-muted-foreground">{{ shortId(t.task_id) }}</td>
                <td class="px-4 py-2.5">
                  <Badge :variant="stateMeta(t.state).variant" class="text-[10px] uppercase tracking-wider inline-flex items-center gap-1">
                    <component :is="stateMeta(t.state).icon" class="size-3" />
                    {{ stateMeta(t.state).label }}
                  </Badge>
                </td>
                <td class="px-4 py-2.5 text-xs text-muted-foreground hidden md:table-cell max-w-[160px] truncate">
                  {{ argsSummary(t.args) }}
                </td>
                <td class="px-4 py-2.5 text-xs text-muted-foreground hidden lg:table-cell max-w-[160px] truncate">
                  {{ resultSummary(t.result) }}
                </td>
                <td class="px-4 py-2.5 text-xs text-muted-foreground hidden lg:table-cell whitespace-nowrap">
                  {{ t.date_done ? new Date(t.date_done).toLocaleString('zh-CN') : '—' }}
                </td>
                <td class="px-4 py-2.5">
                  <Button
                    v-if="t.state === 'STARTED' || t.state === 'PENDING'"
                    variant="ghost"
                    size="icon"
                    class="h-7 w-7 text-destructive"
                    title="撤销任务"
                    @click="revoke(t.task_id)"
                  >
                    <StopCircle class="size-4" />
                  </Button>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </CardContent>
    </Card>
  </div>
</template>

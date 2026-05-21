<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { adminApi } from '@/api'
import { RefreshCw, Search as SearchIcon, Check, X } from 'lucide-vue-next'
import Card from '@/components/ui/Card.vue'
import Button from '@/components/ui/Button.vue'
import Badge from '@/components/ui/Badge.vue'
import Input from '@/components/ui/Input.vue'
import Table from '@/components/ui/Table.vue'
import TableHeader from '@/components/ui/TableHeader.vue'
import TableBody from '@/components/ui/TableBody.vue'
import TableRow from '@/components/ui/TableRow.vue'
import TableHead from '@/components/ui/TableHead.vue'
import TableCell from '@/components/ui/TableCell.vue'
import Skeleton from '@/components/ui/Skeleton.vue'
import EmptyState from '@/components/common/EmptyState.vue'
import { toast } from 'vue-sonner'
import { cn, formatDate, formatNumber } from '@/lib/utils'

defineOptions({ name: 'AdminFeedbacksView' })

const PAGE_SIZE = 20

const STATUS_OPTIONS = ['open', 'acknowledged', 'closed']
const STATUS_LABEL = { open: '待处理', acknowledged: '已确认', closed: '已关闭' }
const STATUS_TONE = { open: 'bg-amber-500', acknowledged: 'bg-blue-500 animate-pulse', closed: 'bg-green-500' }
const CATEGORY_LABEL = { bug: '问题反馈', feature: '功能建议', other: '其他' }

const filters = reactive({ q: '', status: '', category: '' })
const offset = ref(0)
const items = ref([])
const total = ref(0)
const loading = ref(false)
const errored = ref(false)
const busySet = ref(new Set())
const editId = ref(null)
const editStatus = ref('')
const editNote = ref('')

const pageInfo = computed(() => {
  if (total.value === 0) return ''
  const s = offset.value + 1
  const e = Math.min(offset.value + PAGE_SIZE, total.value)
  return `${formatNumber(s)} - ${formatNumber(e)} / ${formatNumber(total.value)}`
})

const totalPages = computed(() => Math.ceil(total.value / PAGE_SIZE))

async function load(reset = false) {
  if (reset) offset.value = 0
  loading.value = true
  errored.value = false
  try {
    const params = { limit: PAGE_SIZE, offset: offset.value }
    if (filters.status) params.status = filters.status
    if (filters.category) params.category = filters.category
    const { data } = await adminApi.listFeedbacks(params)
    items.value = data.items || []
    total.value = data.total || 0
  } catch (e) {
    errored.value = true
    toast.error(e.response?.data?.detail || '加载反馈失败')
  } finally {
    loading.value = false
  }
}

function startEdit(fb) {
  editId.value = fb.id
  editStatus.value = fb.status
  editNote.value = fb.admin_note || ''
}

function cancelEdit() {
  editId.value = null
  editStatus.value = ''
  editNote.value = ''
}

async function saveEdit(fb) {
  busySet.value.add(fb.id)
  try {
    const payload = {}
    if (editStatus.value !== fb.status) payload.status = editStatus.value
    if (editNote.value !== (fb.admin_note || '')) payload.admin_note = editNote.value
    if (Object.keys(payload).length === 0) { cancelEdit(); return }
    const { data } = await adminApi.updateFeedback(fb.id, payload)
    const idx = items.value.findIndex(i => i.id === fb.id)
    if (idx >= 0) items.value[idx] = data
    cancelEdit()
    toast.success('已更新')
  } catch (e) {
    toast.error(e.response?.data?.detail || '更新失败')
  } finally {
    busySet.value.delete(fb.id)
  }
}

async function quickStatus(fb, status) {
  busySet.value.add(fb.id)
  try {
    const { data } = await adminApi.updateFeedback(fb.id, { status })
    const idx = items.value.findIndex(i => i.id === fb.id)
    if (idx >= 0) items.value[idx] = data
    toast.success(`已标记为「${STATUS_LABEL[status]}」`)
  } catch (e) {
    toast.error(e.response?.data?.detail || '更新失败')
  } finally {
    busySet.value.delete(fb.id)
  }
}

function prevPage() { if (offset.value > 0) { offset.value = Math.max(0, offset.value - PAGE_SIZE); load() } }
function nextPage() { if (offset.value + PAGE_SIZE < total.value) { offset.value += PAGE_SIZE; load() } }

onMounted(() => load())
</script>

<template>
  <div class="flex min-h-0 flex-col gap-4 px-6 py-5 max-w-prose mx-auto w-full">
    <div class="flex items-center justify-between">
      <div>
        <h1 class="text-2xl font-serif font-semibold tracking-tight">用户反馈</h1>
        <p class="text-sm text-muted-foreground mt-0.5">查看和处理用户反馈建议</p>
      </div>
      <Button variant="outline" size="sm" :disabled="loading" @click="load(true)">
        <RefreshCw :class="cn('size-3.5', loading && 'animate-spin')" />
        刷新
      </Button>
    </div>

    <div class="flex flex-wrap items-center gap-2">
      <select
        v-model="filters.status"
        class="rounded-md border border-input bg-background px-3 py-1.5 text-sm shadow-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
        @change="load(true)"
      >
        <option value="">全部状态</option>
        <option v-for="s in STATUS_OPTIONS" :key="s" :value="s">{{ STATUS_LABEL[s] }}</option>
      </select>
      <select
        v-model="filters.category"
        class="rounded-md border border-input bg-background px-3 py-1.5 text-sm shadow-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
        @change="load(true)"
      >
        <option value="">全部分类</option>
        <option value="bug">{{ CATEGORY_LABEL.bug }}</option>
        <option value="feature">{{ CATEGORY_LABEL.feature }}</option>
        <option value="other">{{ CATEGORY_LABEL.other }}</option>
      </select>
    </div>

    <Card class="overflow-hidden">
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead class="w-16">ID</TableHead>
            <TableHead>用户</TableHead>
            <TableHead class="w-20">分类</TableHead>
            <TableHead>内容</TableHead>
            <TableHead class="w-16">状态</TableHead>
            <TableHead class="w-32">时间</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          <template v-if="loading && items.length === 0">
            <TableRow v-for="k in 5" :key="k"><TableCell colspan="6"><Skeleton class="h-8 w-full" /></TableCell></TableRow>
          </template>
          <template v-else-if="!loading && items.length === 0 && !errored">
            <TableRow><TableCell colspan="6"><EmptyState message="暂无反馈记录" /></TableCell></TableRow>
          </template>
          <template v-else-if="errored">
            <TableRow><TableCell colspan="6"><div class="text-center text-sm text-muted-foreground py-8">加载失败，请稍后重试</div></TableCell></TableRow>
          </template>
          <template v-else>
            <template v-for="fb in items" :key="fb.id">
              <TableRow class="cursor-pointer hover:bg-accent/50" @click="editId !== fb.id ? startEdit(fb) : undefined">
                <TableCell class="font-mono text-xs text-muted-foreground">#{{ fb.id }}</TableCell>
                <TableCell>
                  <div class="text-sm font-medium">{{ fb.username || fb.user_id?.slice(0, 8) }}</div>
                  <div v-if="fb.email" class="text-xs text-muted-foreground">{{ fb.email }}</div>
                </TableCell>
                <TableCell><Badge variant="outline" class="text-xs">{{ CATEGORY_LABEL[fb.category] || fb.category }}</Badge></TableCell>
                <TableCell>
                  <div class="text-sm line-clamp-2 max-w-xs" :title="fb.content">{{ fb.content }}</div>
                  <div v-if="fb.admin_note" class="text-xs text-muted-foreground mt-0.5">备注：{{ fb.admin_note }}</div>
                </TableCell>
                <TableCell>
                  <div class="flex items-center gap-1.5">
                    <span :class="cn('inline-block size-2 rounded-full shrink-0', STATUS_TONE[fb.status] || 'bg-muted')" />
                    <span class="text-xs">{{ STATUS_LABEL[fb.status] || fb.status }}</span>
                  </div>
                </TableCell>
                <TableCell class="text-xs text-muted-foreground whitespace-nowrap">{{ formatDate(fb.created_at) }}</TableCell>
              </TableRow>

              <TableRow v-if="editId === fb.id" class="bg-accent/30">
                <TableCell colspan="6">
                  <div class="flex flex-wrap items-end gap-3 py-1">
                    <div class="flex-1 min-w-0">
                      <label class="text-xs font-medium mb-1 block">状态</label>
                      <select
                        v-model="editStatus"
                        class="rounded-md border border-input bg-background px-3 py-1.5 text-sm w-full"
                      >
                        <option v-for="s in STATUS_OPTIONS" :key="s" :value="s">{{ STATUS_LABEL[s] }}</option>
                      </select>
                    </div>
                    <div class="flex-[2] min-w-0">
                      <label class="text-xs font-medium mb-1 block">管理员备注</label>
                      <textarea
                        v-model="editNote"
                        rows="2"
                        class="flex w-full rounded-md border border-input bg-background px-3 py-1.5 text-sm resize-none"
                      />
                    </div>
                    <div class="flex gap-1.5">
                      <Button size="sm" :disabled="busySet.has(fb.id)" @click="saveEdit(fb)">
                        <Check class="size-3.5" /> 保存
                      </Button>
                      <Button variant="outline" size="sm" @click="cancelEdit">
                        <X class="size-3.5" /> 取消
                      </Button>
                    </div>
                  </div>
                </TableCell>
              </TableRow>
            </template>
          </template>
        </TableBody>
      </Table>
    </Card>

    <div v-if="total > PAGE_SIZE" class="flex items-center justify-between">
      <div class="text-sm text-muted-foreground">{{ pageInfo }}</div>
      <div class="flex gap-2">
        <Button variant="outline" size="sm" :disabled="offset === 0" @click="prevPage">上一页</Button>
        <Button variant="outline" size="sm" :disabled="offset + PAGE_SIZE >= total" @click="nextPage">下一页</Button>
      </div>
    </div>
  </div>
</template>

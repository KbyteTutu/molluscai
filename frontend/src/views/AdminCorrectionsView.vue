<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { adminApi } from '@/api'
import { RefreshCw, Check, X } from 'lucide-vue-next'
import Card from '@/components/ui/Card.vue'
import Button from '@/components/ui/Button.vue'
import Badge from '@/components/ui/Badge.vue'
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

defineOptions({ name: 'AdminCorrectionsView' })

const PAGE_SIZE = 20

const STATUS_OPTIONS = ['pending', 'approved', 'rejected']
const STATUS_LABEL = { pending: '待审核', approved: '已通过', rejected: '已驳回' }
const STATUS_TONE = { pending: 'bg-amber-500', approved: 'bg-green-500', rejected: 'bg-red-500' }
const TARGET_LABEL = { taxon: '物种', document: '文献', auction: '拍卖' }

const filters = reactive({ status: '', target_type: '' })
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

async function load(reset = false) {
  if (reset) offset.value = 0
  loading.value = true
  errored.value = false
  try {
    const params = { limit: PAGE_SIZE, offset: offset.value }
    if (filters.status) params.status = filters.status
    if (filters.target_type) params.target_type = filters.target_type
    const { data } = await adminApi.listCorrections(params)
    items.value = data.items || []
    total.value = data.total || 0
  } catch (e) {
    errored.value = true
    toast.error(e.response?.data?.detail || '加载纠错记录失败')
  } finally {
    loading.value = false
  }
}

function startEdit(c) {
  editId.value = c.id
  editStatus.value = c.status
  editNote.value = c.admin_note || ''
}

function cancelEdit() {
  editId.value = null
  editStatus.value = ''
  editNote.value = ''
}

async function saveEdit(c) {
  busySet.value.add(c.id)
  try {
    const payload = {}
    if (editStatus.value !== c.status) payload.status = editStatus.value
    if (editNote.value !== (c.admin_note || '')) payload.admin_note = editNote.value
    if (Object.keys(payload).length === 0) { cancelEdit(); return }
    const { data } = await adminApi.updateCorrection(c.id, payload)
    const idx = items.value.findIndex(i => i.id === c.id)
    if (idx >= 0) items.value[idx] = data
    cancelEdit()
    toast.success('已更新')
  } catch (e) {
    toast.error(e.response?.data?.detail || '更新失败')
  } finally {
    busySet.value.delete(c.id)
  }
}

function prevPage() { if (offset.value > 0) { offset.value = Math.max(0, offset.value - PAGE_SIZE); load() } }
function nextPage() { if (offset.value + PAGE_SIZE < total.value) { offset.value += PAGE_SIZE; load() } }

onMounted(() => load())
</script>

<template>
  <div class="space-y-6">
    <div class="flex items-center justify-between">
      <div>
        <h1 class="text-2xl font-serif font-semibold tracking-tight">纠错管理</h1>
        <p class="text-sm text-muted-foreground mt-0.5">审核用户提交的信息纠错</p>
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
        v-model="filters.target_type"
        class="rounded-md border border-input bg-background px-3 py-1.5 text-sm shadow-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
        @change="load(true)"
      >
        <option value="">全部类型</option>
        <option value="taxon">物种</option>
        <option value="document">文献</option>
        <option value="auction">拍卖</option>
      </select>
    </div>

    <Card class="overflow-hidden">
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead class="w-16">ID</TableHead>
            <TableHead>用户</TableHead>
            <TableHead class="w-20">类型</TableHead>
            <TableHead>纠错目标</TableHead>
            <TableHead>字段 · 原值 → 建议值</TableHead>
            <TableHead class="w-16">状态</TableHead>
            <TableHead class="w-32">时间</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          <template v-if="loading && items.length === 0">
            <TableRow v-for="k in 5" :key="k"><TableCell colspan="7"><Skeleton class="h-8 w-full" /></TableCell></TableRow>
          </template>
          <template v-else-if="!loading && items.length === 0 && !errored">
            <TableRow><TableCell colspan="7"><EmptyState message="暂无纠错记录" /></TableCell></TableRow>
          </template>
          <template v-else-if="errored">
            <TableRow><TableCell colspan="7"><div class="text-center text-sm text-muted-foreground py-8">加载失败，请稍后重试</div></TableCell></TableRow>
          </template>
          <template v-else>
            <template v-for="c in items" :key="c.id">
              <TableRow class="cursor-pointer hover:bg-accent/50" @click="editId !== c.id ? startEdit(c) : undefined">
                <TableCell class="font-mono text-xs text-muted-foreground">#{{ c.id }}</TableCell>
                <TableCell>
                  <div class="text-sm font-medium">{{ c.username || c.user_id?.slice(0, 8) }}</div>
                  <div v-if="c.email" class="text-xs text-muted-foreground">{{ c.email }}</div>
                </TableCell>
                <TableCell><Badge variant="outline" class="text-xs">{{ TARGET_LABEL[c.target_type] || c.target_type }}</Badge></TableCell>
                <TableCell>
                  <div class="text-sm font-medium">{{ c.target_title || `#${c.target_id}` }}</div>
                  <div class="text-xs text-muted-foreground font-mono">{{ c.target_type }}:{{ c.target_id }}</div>
                </TableCell>
                <TableCell>
                  <div class="text-sm">
                    <span class="font-medium">{{ c.field_name }}</span>
                  </div>
                  <div class="text-xs text-muted-foreground line-through" v-if="c.current_value">{{ c.current_value }}</div>
                  <div class="text-sm text-foreground">→ {{ c.suggested_value }}</div>
                  <div v-if="c.note" class="text-xs text-muted-foreground mt-0.5 italic">{{ c.note }}</div>
                </TableCell>
                <TableCell>
                  <div class="flex items-center gap-1.5">
                    <span :class="cn('inline-block size-2 rounded-full shrink-0', STATUS_TONE[c.status] || 'bg-muted')" />
                    <span class="text-xs">{{ STATUS_LABEL[c.status] || c.status }}</span>
                  </div>
                </TableCell>
                <TableCell class="text-xs text-muted-foreground whitespace-nowrap">{{ formatDate(c.created_at) }}</TableCell>
              </TableRow>

              <TableRow v-if="editId === c.id" class="bg-accent/30">
                <TableCell colspan="7">
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
                      <Button size="sm" :disabled="busySet.has(c.id)" @click="saveEdit(c)">
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

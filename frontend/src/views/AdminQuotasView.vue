<script setup>
import { ref, onMounted, computed } from 'vue'
import { adminApi } from '@/api'
import { RefreshCw, Crown, Save } from 'lucide-vue-next'
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
import EmptyState from '@/components/common/EmptyState.vue'
import Skeleton from '@/components/ui/Skeleton.vue'
import { toast } from 'vue-sonner'

const EDITABLE_FIELDS = [
  'hourly_ai_limit',
  'hourly_auction_limit',
  'hourly_taxa_limit',
  'daily_ai_limit',
  'daily_auction_limit',
  'daily_taxa_limit',
  'daily_rag_limit',
  'rate_limit_per_min'
]

const ROLE_ORDER = ['user', 'vip', 'doc_admin', 'superadmin']
const ROLE_LABEL = {
  user: '普通用户',
  vip: 'VIP',
  doc_admin: '文档管理员',
  superadmin: '超级管理员'
}

const rows = ref([])
const originals = ref({})
const saving = ref({})
const loading = ref(false)
const errored = ref(false)

const sortedRows = computed(() => {
  const idx = (r) => {
    const i = ROLE_ORDER.indexOf(r.role)
    return i === -1 ? 999 : i
  }
  return [...rows.value].sort((a, b) => idx(a) - idx(b))
})

async function load() {
  loading.value = true
  errored.value = false
  try {
    const { data } = await adminApi.listQuotas()
    rows.value = (data || []).map(r => ({ ...r }))
    originals.value = Object.fromEntries(rows.value.map(r => [r.role, { ...r }]))
  } catch (e) {
    errored.value = true
    toast.error(e.response?.data?.detail || '加载配额失败')
  } finally {
    loading.value = false
  }
}

function isDirty(row) {
  const orig = originals.value[row.role]
  if (!orig) return false
  return EDITABLE_FIELDS.some(f => Number(row[f]) !== Number(orig[f]))
}

function dirtyDiff(row) {
  const orig = originals.value[row.role]
  const out = {}
  for (const f of EDITABLE_FIELDS) {
    const next = Number(row[f])
    if (Number.isFinite(next) && next !== Number(orig[f])) out[f] = next
  }
  return out
}

function onInput(row, field, raw) {
  const n = parseInt(raw, 10)
  row[field] = Number.isFinite(n) ? n : raw
}

function resetRow(row) {
  const orig = originals.value[row.role]
  if (!orig) return
  for (const f of EDITABLE_FIELDS) row[f] = orig[f]
}

async function saveRow(row) {
  const diff = dirtyDiff(row)
  if (!Object.keys(diff).length) return
  for (const k in diff) {
    if (!Number.isFinite(diff[k]) || diff[k] < -1) {
      toast.error(`字段 ${k} 必须为 ≥ -1 的整数`)
      return
    }
  }
  saving.value = { ...saving.value, [row.role]: true }
  try {
    const { data } = await adminApi.updateQuota(row.role, diff)
    Object.assign(row, data)
    originals.value = { ...originals.value, [row.role]: { ...data } }
    toast.success(`已更新「${ROLE_LABEL[row.role] || row.role}」配额`)
  } catch (e) {
    toast.error(e.response?.data?.detail || '保存失败')
  } finally {
    saving.value = { ...saving.value, [row.role]: false }
  }
}

function roleBadgeVariant(role) {
  if (role === 'superadmin') return 'outline'
  if (role === 'vip') return 'default'
  return 'secondary'
}

onMounted(load)
</script>

<template>
  <div class="space-y-6">
    <header class="flex items-end justify-between flex-wrap gap-3">
      <div class="space-y-1">
        <h1 class="font-serif text-3xl font-semibold tracking-tight">配额管理</h1>
        <p class="text-sm text-muted-foreground">按角色编辑每日 / 每小时检索配额 · 仅超级管理员可见</p>
      </div>
      <Button variant="outline" size="sm" @click="load" :disabled="loading">
        <RefreshCw class="size-4" :class="loading && 'animate-spin'" /> 刷新
      </Button>
    </header>

    <Card class="p-3 bg-muted/30 border-dashed">
      <p class="text-xs text-muted-foreground leading-relaxed">
        <span class="font-medium text-foreground/80">约定:</span>
        <span class="font-mono mx-1">-1</span> 表示不限，
        <span class="font-mono mx-1">0</span> 表示禁用，正整数为窗口内请求次数上限。
      </p>
    </Card>

    <Card v-if="loading && !rows.length" class="overflow-hidden">
      <div class="p-4 space-y-3">
        <Skeleton v-for="i in 4" :key="i" class="h-12 w-full" />
      </div>
    </Card>

    <EmptyState
      v-else-if="errored && !rows.length"
      title="无法加载配额"
      description="请检查后端连接后点击刷新重试"
    />

    <EmptyState
      v-else-if="!rows.length"
      title="暂无配额配置"
      description="后端未返回任何角色配额"
    />

    <Card v-else class="overflow-hidden">
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead class="sticky left-0 bg-card z-10 min-w-[140px]">角色</TableHead>
            <TableHead class="text-right">每小时·智能</TableHead>
            <TableHead class="text-right">每小时·拍卖</TableHead>
            <TableHead class="text-right">每小时·物种</TableHead>
            <TableHead class="text-right">每日·智能</TableHead>
            <TableHead class="text-right">每日·拍卖</TableHead>
            <TableHead class="text-right">每日·物种</TableHead>
            <TableHead class="text-right">每日·RAG</TableHead>
            <TableHead class="text-right">每分钟·全局</TableHead>
            <TableHead class="text-right min-w-[160px]">操作</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          <TableRow v-for="row in sortedRows" :key="row.role">
            <TableCell class="sticky left-0 bg-card z-10">
              <div class="flex items-center gap-2">
                <Crown v-if="row.role === 'vip'" class="size-3.5 text-amber-500" />
                <Badge
                  :variant="roleBadgeVariant(row.role)"
                  :class="row.role === 'superadmin' ? 'border-primary/60 text-primary' : ''"
                >
                  {{ ROLE_LABEL[row.role] || row.role }}
                </Badge>
                <span class="text-[10px] text-muted-foreground font-mono">{{ row.role }}</span>
              </div>
            </TableCell>
            <TableCell v-for="field in EDITABLE_FIELDS" :key="field" class="text-right align-top">
              <div class="inline-flex flex-col items-end">
                <Input
                  type="number"
                  :min="-1"
                  step="1"
                  :model-value="row[field]"
                  @update:model-value="(v) => onInput(row, field, v)"
                  class="h-8 w-20 text-right tabular-nums font-mono"
                />
                <span
                  v-if="Number(row[field]) === -1"
                  class="text-[9px] text-muted-foreground mt-0.5 leading-none"
                >∞ 不限</span>
                <span
                  v-else-if="Number(row[field]) === 0"
                  class="text-[9px] text-destructive mt-0.5 leading-none"
                >已禁用</span>
              </div>
            </TableCell>
            <TableCell class="text-right">
              <div class="flex items-center justify-end gap-2">
                <Badge v-if="isDirty(row)" variant="outline" class="text-[10px] border-amber-500/60 text-amber-600">
                  已修改
                </Badge>
                <Button
                  v-if="isDirty(row)"
                  variant="ghost"
                  size="sm"
                  @click="resetRow(row)"
                  :disabled="saving[row.role]"
                >撤销</Button>
                <Button
                  size="sm"
                  :variant="isDirty(row) ? 'default' : 'outline'"
                  :disabled="!isDirty(row) || saving[row.role]"
                  @click="saveRow(row)"
                >
                  <Save class="size-3.5" />
                  {{ saving[row.role] ? '保存中…' : '保存' }}
                </Button>
              </div>
            </TableCell>
          </TableRow>
        </TableBody>
      </Table>
    </Card>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted, watch } from 'vue'
import { adminApi } from '@/api'
import { useAuthStore } from '@/stores/auth'
import { RefreshCw, Lock, Unlock, KeyRound, Search as SearchIcon, X, Check } from 'lucide-vue-next'
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
import { cn, formatNumber } from '@/lib/utils'

defineOptions({ name: 'AdminUsersView' })

const PAGE_SIZE = 20
const ROLE_LABEL = {
  user: '普通用户',
  vip: 'VIP',
  doc_admin: '文档管理员',
  superadmin: '超级管理员'
}
const ROLE_OPTIONS = ['user', 'vip', 'doc_admin', 'superadmin']

const auth = useAuthStore()
const myId = computed(() => auth.currentUser?.id)

const filters = reactive({ q: '', role: '', is_active: '' })
const offset = ref(0)
const items = ref([])
const total = ref(0)
const loading = ref(false)
const errored = ref(false)

const busy = ref({})
const pwdOpenFor = ref(null)
const pwdInput = ref('')
const pwdShow = ref(false)

const pageInfo = computed(() => {
  if (total.value === 0) return ''
  const s = offset.value + 1
  const e = Math.min(offset.value + PAGE_SIZE, total.value)
  return `${formatNumber(s)} – ${formatNumber(e)} / ${formatNumber(total.value)}`
})

function setBusy(id, key, v) {
  const next = { ...busy.value[id], [key]: v }
  busy.value = { ...busy.value, [id]: next }
}
function isBusy(id, key) {
  return Boolean(busy.value[id]?.[key])
}

async function load(reset = false) {
  if (reset) offset.value = 0
  loading.value = true
  errored.value = false
  try {
    const params = { limit: PAGE_SIZE, offset: offset.value }
    if (filters.q.trim()) params.q = filters.q.trim()
    if (filters.role) params.role = filters.role
    if (filters.is_active !== '') params.is_active = filters.is_active === 'true'
    const { data } = await adminApi.listUsers(params)
    items.value = data.items || []
    total.value = data.total || 0
  } catch (e) {
    errored.value = true
    toast.error(e.response?.data?.detail || '加载用户失败')
  } finally {
    loading.value = false
  }
}

function nextPage() {
  if (offset.value + PAGE_SIZE >= total.value) return
  offset.value += PAGE_SIZE
  load(false)
}
function prevPage() {
  if (offset.value === 0) return
  offset.value = Math.max(0, offset.value - PAGE_SIZE)
  load(false)
}

async function changeRole(row, newRole) {
  if (newRole === row.role) return
  if (row.id === myId.value && row.role === 'superadmin' && newRole !== 'superadmin') {
    toast.error('不能降级自己的超级管理员权限')
    return
  }
  if (newRole === 'superadmin') {
    if (!confirm(`确认将「${row.username}」设为超级管理员？该角色拥有全部权限。`)) return
  }
  setBusy(row.id, 'role', true)
  try {
    const { data } = await adminApi.updateUser(row.id, { role: newRole })
    Object.assign(row, data)
    toast.success(`已更新「${row.username}」角色为 ${ROLE_LABEL[newRole] || newRole}`)
  } catch (e) {
    toast.error(e.response?.data?.detail || '更新角色失败')
  } finally {
    setBusy(row.id, 'role', false)
  }
}

async function toggleLock(row) {
  if (row.id === myId.value && row.is_active) {
    toast.error('不能锁定自己的账号')
    return
  }
  const next = !row.is_active
  const verb = next ? '解锁' : '锁定'
  if (!confirm(`确认${verb}用户「${row.username}」？`)) return
  setBusy(row.id, 'lock', true)
  try {
    const { data } = await adminApi.updateUser(row.id, { is_active: next })
    Object.assign(row, data)
    toast.success(`已${verb}「${row.username}」`)
  } catch (e) {
    toast.error(e.response?.data?.detail || `${verb}失败`)
  } finally {
    setBusy(row.id, 'lock', false)
  }
}

function openPwdPanel(row) {
  pwdOpenFor.value = row.id
  pwdInput.value = ''
  pwdShow.value = false
}
function closePwdPanel() {
  pwdOpenFor.value = null
  pwdInput.value = ''
  pwdShow.value = false
}

async function submitResetPwd(row) {
  const pwd = pwdInput.value
  if (!pwd || pwd.length < 8) {
    toast.error('密码至少 8 个字符')
    return
  }
  if (pwd.length > 128) {
    toast.error('密码不超过 128 个字符')
    return
  }
  setBusy(row.id, 'pwd', true)
  try {
    await adminApi.resetUserPassword(row.id, pwd)
    toast.success(`已重置「${row.username}」的密码`)
    closePwdPanel()
  } catch (e) {
    toast.error(e.response?.data?.detail || '重置密码失败')
  } finally {
    setBusy(row.id, 'pwd', false)
  }
}

function roleBadgeVariant(role) {
  if (role === 'superadmin') return 'outline'
  if (role === 'vip') return 'default'
  if (role === 'doc_admin') return 'secondary'
  return 'secondary'
}

function fmtDate(s) {
  if (!s) return ''
  const d = new Date(s)
  if (Number.isNaN(d.getTime())) return s
  const yyyy = d.getFullYear()
  const mm = String(d.getMonth() + 1).padStart(2, '0')
  const dd = String(d.getDate()).padStart(2, '0')
  const hh = String(d.getHours()).padStart(2, '0')
  const mi = String(d.getMinutes()).padStart(2, '0')
  return `${yyyy}-${mm}-${dd} ${hh}:${mi}`
}

let searchTimer = null
watch(() => filters.q, () => {
  if (searchTimer) clearTimeout(searchTimer)
  searchTimer = setTimeout(() => load(true), 300)
})
watch(() => [filters.role, filters.is_active], () => load(true))

onMounted(() => load(true))
</script>

<template>
  <div class="space-y-6">
    <header class="flex items-end justify-between flex-wrap gap-3">
      <div class="space-y-1">
        <h1 class="font-serif text-3xl font-semibold tracking-tight">用户管理</h1>
        <p class="text-sm text-muted-foreground">管理用户角色、锁定状态与密码重置 · 仅超级管理员可见</p>
      </div>
      <Button variant="outline" size="sm" @click="load(true)" :disabled="loading">
        <RefreshCw class="size-4" :class="loading && 'animate-spin'" /> 刷新
      </Button>
    </header>

    <Card class="p-3">
      <div class="grid gap-3 sm:grid-cols-[1fr_auto_auto]">
        <div class="relative">
          <SearchIcon class="absolute left-2.5 top-1/2 -translate-y-1/2 size-4 text-muted-foreground" />
          <Input
            v-model="filters.q"
            placeholder="搜索用户名或邮箱"
            class="pl-8"
          />
        </div>
        <select
          v-model="filters.role"
          class="h-9 rounded-md border bg-background px-2 text-sm"
        >
          <option value="">全部角色</option>
          <option v-for="r in ROLE_OPTIONS" :key="r" :value="r">{{ ROLE_LABEL[r] }}</option>
        </select>
        <select
          v-model="filters.is_active"
          class="h-9 rounded-md border bg-background px-2 text-sm"
        >
          <option value="">全部状态</option>
          <option value="true">启用</option>
          <option value="false">已锁定</option>
        </select>
      </div>
    </Card>

    <Card v-if="loading && !items.length" class="overflow-hidden">
      <div class="p-4 space-y-3">
        <Skeleton v-for="i in 6" :key="i" class="h-12 w-full" />
      </div>
    </Card>

    <EmptyState
      v-else-if="errored && !items.length"
      title="无法加载用户"
      description="请检查后端连接后点击刷新重试"
    />
    <EmptyState
      v-else-if="!items.length"
      title="未找到匹配的用户"
      description="尝试调整搜索条件或筛选器"
    />

    <Card v-else class="overflow-hidden">
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead class="w-[180px]">用户名</TableHead>
            <TableHead>邮箱</TableHead>
            <TableHead class="w-[150px]">角色</TableHead>
            <TableHead class="w-[100px]">状态</TableHead>
            <TableHead class="w-[150px]">注册时间</TableHead>
            <TableHead class="text-right w-[260px]">操作</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          <template v-for="row in items" :key="row.id">
            <TableRow :class="!row.is_active && 'bg-muted/40'">
              <TableCell class="font-medium">
                <div class="flex items-center gap-2">
                  <span class="truncate">{{ row.username }}</span>
                  <Badge v-if="row.id === myId" variant="outline" class="text-[10px]">本人</Badge>
                </div>
              </TableCell>
              <TableCell class="text-sm text-muted-foreground truncate">{{ row.email }}</TableCell>
              <TableCell>
                <select
                  :value="row.role"
                  @change="changeRole(row, $event.target.value)"
                  :disabled="isBusy(row.id, 'role') || (row.id === myId && row.role === 'superadmin')"
                  class="h-8 w-full rounded-md border bg-background px-2 text-xs disabled:opacity-60"
                >
                  <option v-for="r in ROLE_OPTIONS" :key="r" :value="r">{{ ROLE_LABEL[r] }}</option>
                </select>
              </TableCell>
              <TableCell>
                <Badge v-if="row.is_active" variant="secondary" class="text-[10px]">启用</Badge>
                <Badge v-else variant="outline" class="text-[10px] border-destructive/60 text-destructive">已锁定</Badge>
              </TableCell>
              <TableCell class="text-xs text-muted-foreground tabular-nums">{{ fmtDate(row.created_at) }}</TableCell>
              <TableCell class="text-right">
                <div class="flex items-center justify-end gap-1.5">
                  <Button
                    size="sm"
                    variant="outline"
                    @click="toggleLock(row)"
                    :disabled="isBusy(row.id, 'lock') || (row.id === myId && row.is_active)"
                    :class="row.is_active ? '' : 'border-amber-500/50 text-amber-700 dark:text-amber-400'"
                  >
                    <Lock v-if="row.is_active" class="size-3.5" />
                    <Unlock v-else class="size-3.5" />
                    {{ row.is_active ? '锁定' : '解锁' }}
                  </Button>
                  <Button
                    size="sm"
                    variant="outline"
                    @click="pwdOpenFor === row.id ? closePwdPanel() : openPwdPanel(row)"
                    :disabled="isBusy(row.id, 'pwd')"
                  >
                    <KeyRound class="size-3.5" />
                    重置密码
                  </Button>
                </div>
              </TableCell>
            </TableRow>
            <TableRow v-if="pwdOpenFor === row.id" class="bg-muted/30 hover:bg-muted/30">
              <TableCell :colspan="6" class="py-3">
                <div class="flex items-center justify-end gap-2 flex-wrap">
                  <span class="text-xs text-muted-foreground mr-auto">
                    为「{{ row.username }}」设置新密码（8-128 个字符）。用户下次登录将使用新密码。
                  </span>
                  <div class="relative">
                    <Input
                      v-model="pwdInput"
                      :type="pwdShow ? 'text' : 'password'"
                      placeholder="新密码"
                      class="w-56 pr-8"
                      @keydown.enter="submitResetPwd(row)"
                    />
                    <button
                      type="button"
                      class="absolute right-2 top-1/2 -translate-y-1/2 text-[10px] text-muted-foreground hover:text-foreground"
                      @click="pwdShow = !pwdShow"
                    >{{ pwdShow ? '隐藏' : '显示' }}</button>
                  </div>
                  <Button variant="ghost" size="sm" @click="closePwdPanel" :disabled="isBusy(row.id, 'pwd')">
                    <X class="size-3.5" /> 取消
                  </Button>
                  <Button size="sm" @click="submitResetPwd(row)" :disabled="isBusy(row.id, 'pwd')">
                    <Check class="size-3.5" />
                    {{ isBusy(row.id, 'pwd') ? '保存中…' : '保存' }}
                  </Button>
                </div>
              </TableCell>
            </TableRow>
          </template>
        </TableBody>
      </Table>
    </Card>

    <div v-if="items.length" class="flex items-center justify-between text-xs text-muted-foreground">
      <span>{{ pageInfo }}</span>
      <div class="flex items-center gap-2">
        <Button variant="outline" size="sm" :disabled="offset === 0 || loading" @click="prevPage">上一页</Button>
        <Button variant="outline" size="sm" :disabled="offset + PAGE_SIZE >= total || loading" @click="nextPage">下一页</Button>
      </div>
    </div>
  </div>
</template>

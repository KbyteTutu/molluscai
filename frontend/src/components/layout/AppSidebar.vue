<script setup>
import { computed, onMounted, watch } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { Search, BookOpen, MessageCircle, Database, LogOut, User as UserIcon, ChevronRight, Dna, Cpu, Activity, Boxes, ListTodo, Gauge, ScrollText, Users } from 'lucide-vue-next'
import { useAuthStore } from '@/stores/auth'
import ShellLogo from '@/components/brand/ShellLogo.vue'
import ThemeToggle from '@/components/layout/ThemeToggle.vue'
import Avatar from '@/components/ui/Avatar.vue'
import Button from '@/components/ui/Button.vue'
import Separator from '@/components/ui/Separator.vue'
import DropdownMenu from '@/components/ui/DropdownMenu.vue'
import DropdownMenuTrigger from '@/components/ui/DropdownMenuTrigger.vue'
import DropdownMenuContent from '@/components/ui/DropdownMenuContent.vue'
import DropdownMenuItem from '@/components/ui/DropdownMenuItem.vue'
import DropdownMenuSeparator from '@/components/ui/DropdownMenuSeparator.vue'
import { cn } from '@/lib/utils'

const authStore = useAuthStore()
const router = useRouter()
const route = useRoute()

const isAuthed = computed(() => authStore.isAuthenticated)
const isSuperadmin = computed(() => authStore.currentUser?.role === 'superadmin')

const aiQuota = computed(() => authStore.quota?.quotas?.ai?.hourly || null)
const aiQuotaLabel = computed(() => {
  const q = aiQuota.value
  if (!q) return null
  if (q.limit === -1) return '不限'
  return `${q.used} / ${q.limit}`
})
const aiQuotaPercent = computed(() => {
  const q = aiQuota.value
  if (!q || q.limit <= 0) return 0
  return Math.min(100, Math.round((q.used / q.limit) * 100))
})
const aiQuotaTone = computed(() => {
  const p = aiQuotaPercent.value
  if (p >= 90) return 'bg-destructive'
  if (p >= 60) return 'bg-amber-500'
  return 'bg-primary'
})

onMounted(() => {
  if (isAuthed.value) authStore.refreshQuota()
})

watch(isAuthed, (v) => {
  if (v) authStore.refreshQuota()
})

watch(() => route.fullPath, () => {
  if (isAuthed.value) authStore.refreshQuota()
})

const sections = computed(() => [
  {
    label: '软体数据库',
    items: [
      { name: '拍卖记录', to: '/', icon: Search, enabled: true },
      { name: '物种检索', to: '/taxa', icon: Dna, enabled: true }
    ]
  },
  {
    label: '知识库',
    items: [
      { name: '文献', to: '#', icon: BookOpen, enabled: false, hint: '即将推出' },
      { name: '问答', to: '#', icon: MessageCircle, enabled: false, hint: '即将推出' }
    ]
  },
  ...(isSuperadmin.value
    ? [{
        label: '管理',
        items: [
          { name: '数据采集', to: '/admin/scraper', icon: Database, enabled: true },
          { name: '任务管理', to: '/admin/tasks', icon: ListTodo, enabled: true },
          { name: '模型配置', to: '/admin/models', icon: Cpu, enabled: true },
          { name: '向量管理', to: '/admin/embeddings', icon: Boxes, enabled: true },
          { name: '用量统计', to: '/admin/usage', icon: Activity, enabled: true },
          { name: '配额管理', to: '/admin/quotas', icon: Gauge, enabled: true },
          { name: '查询日志', to: '/admin/queries', icon: ScrollText, enabled: true },
          { name: '用户管理', to: '/admin/users', icon: Users, enabled: true }
        ]
      }]
    : [])
])

const initials = computed(() => {
  const u = authStore.currentUser?.username || '?'
  return u.slice(0, 2).toUpperCase()
})

function isActive(to) {
  if (to === '/') return route.path === '/'
  return route.path.startsWith(to)
}

function logout() {
  authStore.logout()
  router.push('/login')
}
</script>

<template>
  <aside class="flex h-screen w-60 shrink-0 flex-col border-r bg-card">
    <div class="flex items-center justify-between px-5 py-5">
      <div class="flex items-center gap-2">
        <ShellLogo :size="33" class="text-primary" />
        <div class="leading-tight">
          <div class="font-serif text-lg font-semibold tracking-tight">MolluscAI</div>
          <div class="text-[11px] text-muted-foreground">软体动物学知识检索</div>
        </div>
      </div>
      <ThemeToggle />
    </div>

    <Separator />

    <nav class="flex-1 overflow-y-auto px-3 py-4">
      <div v-for="section in sections" :key="section.label" class="mb-5 last:mb-0">
        <div class="px-2 mb-1.5 text-[10px] font-medium uppercase tracking-widest text-muted-foreground">
          {{ section.label }}
        </div>
        <ul class="space-y-0.5">
          <li v-for="item in section.items" :key="item.name">
            <router-link
              v-if="item.enabled"
              :to="item.to"
              :class="cn(
                'flex items-center gap-2.5 rounded-md px-2 py-1.5 text-sm transition-colors',
                isActive(item.to)
                  ? 'bg-accent text-accent-foreground font-medium'
                  : 'text-foreground/80 hover:bg-accent/50 hover:text-foreground'
              )"
            >
              <component :is="item.icon" class="size-4" />
              <span>{{ item.name }}</span>
            </router-link>
            <div
              v-else
              class="flex items-center gap-2.5 rounded-md px-2 py-1.5 text-sm text-muted-foreground/60 cursor-not-allowed"
              :title="item.hint"
            >
              <component :is="item.icon" class="size-4" />
              <span>{{ item.name }}</span>
              <span class="ml-auto text-[10px] uppercase tracking-wider">{{ item.hint }}</span>
            </div>
          </li>
        </ul>
      </div>
    </nav>

    <Separator />

    <div v-if="isAuthed && aiQuota" class="px-3 pt-3 pb-1.5">
      <div class="flex items-center justify-between text-[11px]">
        <span class="text-muted-foreground">智能检索 · 每小时</span>
        <span class="font-mono tabular-nums">{{ aiQuotaLabel }}</span>
      </div>
      <div v-if="aiQuota.limit !== -1" class="mt-1.5 h-1 rounded-full bg-muted overflow-hidden">
        <div :class="cn('h-full transition-all', aiQuotaTone)" :style="{ width: aiQuotaPercent + '%' }"></div>
      </div>
    </div>

    <div class="flex items-center gap-2 p-3">
      <DropdownMenu v-if="isAuthed">
        <DropdownMenuTrigger>
          <button class="flex flex-1 items-center gap-2 rounded-md px-2 py-1.5 hover:bg-accent transition-colors">
            <Avatar class="size-7 text-xs font-medium text-primary bg-primary/10">{{ initials }}</Avatar>
            <div class="flex-1 text-left leading-tight overflow-hidden">
              <div class="text-sm font-medium truncate">{{ authStore.currentUser?.username }}</div>
              <div class="text-[11px] text-muted-foreground truncate">{{ authStore.currentUser?.email || '' }}</div>
            </div>
            <ChevronRight class="size-3.5 text-muted-foreground" />
          </button>
        </DropdownMenuTrigger>
        <DropdownMenuContent align="start">
          <DropdownMenuItem @select="router.push('/me')">
            <UserIcon class="size-4" /> 个人中心
          </DropdownMenuItem>
          <DropdownMenuSeparator />
          <DropdownMenuItem @select="logout">
            <LogOut class="size-4" /> 退出登录
          </DropdownMenuItem>
        </DropdownMenuContent>
      </DropdownMenu>

      <div v-else class="flex w-full items-center gap-2">
        <Button variant="outline" size="sm" class="flex-1" @click="router.push({ name: 'Login' })">登录</Button>
        <Button size="sm" class="flex-1" @click="router.push({ name: 'Login' })">注册</Button>
      </div>
    </div>
  </aside>
</template>

<script setup>
import { ref, onMounted, onBeforeUnmount } from 'vue'
import { useRouter } from 'vue-router'
import { adminApi } from '@/api'
import { toast } from 'vue-sonner'
import { 
  LayoutDashboard, Database, ListTodo, Cpu, Boxes, Activity, 
  Gauge, ScrollText, Users, MessageSquareHeart, Pencil, Settings,
  Search, Dna, HardDrive, Image, Loader2, Sparkles, Zap,
  BookOpen
} from 'lucide-vue-next'
import Card from '@/components/ui/Card.vue'
import CardHeader from '@/components/ui/CardHeader.vue'
import CardTitle from '@/components/ui/CardTitle.vue'
import CardDescription from '@/components/ui/CardDescription.vue'
import CardContent from '@/components/ui/CardContent.vue'
import Switch from '@/components/ui/Switch.vue'
import Badge from '@/components/ui/Badge.vue'
import Button from '@/components/ui/Button.vue'
import Separator from '@/components/ui/Separator.vue'
import Skeleton from '@/components/ui/Skeleton.vue'

const router = useRouter()

const REFRESH_INTERVAL = 15000
let statsTimer = null
let settingsTimer = null

// Smart Search Settings
const settings = ref({
  smart_search_auction: false,
  smart_search_taxa: false,
  smart_search_documents: false
})
const settingsLoaded = ref(false)

// Stats Overview — each field loads independently for lazy skeleton
const stats = ref({
  auctionRecords: null,
  taxaRecords: '315,589',
  userCount: null,
  todayQueries: null,
  dbSize: '约 30 GB',
  imageStorage: null,
  activeTasks: null
})
const statsLoaded = ref(false)

async function fetchSettings() {
  try {
    const res = await adminApi.getSettings()
    if (res.data) {
      settings.value = {
        smart_search_auction: res.data.smart_search_auction === 'true',
        smart_search_taxa: res.data.smart_search_taxa === 'true',
        smart_search_documents: res.data.smart_search_documents === 'true',
      }
    }
  } catch {
    // Settings load silently — non-critical, keep previous values
  } finally {
    settingsLoaded.value = true
  }
}

async function updateSetting(key, value) {
  const originalValue = settings.value[key]
  settings.value[key] = value

  try {
    await adminApi.updateSettings({ [key]: value ? 'true' : 'false' })
    toast.success('设置已保存')
  } catch (error) {
    settings.value[key] = originalValue
    toast.error('保存设置失败')
  }
}

async function fetchStats() {
  try {
    const [scraperRes, queriesRes, usersRes, tasksRes] = await Promise.allSettled([
      adminApi.scraperStats(),
      adminApi.queryStats(1),
      adminApi.listUsers({ limit: 1 }),
      adminApi.listTasks()
    ])

    if (scraperRes.status === 'fulfilled') {
      stats.value.auctionRecords = scraperRes.value.data.total_records?.toLocaleString() || '0'
      stats.value.imageStorage = scraperRes.value.data.storage_size_mb
        ? `${scraperRes.value.data.storage_size_mb.toLocaleString()} MB`
        : '0 MB'
    }

    if (queriesRes.status === 'fulfilled') {
      stats.value.todayQueries = queriesRes.value.data.total_queries?.toLocaleString() || '0'
    }

    if (usersRes.status === 'fulfilled') {
      stats.value.userCount = usersRes.value.data.total?.toLocaleString() || '0'
    }

    if (tasksRes.status === 'fulfilled') {
      const w = tasksRes.value.data.workers || {}
      stats.value.activeTasks = ((w.active || 0) + (w.reserved || 0)).toString()
    }
  } catch {
    // Stats load silently
  } finally {
    statsLoaded.value = true
  }
}

function startPolling() {
  stopPolling()
  statsTimer = setInterval(fetchStats, REFRESH_INTERVAL)
  settingsTimer = setInterval(fetchSettings, REFRESH_INTERVAL)
}

function stopPolling() {
  if (statsTimer) { clearInterval(statsTimer); statsTimer = null }
  if (settingsTimer) { clearInterval(settingsTimer); settingsTimer = null }
}

onMounted(() => {
  fetchSettings()
  fetchStats()
  startPolling()
})

onBeforeUnmount(stopPolling)

const quickLinks = [
  { name: '数据采集', path: '/admin/scraper', icon: Database, desc: '拍卖数据爬取与图片下载' },
  { name: '任务管理', path: '/admin/tasks', icon: ListTodo, desc: 'Celery 异步任务监控' },
  { name: '模型配置', path: '/admin/models', icon: Cpu, desc: 'LLM/Embedding API 配置' },
  { name: '向量管理', path: '/admin/embeddings', icon: Boxes, desc: '嵌入进度与触发' },
  { name: '用量统计', path: '/admin/usage', icon: Activity, desc: 'API 调用成本分析' },
  { name: '配额管理', path: '/admin/quotas', icon: Gauge, desc: '用户查询额度设置' },
  { name: '查询日志', path: '/admin/queries', icon: ScrollText, desc: '用户查询审计记录' },
  { name: '用户管理', path: '/admin/users', icon: Users, desc: '角色/锁定/重置密码' },
  { name: '用户反馈', path: '/admin/feedbacks', icon: MessageSquareHeart, desc: '用户建议与反馈' },
  { name: '纠错管理', path: '/admin/corrections', icon: Pencil, desc: '物种/文献数据纠错审核' },
  { name: '系统设置', path: '/admin/settings', icon: Settings, desc: '全局开关与数据清理' }
]
</script>

<template>
  <div class="space-y-6 max-w-6xl mx-auto">
    <div class="flex items-center gap-2">
      <LayoutDashboard class="h-6 w-6 text-slate-500" />
      <h1 class="text-2xl font-bold tracking-tight text-slate-900 dark:text-slate-100">管理后台 <span class="text-slate-400 font-normal text-lg ml-2">MolluscAI</span></h1>
    </div>

    <!-- System Overview -->
    <div class="space-y-3">
      <h2 class="text-lg font-semibold tracking-tight">系统概览</h2>
      <div class="grid gap-4 grid-cols-2 md:grid-cols-4 lg:grid-cols-7">
        <Card class="col-span-2 md:col-span-1 lg:col-span-1">
          <CardHeader class="pb-2">
            <CardTitle class="text-sm font-medium text-slate-500 flex items-center justify-between">
              拍卖记录
              <Search class="h-4 w-4 text-muted-foreground" />
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div class="text-2xl font-bold">
              <Skeleton v-if="!statsLoaded" class="h-7 w-20" />
              <span v-else>{{ stats.auctionRecords || '获取失败' }}</span>
            </div>
          </CardContent>
        </Card>

        <Card class="col-span-2 md:col-span-1 lg:col-span-1">
          <CardHeader class="pb-2">
            <CardTitle class="text-sm font-medium text-slate-500 flex items-center justify-between">
              物种数据
              <Dna class="h-4 w-4 text-muted-foreground" />
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div class="text-2xl font-bold">{{ stats.taxaRecords }}</div>
          </CardContent>
        </Card>

        <Card class="col-span-2 md:col-span-1 lg:col-span-1">
          <CardHeader class="pb-2">
            <CardTitle class="text-sm font-medium text-slate-500 flex items-center justify-between">
              用户数量
              <Users class="h-4 w-4 text-muted-foreground" />
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div class="text-2xl font-bold">
              <Skeleton v-if="!statsLoaded" class="h-7 w-16" />
              <span v-else>{{ stats.userCount || '获取失败' }}</span>
            </div>
          </CardContent>
        </Card>

        <Card class="col-span-2 md:col-span-1 lg:col-span-1">
          <CardHeader class="pb-2">
            <CardTitle class="text-sm font-medium text-slate-500 flex items-center justify-between">
              今日查询
              <Zap class="h-4 w-4 text-muted-foreground" />
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div class="text-2xl font-bold">
              <Skeleton v-if="!statsLoaded" class="h-7 w-16" />
              <span v-else>{{ stats.todayQueries || '获取失败' }}</span>
            </div>
          </CardContent>
        </Card>

        <Card class="col-span-2 md:col-span-1 lg:col-span-1">
          <CardHeader class="pb-2">
            <CardTitle class="text-sm font-medium text-slate-500 flex items-center justify-between">
              数据库
              <HardDrive class="h-4 w-4 text-muted-foreground" />
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div class="text-2xl font-bold">{{ stats.dbSize }}</div>
          </CardContent>
        </Card>

        <Card class="col-span-2 md:col-span-1 lg:col-span-1">
          <CardHeader class="pb-2">
            <CardTitle class="text-sm font-medium text-slate-500 flex items-center justify-between">
              图片缓存
              <Image class="h-4 w-4 text-muted-foreground" />
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div class="text-2xl font-bold truncate" :title="stats.imageStorage">
              <Skeleton v-if="!statsLoaded" class="h-7 w-24" />
              <span v-else>{{ stats.imageStorage || '获取失败' }}</span>
            </div>
          </CardContent>
        </Card>

        <Card class="col-span-2 md:col-span-2 lg:col-span-1">
          <CardHeader class="pb-2">
            <CardTitle class="text-sm font-medium text-slate-500 flex items-center justify-between">
              活跃任务
              <Activity class="h-4 w-4 text-muted-foreground" />
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div class="text-2xl font-bold">
              <Skeleton v-if="!statsLoaded" class="h-7 w-10" />
              <span v-else>{{ stats.activeTasks || '0' }}</span>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>

    <!-- Smart Search Toggles -->
    <div class="space-y-3">
      <h2 class="text-lg font-semibold tracking-tight">智能检索开关</h2>
      <div class="grid gap-4 md:grid-cols-2">
        <!-- Auction Smart Search -->
        <Card>
          <CardContent class="p-6 flex flex-col h-full">
            <div class="flex justify-between items-start mb-4">
              <div class="p-2 bg-blue-100 dark:bg-blue-900/30 rounded-lg text-blue-600 dark:text-blue-400">
                <Search class="h-5 w-5" />
              </div>
              <Badge :variant="settings.smart_search_auction ? 'default' : 'secondary'">
                {{ settings.smart_search_auction ? '已启用' : '已关闭' }}
              </Badge>
            </div>
            <div class="mt-auto space-y-4">
              <div>
                <h3 class="font-medium text-slate-900 dark:text-slate-100">拍卖智能检索</h3>
                <p class="text-sm text-slate-500 dark:text-slate-400 mt-1 line-clamp-2">支持基于语义的复杂拍卖记录搜索</p>
              </div>
              <div class="flex items-center justify-between pt-4 border-t">
                <span class="text-sm font-medium text-slate-700 dark:text-slate-300">状态控制</span>
                <Skeleton v-if="!settingsLoaded" class="h-6 w-10 rounded-full" />
                <Switch
                  v-else
                  :checked="settings.smart_search_auction"
                  @update:checked="(val) => updateSetting('smart_search_auction', val)"
                />
              </div>
            </div>
          </CardContent>
        </Card>

        <!-- Taxa Smart Search -->
        <Card>
          <CardContent class="p-6 flex flex-col h-full">
            <div class="flex justify-between items-start mb-4">
              <div class="p-2 bg-emerald-100 dark:bg-emerald-900/30 rounded-lg text-emerald-600 dark:text-emerald-400">
                <Dna class="h-5 w-5" />
              </div>
              <Badge :variant="settings.smart_search_taxa ? 'default' : 'secondary'">
                {{ settings.smart_search_taxa ? '已启用' : '已关闭' }}
              </Badge>
            </div>
            <div class="mt-auto space-y-4">
              <div>
                <h3 class="font-medium text-slate-900 dark:text-slate-100">物种智能检索</h3>
                <p class="text-sm text-slate-500 dark:text-slate-400 mt-1 line-clamp-2">支持物种分类与描述的向量混合检索</p>
              </div>
              <div class="flex items-center justify-between pt-4 border-t">
                <span class="text-sm font-medium text-slate-700 dark:text-slate-300">状态控制</span>
                <Skeleton v-if="!settingsLoaded" class="h-6 w-10 rounded-full" />
                <Switch
                  v-else
                  :checked="settings.smart_search_taxa"
                  @update:checked="(val) => updateSetting('smart_search_taxa', val)"
                />
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>

    <!-- Quick Links -->
    <div class="space-y-3">
      <h2 class="text-lg font-semibold tracking-tight">快捷管理</h2>
      <div class="grid gap-4 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
        <router-link v-for="link in quickLinks" :key="link.path" :to="link.path" class="group block">
          <Card class="h-full hover:bg-slate-50 dark:hover:bg-slate-800/50 transition-colors border-transparent hover:border-slate-200 dark:hover:border-slate-700 shadow-sm">
            <CardContent class="p-5 flex items-center gap-4">
              <div class="p-2.5 rounded-md bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-400 group-hover:text-primary group-hover:bg-primary/10 transition-colors">
                <component :is="link.icon" class="h-5 w-5" />
              </div>
              <div class="flex-1 overflow-hidden">
                <h3 class="font-medium text-slate-900 dark:text-slate-100 truncate group-hover:text-primary transition-colors">{{ link.name }}</h3>
                <p class="text-xs text-slate-500 dark:text-slate-400 truncate mt-0.5">{{ link.desc }}</p>
              </div>
            </CardContent>
          </Card>
        </router-link>
      </div>
    </div>
  </div>
</template>

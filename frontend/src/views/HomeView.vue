<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useSearchStore } from '@/stores/search'
import { useAuthStore } from '@/stores/auth'
import { auctionApi } from '@/api'
import { Search, SlidersHorizontal, LayoutGrid, Rows3, ChevronDown, Lock } from 'lucide-vue-next'
import Card from '@/components/ui/Card.vue'
import CardContent from '@/components/ui/CardContent.vue'
import Input from '@/components/ui/Input.vue'
import Button from '@/components/ui/Button.vue'
import Badge from '@/components/ui/Badge.vue'
import Skeleton from '@/components/ui/Skeleton.vue'
import Alert from '@/components/ui/Alert.vue'
import AlertTitle from '@/components/ui/AlertTitle.vue'
import AlertDescription from '@/components/ui/AlertDescription.vue'
import Collapsible from '@/components/ui/Collapsible.vue'
import CollapsibleTrigger from '@/components/ui/CollapsibleTrigger.vue'
import CollapsibleContent from '@/components/ui/CollapsibleContent.vue'
import Separator from '@/components/ui/Separator.vue'
import AdvancedFilters from '@/components/auction/AdvancedFilters.vue'
import AuctionCard from '@/components/auction/AuctionCard.vue'
import AuctionTable from '@/components/auction/AuctionTable.vue'
import EmptyState from '@/components/common/EmptyState.vue'
import { cn, formatNumber } from '@/lib/utils'

const search = useSearchStore()
const auth = useAuthStore()
const router = useRouter()

const isAuthenticated = computed(() => auth.isAuthenticated)

const view = ref('cards')
const filtersOpen = ref(false)

const anonItems = ref([])
const anonLoading = ref(false)
const anonError = ref(null)

function lastMonthRange() {
  const now = new Date()
  const from = new Date(now.getFullYear(), now.getMonth() - 1, 1)
  const to = new Date(now.getFullYear(), now.getMonth(), 0)
  return { from: from.toISOString().slice(0, 10), to: to.toISOString().slice(0, 10) }
}

const { from: defaultFrom, to: defaultTo } = lastMonthRange()

const filters = reactive({
  name: '', family: '', size: '', locality: '',
  price_min: null, price_max: null,
  end_date_from: defaultFrom,
  end_date_to: defaultTo,
  seller: '', is_sold: '',
  sort: 'price_desc'
})

const SORT_OPTIONS = [
  { value: 'price_desc', label: '价格 · 由高到低' },
  { value: 'price_asc', label: '价格 · 由低到高' },
  { value: 'end_date_desc', label: '日期 · 最新优先' },
  { value: 'item_no_desc', label: '编号 · 最新优先' }
]

const PAGE_SIZE = 12
const offset = ref(0)
const totalRecords = ref(null)
const totalSold = ref(null)

const advancedFilterCount = computed(() => {
  let n = 0
  for (const k of ['family','size','locality','seller','is_sold','end_date_from','end_date_to']) if (filters[k]) n++
  if (filters.price_min !== null || filters.price_max !== null) n++
  return n
})

function buildPayload() {
  const out = { offset: offset.value, limit: PAGE_SIZE, sort: filters.sort }
  for (const [k, v] of Object.entries(filters)) {
    if (k === 'sort') continue
    if (k === 'is_sold') {
      if (v === 'true') out.is_sold = true
      else if (v === 'false') out.is_sold = false
      continue
    }
    if (v !== '' && v !== null && v !== undefined) out[k] = v
  }
  return out
}

async function runSearch(reset = true) {
  if (!isAuthenticated.value) {
    redirectToLogin()
    return
  }
  if (reset) offset.value = 0
  await search.searchAuctions(buildPayload())
}

function nextPage() {
  if (!isAuthenticated.value) { redirectToLogin(); return }
  if (offset.value + PAGE_SIZE >= Math.min(search.total, 500)) return
  offset.value += PAGE_SIZE
  search.searchAuctions(buildPayload())
}
function prevPage() {
  if (!isAuthenticated.value) { redirectToLogin(); return }
  if (offset.value === 0) return
  offset.value = Math.max(0, offset.value - PAGE_SIZE)
  search.searchAuctions(buildPayload())
}

function redirectToLogin() {
  router.push({ name: 'Login', query: { redirect: '/' } })
}

const pageInfo = computed(() => {
  if (search.total === 0) return ''
  const start = offset.value + 1
  const end = Math.min(offset.value + PAGE_SIZE, search.total)
  return `${formatNumber(start)} – ${formatNumber(end)} / ${formatNumber(search.total)}`
})

const displayItems = computed(() =>
  isAuthenticated.value ? search.results : anonItems.value
)

const displayLoading = computed(() =>
  isAuthenticated.value ? search.loading : anonLoading.value
)

async function loadAnonRecent() {
  anonLoading.value = true
  anonError.value = null
  try {
    const response = await auctionApi.recent()
    anonItems.value = response.data.items || []
  } catch (e) {
    anonError.value = e.response?.data?.detail || '加载失败'
  } finally {
    anonLoading.value = false
  }
}

onMounted(async () => {
  totalRecords.value = 2990337
  totalSold.value = 1727375
  if (isAuthenticated.value) {
    await runSearch(true)
  } else {
    await loadAnonRecent()
  }
})
</script>

<template>
  <div class="space-y-8 md:space-y-10">
    <header class="space-y-3">
      <h1 class="font-serif text-3xl md:text-4xl font-semibold tracking-tight">拍卖记录检索</h1>
      <p class="text-sm text-muted-foreground max-w-2xl leading-relaxed">
        查询 shellauction.net 的历史拍品数据。数据每月1日更新，默认显示上月成交记录，按成交价由高到低排列。
        <span class="text-muted-foreground/70">All records are for reference and research purposes only.</span>
      </p>
    </header>

    <section class="grid grid-cols-2 sm:grid-cols-4 gap-3">
      <Card class="p-4">
        <div class="text-[10px] uppercase tracking-widest text-muted-foreground">总记录</div>
        <div class="font-serif text-xl md:text-2xl mt-1 tabular-nums">{{ formatNumber(totalRecords) }}</div>
      </Card>
      <Card class="p-4">
        <div class="text-[10px] uppercase tracking-widest text-muted-foreground">已成交</div>
        <div class="font-serif text-xl md:text-2xl mt-1 tabular-nums">{{ formatNumber(totalSold) }}</div>
      </Card>
      <Card class="p-4">
        <div class="text-[10px] uppercase tracking-widest text-muted-foreground">收录科</div>
        <div class="font-serif text-xl md:text-2xl mt-1 tabular-nums">67</div>
      </Card>
      <Card class="p-4">
        <div class="text-[10px] uppercase tracking-widest text-muted-foreground">数据更新</div>
        <div class="font-serif text-xl md:text-2xl mt-1">每月1日</div>
      </Card>
    </section>

    <Card v-if="!isAuthenticated" class="border-primary/30 bg-primary/5">
      <CardContent class="p-5 flex flex-col sm:flex-row items-start sm:items-center gap-3 sm:gap-4">
        <Lock class="size-5 shrink-0 text-primary" />
        <div class="flex-1 space-y-0.5">
          <p class="text-sm font-medium">下面展示最近 12 条拍卖记录</p>
          <p class="text-xs text-muted-foreground">登录后可使用按学名/科/产地/价格/日期等条件检索全部 290 万条历史数据，并查看物种详情与对比。</p>
        </div>
        <div class="flex items-center gap-2 w-full sm:w-auto">
          <Button variant="outline" size="sm" class="flex-1 sm:flex-none" @click="redirectToLogin">注册</Button>
          <Button size="sm" class="flex-1 sm:flex-none" @click="redirectToLogin">登录</Button>
        </div>
      </CardContent>
    </Card>

    <Card v-if="isAuthenticated">
      <CardContent class="p-4 md:p-5 space-y-4">
        <form @submit.prevent="runSearch(true)" class="flex flex-col sm:flex-row items-stretch sm:items-center gap-3">
          <div class="relative flex-1">
            <Search class="absolute left-3 top-1/2 -translate-y-1/2 size-4 text-muted-foreground" />
            <Input
              v-model="filters.name"
              placeholder="拉丁学名、科、产地…"
              class="pl-9 h-10"
            />
          </div>
          <div class="flex items-center gap-2">
            <Collapsible v-model:open="filtersOpen" class="flex-1 sm:flex-none">
              <CollapsibleTrigger>
                <Button type="button" variant="outline" class="gap-2 relative w-full sm:w-auto">
                  <SlidersHorizontal class="size-4" />
                  <span class="hidden xs:inline">高级筛选</span>
                  <Badge v-if="advancedFilterCount" variant="default" class="ml-1 h-5 min-w-5 px-1 text-[10px]">{{ advancedFilterCount }}</Badge>
                  <ChevronDown :class="cn('size-3.5 transition-transform', filtersOpen && 'rotate-180')" />
                </Button>
              </CollapsibleTrigger>
            </Collapsible>
            <Button type="submit" class="h-10 px-6" :disabled="search.loading">
              {{ search.loading ? '检索中…' : '检索' }}
            </Button>
          </div>
        </form>
        <Collapsible :open="filtersOpen">
          <CollapsibleContent>
            <Separator class="mb-4" />
            <AdvancedFilters v-model="filters" />
          </CollapsibleContent>
        </Collapsible>
      </CardContent>
    </Card>

    <section>
      <div v-if="isAuthenticated" class="flex flex-col sm:flex-row sm:items-end sm:justify-between gap-3 mb-4">
        <div>
          <h2 class="font-serif text-xl">检索结果</h2>
          <p v-if="search.total > 0" class="text-xs text-muted-foreground mt-0.5">{{ pageInfo }}</p>
        </div>
        <div class="flex items-center gap-2 flex-wrap">
          <label class="inline-flex items-center gap-2 text-xs text-muted-foreground">
            <span class="hidden sm:inline">排序</span>
            <select
              v-model="filters.sort"
              @change="runSearch(true)"
              class="h-8 rounded-md border border-input bg-background px-2 text-xs focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
            >
              <option v-for="opt in SORT_OPTIONS" :key="opt.value" :value="opt.value">{{ opt.label }}</option>
            </select>
          </label>
          <div class="inline-flex items-center rounded-md border bg-card p-0.5">
            <button
              type="button"
              :class="cn('inline-flex items-center gap-1.5 rounded px-2.5 py-1 text-xs transition-colors',
                view === 'cards' ? 'bg-accent text-accent-foreground' : 'text-muted-foreground hover:text-foreground')"
              @click="view = 'cards'"
            >
              <LayoutGrid class="size-3.5" /> 卡片
            </button>
            <button
              type="button"
              :class="cn('inline-flex items-center gap-1.5 rounded px-2.5 py-1 text-xs transition-colors',
                view === 'table' ? 'bg-accent text-accent-foreground' : 'text-muted-foreground hover:text-foreground')"
              @click="view = 'table'"
            >
              <Rows3 class="size-3.5" /> 表格
            </button>
          </div>
        </div>
      </div>

      <div v-else class="mb-4">
        <h2 class="font-serif text-xl">最近上拍</h2>
        <p class="text-xs text-muted-foreground mt-0.5">登录后解锁完整 290 万条历史记录与高级筛选</p>
      </div>

      <Alert v-if="isAuthenticated && search.error" variant="destructive" class="mb-4">
        <AlertTitle>检索失败</AlertTitle>
        <AlertDescription>{{ search.error }}</AlertDescription>
      </Alert>

      <Alert v-if="!isAuthenticated && anonError" variant="destructive" class="mb-4">
        <AlertTitle>加载失败</AlertTitle>
        <AlertDescription>{{ anonError }}</AlertDescription>
      </Alert>

      <div v-if="displayLoading && !displayItems.length">
        <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
          <Skeleton v-for="i in PAGE_SIZE" :key="i" class="aspect-[3/4]" />
        </div>
      </div>

      <EmptyState v-else-if="!displayItems.length && !displayLoading" />

      <div v-else>
        <div v-if="!isAuthenticated || view === 'cards'" class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
          <AuctionCard v-for="item in displayItems" :key="item.item_no" :item="item" />
        </div>
        <Card v-else class="overflow-hidden">
          <AuctionTable :items="displayItems" />
        </Card>

        <div v-if="isAuthenticated && search.total > PAGE_SIZE" class="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 mt-6">
          <p class="text-xs text-muted-foreground">{{ pageInfo }}</p>
          <div class="flex items-center gap-2">
            <Button variant="outline" size="sm" :disabled="offset === 0 || search.loading" @click="prevPage">上一页</Button>
            <Button variant="outline" size="sm" :disabled="offset + PAGE_SIZE >= Math.min(search.total, 500) || search.loading" @click="nextPage">下一页</Button>
          </div>
        </div>
        <p v-if="isAuthenticated && search.total > 500" class="text-[11px] text-muted-foreground/70 mt-2 sm:text-right">
          检索结果上限 500 条 · 请使用筛选条件缩小范围
        </p>

        <div v-if="!isAuthenticated" class="mt-6 flex justify-center">
          <Button @click="redirectToLogin" class="px-8">登录后查看更多</Button>
        </div>
      </div>
    </section>
  </div>
</template>

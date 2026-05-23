<script setup>
import { ref, reactive, computed, onMounted, watch } from 'vue'
import { useRouter } from 'vue-router'
import { taxaApi } from '@/api'
import { Search, ChevronRight, Sparkles, Type, History, Languages, ShieldAlert } from 'lucide-vue-next'
import Card from '@/components/ui/Card.vue'
import CardContent from '@/components/ui/CardContent.vue'
import Input from '@/components/ui/Input.vue'
import Button from '@/components/ui/Button.vue'
import Badge from '@/components/ui/Badge.vue'
import Skeleton from '@/components/ui/Skeleton.vue'
import Alert from '@/components/ui/Alert.vue'
import AlertTitle from '@/components/ui/AlertTitle.vue'
import AlertDescription from '@/components/ui/AlertDescription.vue'
import EmptyState from '@/components/common/EmptyState.vue'
import TaxonName from '@/components/common/TaxonName.vue'
import { formatNumber, cn } from '@/lib/utils'

defineOptions({ name: 'TaxaSearchView' })

const router = useRouter()

const PAGE_SIZE = 20
const q = ref('')
const mode = ref('lexical')
const rank = ref('')
const family = ref('')
const genus = ref('')
const status = ref('')
const offset = ref(0)

const items = ref([])
const total = ref(0)
const loading = ref(false)
const error = ref('')

const RANKS = ['', 'Species', 'Genus', 'Family', 'Order', 'Class', 'Phylum']
const STATUSES = ['', 'accepted', 'unaccepted', 'superseded combination', 'nomen dubium', 'taxon inquirendum']

const pageInfo = computed(() => {
  if (total.value === 0) return ''
  const s = offset.value + 1
  const e = Math.min(offset.value + PAGE_SIZE, total.value)
  return `${formatNumber(s)} – ${formatNumber(e)} / ${formatNumber(total.value)}`
})

const zhNames = ref({})

async function runSearch(reset = true) {
  if (reset) offset.value = 0
  loading.value = true
  error.value = ''
  try {
    const params = { offset: offset.value, limit: PAGE_SIZE, mode: mode.value }
    if (q.value.trim()) params.q = q.value.trim()
    if (rank.value) params.rank = rank.value
    if (family.value.trim()) params.family = family.value.trim()
    if (genus.value.trim()) params.genus = genus.value.trim()
    if (status.value) params.status = status.value
    const { data } = await taxaApi.search(params)
    items.value = data.items
    total.value = data.total
  } catch (e) {
    error.value = e.response?.data?.detail || e.message || '检索失败'
    items.value = []
    total.value = 0
  } finally {
    loading.value = false
  }
  if (!Object.keys(zhNames.value).length) {
    try { const r = await taxaApi.rankNamesZh(); zhNames.value = r.data } catch {}
  }
}

function zhName(latin) {
  const zh = zhNames.value[latin]
  return zh ? `${latin} ${zh}` : latin
}

function nextPage() {
  if (offset.value + PAGE_SIZE >= total.value) return
  offset.value += PAGE_SIZE
  runSearch(false)
}
function prevPage() {
  if (offset.value === 0) return
  offset.value = Math.max(0, offset.value - PAGE_SIZE)
  runSearch(false)
}

onMounted(() => runSearch(true))
</script>

<template>
  <div class="space-y-8 md:space-y-10">
    <header class="space-y-2">
      <h1 class="font-serif text-3xl md:text-4xl font-semibold tracking-tight">物种检索</h1>
      <p class="inline-flex items-center gap-1.5 text-xs text-amber-700 dark:text-amber-400">
        <ShieldAlert class="size-3.5 shrink-0" />
        <span>使用须知：数据来源 WoRMS 数据库等公开渠道，仅供便捷集合查询使用，不得用于违法违规目的。因AI算力开销，限制每小时智能查询次数。</span>
      </p>
      <p class="text-sm text-muted-foreground max-w-2xl leading-relaxed">
        基于 WoRMS / MolluscaBase 的软体动物分类数据库。支持拉丁学名模糊匹配、按科/属筛选、按阶元过滤。
        <span class="text-muted-foreground/70">Taxonomic data: WoRMS Editorial Board. World Register of Marine Species. Available from https://www.marinespecies.org at VLIZ.</span>
      </p>
    </header>

    <Card>
      <CardContent class="p-4 md:p-5 space-y-3">
        <form @submit.prevent="runSearch(true)" class="flex flex-col sm:flex-row items-stretch gap-2">
          <div class="relative flex-1">
            <Search class="absolute left-3 top-1/2 -translate-y-1/2 size-4 text-muted-foreground" />
            <Input v-model="q" placeholder="学名、曾用名 或 各语言俗名，如 Conus、Loricata、chiton…" class="pl-9 h-10" />
          </div>
          <div class="inline-flex items-center rounded-md border bg-card p-0.5">
            <button
              type="button"
              :class="['inline-flex items-center gap-1.5 rounded px-2.5 py-1 text-xs transition-colors',
                mode === 'lexical' ? 'bg-accent text-accent-foreground' : 'text-muted-foreground hover:text-foreground']"
              @click="mode = 'lexical'; runSearch(true)"
              title="词法模糊匹配 · 最快"
            >
              <Type class="size-3.5" /> 词法
            </button>
            <button
              type="button"
              :class="['inline-flex items-center gap-1.5 rounded px-2.5 py-1 text-xs transition-colors',
                mode === 'hybrid' ? 'bg-accent text-accent-foreground' : 'text-muted-foreground hover:text-foreground']"
              @click="mode = 'hybrid'; runSearch(true)"
              title="语义检索 · 词法+向量+重排序"
            >
              <Sparkles class="size-3.5" /> 智能
            </button>
          </div>
          <Button type="submit" class="h-10 px-6" :disabled="loading">
            {{ loading ? '检索中…' : '检索' }}
          </Button>
        </form>
        <div class="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-3 text-sm">
          <label class="flex items-center gap-2">
            <span class="text-xs text-muted-foreground shrink-0 w-10">阶元</span>
            <select v-model="rank" @change="runSearch(true)" class="h-8 flex-1 rounded-md border border-input bg-background px-2 text-xs">
              <option v-for="r in RANKS" :key="r" :value="r">{{ r || '全部' }}</option>
            </select>
          </label>
          <label class="flex items-center gap-2">
            <span class="text-xs text-muted-foreground shrink-0 w-10">状态</span>
            <select v-model="status" @change="runSearch(true)" class="h-8 flex-1 rounded-md border border-input bg-background px-2 text-xs">
              <option v-for="s in STATUSES" :key="s" :value="s">{{ s || '全部' }}</option>
            </select>
          </label>
          <label class="flex items-center gap-2">
            <span class="text-xs text-muted-foreground shrink-0 w-10">科</span>
            <Input v-model="family" placeholder="Conidae" class="h-8 text-xs" @keyup.enter="runSearch(true)" />
          </label>
          <label class="flex items-center gap-2">
            <span class="text-xs text-muted-foreground shrink-0 w-10">属</span>
            <Input v-model="genus" placeholder="Conus" class="h-8 text-xs" @keyup.enter="runSearch(true)" />
          </label>
        </div>
      </CardContent>
    </Card>

    <section>
      <div class="flex items-end justify-between mb-4">
        <div>
          <h2 class="font-serif text-xl">检索结果</h2>
          <p v-if="total > 0" class="text-xs text-muted-foreground mt-0.5">{{ pageInfo }}</p>
        </div>
      </div>

      <Alert v-if="error" variant="destructive" class="mb-4">
        <AlertTitle>检索失败</AlertTitle>
        <AlertDescription>{{ error }}</AlertDescription>
      </Alert>

      <div v-if="loading && !items.length" class="space-y-2">
        <Skeleton v-for="i in 8" :key="i" class="h-14" />
      </div>

      <EmptyState v-else-if="!items.length && !loading" title="未找到匹配物种" />

      <Card v-else class="divide-y overflow-hidden">
        <button
          v-for="t in items"
          :key="t.aphia_id"
          type="button"
          class="flex items-center gap-4 w-full px-4 py-3 text-left hover:bg-accent/50 transition-colors"
          @click="router.push(`/taxa/${t.aphia_id}`)"
        >
          <Badge
            :variant="t.status === 'accepted' ? 'default' : 'muted'"
            class="text-[10px] uppercase tracking-wider shrink-0 w-[4.5rem] justify-center"
          >{{ t.status === 'accepted' ? 'accepted' : t.status || '—' }}</Badge>
          <div class="flex-1 min-w-0">
            <div class="flex items-baseline gap-2 flex-wrap">
              <TaxonName :name="t.scientificname" class="text-sm" />
              <span v-if="t.authority" class="text-xs text-muted-foreground font-serif not-italic">{{ t.authority }}</span>
            </div>
            <div
              v-if="t.match_info && t.match_info.kind === 'synonym'"
              class="mt-1.5 inline-flex items-center gap-1.5 rounded-md bg-amber-100 dark:bg-amber-950/60 px-2 py-1 text-xs text-amber-900 dark:text-amber-200 ring-1 ring-amber-300 dark:ring-amber-800/60"
            >
              <History class="size-3.5 shrink-0" />
              <span>命中曾用名:&nbsp;</span>
              <em class="font-serif font-semibold not-italic">{{ t.match_info.term }}</em>
              <span v-if="t.match_info.authority" class="text-amber-700 dark:text-amber-400/80 font-serif not-italic">{{ t.match_info.authority }}</span>
            </div>
            <div
              v-else-if="t.match_info && t.match_info.kind === 'vernacular'"
              class="mt-1.5 inline-flex items-center gap-1.5 rounded-md bg-sky-100 dark:bg-sky-950/60 px-2 py-1 text-xs text-sky-900 dark:text-sky-200 ring-1 ring-sky-300 dark:ring-sky-800/60"
            >
              <Languages class="size-3.5 shrink-0" />
              <span>命中俗名:&nbsp;</span>
              <em class="font-semibold not-italic">{{ t.match_info.term }}</em>
              <span v-if="t.match_info.language" class="text-sky-700 dark:text-sky-400/80 uppercase tracking-wider text-[10px]">{{ t.match_info.language }}</span>
            </div>
            <div class="mt-0.5 text-xs text-muted-foreground flex items-center gap-2 flex-wrap">
              <span v-if="t.rank" class="uppercase tracking-wider text-[10px]">{{ t.rank }}</span>
              <span v-if="t.family">· {{ zhName(t.family) }}</span>
              <span v-if="t.class" class="text-muted-foreground/70">· {{ zhName(t.class) }}</span>
              <span class="font-mono text-muted-foreground/70">· #{{ t.aphia_id }}</span>
            </div>
          </div>
          <div class="flex items-center gap-2 shrink-0">
            <Badge v-if="t.is_extinct" variant="muted" class="text-[10px]">†</Badge>
            <ChevronRight class="size-4 text-muted-foreground" />
          </div>
        </button>
      </Card>

      <div v-if="total > PAGE_SIZE" class="flex items-center justify-between mt-5">
        <p class="text-xs text-muted-foreground">{{ pageInfo }}</p>
        <div class="flex items-center gap-2">
          <Button variant="outline" size="sm" :disabled="offset === 0 || loading" @click="prevPage">上一页</Button>
          <Button variant="outline" size="sm" :disabled="offset + PAGE_SIZE >= total || loading" @click="nextPage">下一页</Button>
        </div>
      </div>
    </section>
  </div>
</template>

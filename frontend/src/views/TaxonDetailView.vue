<script setup>
import { ref, onMounted, computed, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import axios from 'axios'
import { taxaApi } from '@/api'
import { ArrowLeft, ExternalLink, History, Languages, Map, GitBranch, Network, BookOpen, Search, Loader2 } from 'lucide-vue-next'
import Card from '@/components/ui/Card.vue'
import Badge from '@/components/ui/Badge.vue'
import Button from '@/components/ui/Button.vue'
import Input from '@/components/ui/Input.vue'
import Skeleton from '@/components/ui/Skeleton.vue'
import Alert from '@/components/ui/Alert.vue'
import AlertTitle from '@/components/ui/AlertTitle.vue'
import AlertDescription from '@/components/ui/AlertDescription.vue'
import Separator from '@/components/ui/Separator.vue'
import TaxonName from '@/components/common/TaxonName.vue'

const route = useRoute()
const router = useRouter()
const taxon = ref(null)
const loading = ref(true)
const error = ref('')

const synonyms = ref([])
const vernaculars = ref([])
const distributions = ref([])
const children = ref([])
const classification = ref([])
const externalIds = ref([])

async function load() {
  loading.value = true
  error.value = ''
  taxon.value = null
  synonyms.value = []
  vernaculars.value = []
  distributions.value = []
  children.value = []
  classification.value = []
  externalIds.value = []
  const id = route.params.aphiaId
  try {
    const { data } = await taxaApi.getDetail(id)
    taxon.value = data
  } catch (e) {
    error.value = e.response?.status === 404 ? '未找到该物种' : (e.response?.data?.detail || '加载失败')
    loading.value = false
    return
  }
  loading.value = false
  const settle = (promise) => promise.catch(() => null)
  const [s, v, d, c, cls, x] = await Promise.all([
    settle(taxaApi.getSynonyms(id)),
    settle(taxaApi.getVernaculars(id)),
    settle(taxaApi.getDistributions(id)),
    settle(taxaApi.getChildren(id, { accepted_only: true })),
    settle(taxaApi.getClassification(id)),
    settle(taxaApi.getExternalIds(id))
  ])
  if (s) synonyms.value = s.data
  if (v) vernaculars.value = v.data
  if (d) distributions.value = d.data
  if (c) children.value = c.data
  if (cls) classification.value = cls.data
  if (x) externalIds.value = x.data
}

const classificationDisplay = computed(() => {
  if (!taxon.value) return []
  const t = taxon.value
  return [
    ['界 Kingdom', t.kingdom],
    ['门 Phylum', t.phylum],
    ['亚门 Subphylum', t.subphylum],
    ['纲 Class', t.class],
    ['亚纲 Subclass', t.subclass],
    ['下纲 Infraclass', t.infraclass],
    ['总目 Superorder', t.superorder],
    ['目 Order', t.order],
    ['亚目 Suborder', t.suborder],
    ['下目 Infraorder', t.infraorder],
    ['总科 Superfamily', t.superfamily],
    ['科 Family', t.family],
    ['属 Genus', t.genus],
    ['种 Species', t.species_epithet]
  ].filter(([, v]) => v)
})

const ancestors = computed(() => {
  return [...classification.value].sort((a, b) => b.depth - a.depth)
})

const externalIdsByGroup = computed(() => {
  const groups = {}
  for (const x of externalIds.value) {
    const key = x.source.toUpperCase()
    if (!groups[key]) groups[key] = []
    groups[key].push(x.external_id)
  }
  return Object.entries(groups).sort(([a], [b]) => a.localeCompare(b))
})

const externalIdLink = (source, id) => {
  const s = source.toLowerCase()
  if (s === 'ncbi') return `https://www.ncbi.nlm.nih.gov/Taxonomy/Browser/wwwtax.cgi?id=${id}`
  if (s === 'tsn') return `https://www.itis.gov/servlet/SingleRpt/SingleRpt?search_topic=TSN&search_value=${id}`
  if (s === 'iucn') return `https://www.iucnredlist.org/species/${id}/0`
  if (s === 'fishbase') return `https://www.fishbase.se/summary/${id}`
  if (s === 'algaebase') return `https://www.algaebase.org/search/species/detail/?species_id=${id}`
  if (s === 'bold') return `https://www.boldsystems.org/index.php/TaxBrowser_Taxonpage?taxid=${id}`
  return null
}

// --- 冈瓦纳英汉博物词典 ---
const ganvanaQuery = ref('')
const ganvanaResults = ref([])
const ganvanaLoading = ref(false)
const ganvanaError = ref('')
const ganvanaSearched = ref(false)

async function searchGanvana() {
  const keyword = ganvanaQuery.value.trim()
  if (!keyword) return
  ganvanaLoading.value = true
  ganvanaError.value = ''
  try {
    const params = new URLSearchParams()
    params.append('keyword', keyword)
    const { data } = await axios.post('/ganvana/searchDic', params, {
      headers: {
        'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
        'X-Requested-With': 'XMLHttpRequest'
      },
      transformRequest: [(d) => d]
    })
    ganvanaResults.value = Array.isArray(data) ? data : []
    ganvanaSearched.value = true
  } catch (e) {
    ganvanaError.value = e.response?.data?.message || e.message || '查询失败'
    ganvanaResults.value = []
  } finally {
    ganvanaLoading.value = false
  }
}

const ganvanaTopResults = computed(() => ganvanaResults.value.slice(0, 10))

// 默认填入物种学名（不含作者）并自动检索一次
watch(() => taxon.value?.scientificname, (name) => {
  if (name && !ganvanaQuery.value) {
    ganvanaQuery.value = name
    searchGanvana()
  }
}, { immediate: false })

watch(() => route.params.aphiaId, () => { if (route.params.aphiaId) load() })
onMounted(load)
</script>

<template>
  <div class="space-y-6">
    <button
      class="inline-flex items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground transition-colors"
      @click="router.back()"
    >
      <ArrowLeft class="size-4" /> 返回
    </button>

    <div v-if="loading" class="space-y-3">
      <Skeleton class="h-10 w-2/3" />
      <Skeleton class="h-64" />
    </div>

    <Alert v-else-if="error" variant="destructive">
      <AlertTitle>错误</AlertTitle>
      <AlertDescription>{{ error }}</AlertDescription>
    </Alert>

    <div v-else-if="taxon" class="space-y-6 max-w-3xl">
      <header class="space-y-2">
        <div class="flex items-baseline gap-3 flex-wrap">
          <TaxonName :name="taxon.scientificname" class="text-3xl leading-tight" />
          <span v-if="taxon.authority" class="text-lg text-muted-foreground font-serif not-italic">{{ taxon.authority }}</span>
        </div>
        <div class="flex items-center gap-2 flex-wrap">
          <Badge v-if="taxon.rank" variant="outline" class="text-[10px] uppercase tracking-wider">{{ taxon.rank }}</Badge>
          <Badge v-if="taxon.status" :variant="taxon.status === 'accepted' ? 'default' : 'muted'" class="text-[10px] uppercase tracking-wider">{{ taxon.status }}</Badge>
          <Badge v-if="taxon.is_extinct" variant="muted" class="text-[10px] uppercase tracking-wider">† Extinct</Badge>
          <span class="text-xs font-mono text-muted-foreground">#{{ taxon.aphia_id }}</span>
          <a v-if="taxon.url" :href="taxon.url" target="_blank" rel="noopener noreferrer" class="ml-auto">
            <Button variant="default" size="sm"><ExternalLink class="size-3.5" /> 在 WoRMS 查看</Button>
          </a>
        </div>
        <div v-if="ancestors.length" class="flex items-center gap-1 flex-wrap text-xs text-muted-foreground pt-1">
          <template v-for="(a, idx) in ancestors" :key="a.ancestor_aphia_id">
            <button
              v-if="a.ancestor_aphia_id !== taxon.aphia_id"
              class="hover:text-foreground hover:underline transition-colors"
              @click="router.push(`/taxa/${a.ancestor_aphia_id}`)"
            >{{ a.scientificname }}</button>
            <span v-else class="font-medium text-foreground">{{ a.scientificname }}</span>
            <span v-if="idx < ancestors.length - 1" class="text-muted-foreground/50">›</span>
          </template>
        </div>
      </header>

      <Card class="p-6">
        <div class="text-[10px] uppercase tracking-widest text-muted-foreground mb-4">分类阶元 / Classification</div>
        <dl class="grid grid-cols-1 sm:grid-cols-2 gap-x-8 gap-y-3 text-sm">
          <div v-for="[label, value] in classificationDisplay" :key="label" class="flex items-baseline justify-between gap-3 border-b border-dashed pb-1.5">
            <dt class="text-muted-foreground text-xs">{{ label }}</dt>
            <dd class="text-right">{{ value }}</dd>
          </div>
        </dl>
      </Card>

      <Card v-if="synonyms.length" class="p-6">
        <div class="flex items-center gap-2 mb-3 text-[10px] uppercase tracking-widest text-muted-foreground">
          <History class="size-3.5" /> 曾用名 / Synonyms <span class="text-muted-foreground/60">({{ synonyms.length }})</span>
        </div>
        <ul class="space-y-2">
          <li
            v-for="s in synonyms"
            :key="s.synonym_aphia_id"
            class="flex items-baseline gap-2 flex-wrap text-sm border-b border-dashed last:border-b-0 pb-2 last:pb-0"
          >
            <em class="font-serif not-italic">{{ s.scientificname }}</em>
            <span v-if="s.authority" class="text-xs text-muted-foreground font-serif not-italic">{{ s.authority }}</span>
            <Badge v-if="s.status" variant="muted" class="text-[10px] uppercase tracking-wider">{{ s.status }}</Badge>
          </li>
        </ul>
      </Card>

      <Card v-if="vernaculars.length" class="p-6">
        <div class="flex items-center gap-2 mb-3 text-[10px] uppercase tracking-widest text-muted-foreground">
          <Languages class="size-3.5" /> 各语言俗名 / Vernaculars <span class="text-muted-foreground/60">({{ vernaculars.length }})</span>
        </div>
        <ul class="grid grid-cols-1 sm:grid-cols-2 gap-x-6 gap-y-2 text-sm">
          <li
            v-for="(v, idx) in vernaculars"
            :key="`${v.vernacular}-${idx}`"
            class="flex items-baseline justify-between gap-2"
          >
            <span>{{ v.vernacular }}</span>
            <Badge v-if="v.language_code" variant="outline" class="text-[10px] uppercase tracking-wider shrink-0">{{ v.language_code }}</Badge>
          </li>
        </ul>
      </Card>

      <div v-if="taxon.is_marine !== null || taxon.is_freshwater !== null">
        <Card class="p-6">
          <div class="text-[10px] uppercase tracking-widest text-muted-foreground mb-3">生境 / Habitat</div>
          <div class="flex flex-wrap gap-2 text-xs">
            <Badge v-if="taxon.is_marine" variant="secondary">海洋 Marine</Badge>
            <Badge v-if="taxon.is_brackish" variant="secondary">半咸 Brackish</Badge>
            <Badge v-if="taxon.is_freshwater" variant="secondary">淡水 Freshwater</Badge>
            <Badge v-if="taxon.is_terrestrial" variant="secondary">陆生 Terrestrial</Badge>
          </div>
        </Card>
      </div>

      <Card v-if="distributions.length" class="p-6">
        <div class="flex items-center gap-2 mb-3 text-[10px] uppercase tracking-widest text-muted-foreground">
          <Map class="size-3.5" /> 分布 / Distributions <span class="text-muted-foreground/60">({{ distributions.length }})</span>
        </div>
        <ul class="space-y-2 text-sm">
          <li
            v-for="(d, idx) in distributions"
            :key="idx"
            class="border-b border-dashed last:border-b-0 pb-2 last:pb-0"
          >
            <div class="flex items-baseline gap-2 flex-wrap">
              <span class="font-medium">{{ d.locality || d.higher_geography || '—' }}</span>
              <span v-if="d.higher_geography && d.locality" class="text-xs text-muted-foreground">· {{ d.higher_geography }}</span>
              <Badge v-if="d.establishment_means" variant="outline" class="text-[10px] uppercase tracking-wider">{{ d.establishment_means }}</Badge>
            </div>
          </li>
        </ul>
      </Card>

      <Card v-if="children.length" class="p-6">
        <div class="flex items-center gap-2 mb-3 text-[10px] uppercase tracking-widest text-muted-foreground">
          <GitBranch class="size-3.5" /> 下级分类 / Children <span class="text-muted-foreground/60">({{ children.length }})</span>
        </div>
        <ul class="grid grid-cols-1 sm:grid-cols-2 gap-2">
          <li v-for="c in children" :key="c.child_aphia_id">
            <button
              class="flex items-baseline justify-between gap-2 w-full text-left text-sm hover:bg-accent/50 transition-colors px-2 py-1 rounded"
              @click="router.push(`/taxa/${c.child_aphia_id}`)"
            >
              <span class="flex items-baseline gap-2 min-w-0">
                <em class="font-serif not-italic truncate">{{ c.scientificname }}</em>
                <span v-if="c.rank" class="text-[10px] uppercase tracking-wider text-muted-foreground shrink-0">{{ c.rank }}</span>
              </span>
              <span class="text-xs font-mono text-muted-foreground/70 shrink-0">#{{ c.child_aphia_id }}</span>
            </button>
          </li>
        </ul>
      </Card>

      <Card v-if="externalIdsByGroup.length" class="p-6">
        <div class="flex items-center gap-2 mb-3 text-[10px] uppercase tracking-widest text-muted-foreground">
          <Network class="size-3.5" /> 外部数据库 / External IDs
        </div>
        <dl class="space-y-2 text-sm">
          <div v-for="[source, ids] in externalIdsByGroup" :key="source" class="flex items-baseline gap-3 flex-wrap">
            <dt class="text-xs font-mono uppercase tracking-wider text-muted-foreground shrink-0 w-20">{{ source }}</dt>
            <dd class="flex items-center gap-1.5 flex-wrap">
              <template v-for="id in ids" :key="id">
                <a
                  v-if="externalIdLink(source, id)"
                  :href="externalIdLink(source, id)"
                  target="_blank"
                  rel="noopener noreferrer"
                  class="inline-flex items-center gap-1 text-xs hover:text-foreground transition-colors text-muted-foreground hover:underline"
                >
                  {{ id }}<ExternalLink class="size-3" />
                </a>
                <span v-else class="text-xs font-mono text-muted-foreground">{{ id }}</span>
              </template>
            </dd>
          </div>
        </dl>
      </Card>

      <Card class="p-6 border-emerald-500/30 bg-gradient-to-br from-emerald-500/5 via-transparent to-transparent">
        <div class="flex items-start justify-between gap-3 mb-1 flex-wrap">
          <div class="space-y-0.5">
            <a
              href="https://ganvana.com"
              target="_blank"
              rel="noopener noreferrer"
              class="inline-flex items-center gap-1.5 font-serif text-lg font-semibold text-foreground hover:text-emerald-700 dark:hover:text-emerald-400 transition-colors group"
            >
              <BookOpen class="size-4 text-emerald-600 dark:text-emerald-400" />
              冈瓦纳英汉博物词典
              <ExternalLink class="size-3.5 opacity-0 group-hover:opacity-70 transition-opacity" />
            </a>
            <a
              href="https://ganvana.com"
              target="_blank"
              rel="noopener noreferrer"
              class="block text-[11px] text-muted-foreground hover:text-emerald-700 dark:hover:text-emerald-400 hover:underline transition-colors"
            >
              点击进入冈瓦纳自然网 ›
            </a>
          </div>
        </div>

        <form @submit.prevent="searchGanvana" class="flex items-stretch gap-2 mt-4">
          <Input
            v-model="ganvanaQuery"
            placeholder="输入物种名（拉丁名或属名）"
            class="flex-1"
            autocomplete="off"
          />
          <Button type="submit" :disabled="ganvanaLoading || !ganvanaQuery.trim()" size="default">
            <Loader2 v-if="ganvanaLoading" class="size-4 animate-spin" />
            <Search v-else class="size-4" />
            {{ ganvanaLoading ? '查询中…' : '查询' }}
          </Button>
        </form>

        <Alert v-if="ganvanaError" variant="destructive" class="mt-3">
          <AlertTitle>查询失败</AlertTitle>
          <AlertDescription>{{ ganvanaError }}</AlertDescription>
        </Alert>

        <div v-if="ganvanaSearched && !ganvanaError" class="mt-4">
          <div v-if="ganvanaTopResults.length === 0" class="text-sm text-muted-foreground py-6 text-center">
            未找到匹配条目
          </div>
          <ul v-else class="divide-y divide-border/60 -mx-2">
            <li
              v-for="r in ganvanaTopResults"
              :key="r.id"
              class="px-3 py-2.5 hover:bg-emerald-500/5 transition-colors rounded"
            >
              <div class="flex items-baseline justify-between gap-3 flex-wrap">
                <div class="flex-1 min-w-0 space-y-0.5">
                  <div class="flex items-baseline gap-2 flex-wrap">
                    <span v-if="r.ch" class="font-medium text-foreground">{{ r.ch }}</span>
                    <span v-if="r.en" class="text-xs text-muted-foreground">{{ r.en.trim() }}</span>
                  </div>
                  <div class="font-serif italic text-sm text-muted-foreground/90 truncate">{{ r.lat }}</div>
                </div>
                <span class="text-[10px] font-mono text-muted-foreground/60 shrink-0">#{{ r.id }}</span>
              </div>
            </li>
          </ul>
          <div v-if="ganvanaResults.length > ganvanaTopResults.length" class="mt-3 text-[11px] text-muted-foreground text-center">
            共 {{ ganvanaResults.length }} 条结果，仅展示前 {{ ganvanaTopResults.length }} 条
          </div>
        </div>
      </Card>

      <p v-if="taxon.citation" class="text-xs text-muted-foreground leading-relaxed border-t pt-4">
        {{ taxon.citation }}
      </p>
      <p v-else class="text-xs text-muted-foreground/70 leading-relaxed border-t pt-4">
        Data source: {{ taxon.data_source }} · 完整分类学数据将随 WoRMS 同步后丰富
      </p>
    </div>
  </div>
</template>

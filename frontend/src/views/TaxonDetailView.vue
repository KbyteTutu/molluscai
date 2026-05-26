<script setup>
import { ref, onMounted, computed, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { taxaApi, correctionApi } from '@/api'
import { ArrowLeft, ExternalLink, Globe, History, Languages, Map, GitBranch, Network, Pencil } from 'lucide-vue-next'
import Card from '@/components/ui/Card.vue'
import Badge from '@/components/ui/Badge.vue'
import Button from '@/components/ui/Button.vue'
import Skeleton from '@/components/ui/Skeleton.vue'
import Alert from '@/components/ui/Alert.vue'
import AlertTitle from '@/components/ui/AlertTitle.vue'
import AlertDescription from '@/components/ui/AlertDescription.vue'
import Separator from '@/components/ui/Separator.vue'
import TaxonName from '@/components/common/TaxonName.vue'

import { toast } from 'vue-sonner'

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
const inaturalist = ref(null)
const zhNames = ref({})

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
  inaturalist.value = null
  showAllSynonyms.value = false
  showAllVernaculars.value = false
  showAllDistributions.value = false
  showAllChildren.value = false
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
  const [s, v, d, c, cls, x, iNat] = await Promise.all([
    settle(taxaApi.getSynonyms(id)),
    settle(taxaApi.getVernaculars(id)),
    settle(taxaApi.getDistributions(id)),
    settle(taxaApi.getChildren(id, { accepted_only: true })),
    settle(taxaApi.getClassification(id)),
    settle(taxaApi.getExternalIds(id)),
    settle(taxaApi.getInaturalist(id))
  ])
  if (s) synonyms.value = s.data
  if (v) vernaculars.value = v.data
  if (d) distributions.value = d.data
  if (c) children.value = c.data
  if (cls) classification.value = cls.data
  if (x) externalIds.value = x.data
  if (iNat?.data?.found) inaturalist.value = iNat.data
  if (taxon.value?.rank_names_zh && !Object.keys(zhNames.value).length) {
    zhNames.value = taxon.value.rank_names_zh
  }
}

function withZh(latin) {
  if (!latin) return latin
  const zh = zhNames.value[latin]
  return zh ? `${latin} ${zh}` : latin
}

const classificationDisplay = computed(() => {
  if (!taxon.value) return []
  const t = taxon.value
  return [
    ['界 Kingdom', withZh(t.kingdom)],
    ['门 Phylum', withZh(t.phylum)],
    ['亚门 Subphylum', withZh(t.subphylum)],
    ['纲 Class', withZh(t.class)],
    ['亚纲 Subclass', withZh(t.subclass)],
    ['下纲 Infraclass', withZh(t.infraclass)],
    ['总目 Superorder', withZh(t.superorder)],
    ['目 Order', withZh(t.order)],
    ['亚目 Suborder', withZh(t.suborder)],
    ['下目 Infraorder', withZh(t.infraorder)],
    ['总科 Superfamily', withZh(t.superfamily)],
    ['科 Family', withZh(t.family)],
    ['属 Genus', withZh(t.genus)],
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

const sortedVernaculars = computed(() => {
  return [...vernaculars.value].sort((a, b) => {
    const aChn = a.language_code === 'CHN'
    const bChn = b.language_code === 'CHN'
    if (aChn && !bChn) return -1
    if (!aChn && bChn) return 1
    return 0
  })
})

const COLLAPSE_LIMIT = 50
const showAllSynonyms = ref(false)
const showAllVernaculars = ref(false)
const showAllDistributions = ref(false)
const showAllChildren = ref(false)

const visibleSynonyms = computed(() =>
  showAllSynonyms.value ? synonyms.value : synonyms.value.slice(0, COLLAPSE_LIMIT)
)
const visibleVernaculars = computed(() =>
  showAllVernaculars.value ? sortedVernaculars.value : sortedVernaculars.value.slice(0, COLLAPSE_LIMIT)
)
const visibleDistributions = computed(() =>
  showAllDistributions.value ? distributions.value : distributions.value.slice(0, COLLAPSE_LIMIT)
)
const visibleChildren = computed(() =>
  showAllChildren.value ? children.value : children.value.slice(0, COLLAPSE_LIMIT)
)

// --- 冈瓦纳英汉博物词典 已下线（ECS 出口无法访问 ganvana.com） ---

watch(() => route.params.aphiaId, () => { if (route.params.aphiaId) load() })
onMounted(load)

const correctionOpen = ref(false)
const correctionField = ref('')
const correctionCustomField = ref('')
const correctionVernacularIdx = ref(-1)
const correctionCurrent = ref('')
const correctionSuggested = ref('')
const correctionNote = ref('')
const correctionSubmitting = ref(false)

const CORRECTION_FIELDS = [
  { value: 'vernaculars', label: '俗名 Vernaculars' },
  { value: 'scientificname', label: '学名 Scientific name' },
  { value: 'authority', label: '命名人 Authority' },
  { value: 'status', label: '分类状态 Status' },
  { value: 'rank', label: '分类等级 Rank' },
  { value: 'kingdom', label: '界 Kingdom' },
  { value: 'phylum', label: '门 Phylum' },
  { value: 'class', label: '纲 Class' },
  { value: 'order', label: '目 Order' },
  { value: 'family', label: '科 Family' },
  { value: 'genus', label: '属 Genus' },
  { value: 'species_epithet', label: '种加词 Species epithet' },
  { value: 'other', label: '其他字段' },
]

function openCorrection() {
  correctionField.value = ''
  correctionCustomField.value = ''
  correctionVernacularIdx.value = -1
  correctionCurrent.value = ''
  correctionSuggested.value = ''
  correctionNote.value = ''
  correctionOpen.value = true
}

function onSelectField(field) {
  correctionField.value = field
  correctionCustomField.value = ''
  correctionVernacularIdx.value = -1
  if (field === 'other' || field === 'vernaculars') {
    correctionCurrent.value = ''
  } else if (taxon.value) {
    correctionCurrent.value = taxon.value[field] || ''
  }
}

function onSelectVernacular(idx) {
  correctionVernacularIdx.value = idx
  const v = sortedVernaculars.value[idx]
  if (v) {
    correctionCurrent.value = v.vernacular
  }
}

const effectiveFieldName = () => {
  if (correctionField.value === 'other') return correctionCustomField.value.trim()
  if (correctionField.value === 'vernaculars') {
    const v = sortedVernaculars.value[correctionVernacularIdx.value]
    if (v) return `vernacular:${v.language_code}`
    return ''
  }
  return correctionField.value
}

async function submitCorrection() {
  const fname = effectiveFieldName()
  if (!fname || !correctionSuggested.value.trim()) return
  correctionSubmitting.value = true
  try {
    await correctionApi.create({
      target_type: 'taxon',
      target_id: String(taxon.value.aphia_id),
      target_title: taxon.value.scientificname,
      field_name: fname,
      current_value: correctionCurrent.value || null,
      suggested_value: correctionSuggested.value.trim(),
      note: correctionNote.value.trim() || null,
    })
    toast.success('纠错已提交，等待管理员审核')
    correctionOpen.value = false
  } catch (e) {
    toast.error(e.response?.data?.detail || '提交失败')
  } finally {
    correctionSubmitting.value = false
  }
}
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
          <div class="ml-auto flex items-center gap-2">
            <Button variant="outline" size="sm" @click="openCorrection">
              <Pencil class="size-3.5" /> 信息纠错
            </Button>
            <a v-if="taxon.url" :href="taxon.url" target="_blank" rel="noopener noreferrer">
              <Button variant="default" size="sm"><ExternalLink class="size-3.5" /> 在 WoRMS 查看</Button>
            </a>
          </div>
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
            v-for="s in visibleSynonyms"
            :key="s.synonym_aphia_id"
            class="flex items-baseline gap-2 flex-wrap text-sm border-b border-dashed last:border-b-0 pb-2 last:pb-0"
          >
            <em class="font-serif not-italic">{{ s.scientificname }}</em>
            <span v-if="s.authority" class="text-xs text-muted-foreground font-serif not-italic">{{ s.authority }}</span>
            <Badge v-if="s.status" variant="muted" class="text-[10px] uppercase tracking-wider">{{ s.status }}</Badge>
          </li>
        </ul>
        <div v-if="synonyms.length > COLLAPSE_LIMIT" class="mt-3 pt-3 border-t border-dashed">
          <Button variant="ghost" size="sm" class="w-full text-xs text-muted-foreground" @click="showAllSynonyms = !showAllSynonyms">
            {{ showAllSynonyms ? '收起' : `展开全部 (${synonyms.length})` }}
          </Button>
        </div>
      </Card>

      <Card v-if="vernaculars.length" class="p-6">
        <div class="flex items-center gap-2 mb-3 text-[10px] uppercase tracking-widest text-muted-foreground">
          <Languages class="size-3.5" /> 各语言俗名 / Vernaculars <span class="text-muted-foreground/60">({{ sortedVernaculars.length }})</span>
        </div>
        <ul class="grid grid-cols-1 sm:grid-cols-2 gap-x-6 gap-y-2 text-sm">
          <li
            v-for="(v, idx) in visibleVernaculars"
            :key="`${v.vernacular}-${idx}`"
            class="flex items-baseline justify-between gap-2"
          >
            <span>{{ v.vernacular }}</span>
            <Badge v-if="v.language_code" variant="outline" class="text-[10px] uppercase tracking-wider shrink-0">{{ v.language_code }}</Badge>
          </li>
        </ul>
        <div v-if="sortedVernaculars.length > COLLAPSE_LIMIT" class="mt-3 pt-3 border-t border-dashed">
          <Button variant="ghost" size="sm" class="w-full text-xs text-muted-foreground" @click="showAllVernaculars = !showAllVernaculars">
            {{ showAllVernaculars ? '收起' : `展开全部 (${sortedVernaculars.length})` }}
          </Button>
        </div>
      </Card>

      <Card v-if="inaturalist?.found" class="p-6">
        <div class="flex items-center gap-2 mb-3 text-[10px] uppercase tracking-widest text-muted-foreground">
          <Globe class="size-3.5" /> iNaturalist
          <span v-if="inaturalist.observations_count" class="text-muted-foreground/60">
            ({{ inaturalist.observations_count.toLocaleString() }} observations)
          </span>
        </div>
        <div class="flex gap-4">
          <img
            v-if="inaturalist.image_url"
            :src="inaturalist.image_url"
            :alt="inaturalist.preferred_common_name || 'iNaturalist photo'"
            class="w-24 h-24 rounded-lg object-cover shrink-0"
          />
          <div class="flex-1 min-w-0 space-y-2 text-sm">
            <div v-if="inaturalist.preferred_common_name" class="flex items-baseline gap-2">
              <span class="text-xs text-muted-foreground shrink-0">Common name:</span>
              <span class="font-medium">{{ inaturalist.preferred_common_name }}</span>
            </div>
            <div v-if="inaturalist.conservation_status" class="flex items-baseline gap-2">
              <span class="text-xs text-muted-foreground shrink-0">Status:</span>
              <Badge variant="secondary" class="text-[10px]">{{ inaturalist.conservation_status }}</Badge>
            </div>
            <div v-if="inaturalist.wikipedia_summary" class="text-xs text-muted-foreground line-clamp-3 leading-relaxed" v-html="inaturalist.wikipedia_summary" />
          </div>
        </div>
        <div class="flex gap-2 mt-3">
          <a :href="`https://www.inaturalist.org/taxa/${inaturalist.inat_id}`" target="_blank" rel="noopener noreferrer">
            <Button variant="default" size="sm"><ExternalLink class="size-3.5" /> 在 iNaturalist 查看</Button>
          </a>
          <a v-if="inaturalist.wikipedia_url" :href="inaturalist.wikipedia_url" target="_blank" rel="noopener noreferrer">
            <Button variant="outline" size="sm"><ExternalLink class="size-3.5" /> Wikipedia</Button>
          </a>
        </div>
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
            v-for="(d, idx) in visibleDistributions"
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
        <div v-if="distributions.length > COLLAPSE_LIMIT" class="mt-3 pt-3 border-t border-dashed">
          <Button variant="ghost" size="sm" class="w-full text-xs text-muted-foreground" @click="showAllDistributions = !showAllDistributions">
            {{ showAllDistributions ? '收起' : `展开全部 (${distributions.length})` }}
          </Button>
        </div>
      </Card>

      <Card v-if="children.length" class="p-6">
        <div class="flex items-center gap-2 mb-3 text-[10px] uppercase tracking-widest text-muted-foreground">
          <GitBranch class="size-3.5" /> 下级分类 / Children <span class="text-muted-foreground/60">({{ children.length }})</span>
        </div>
        <ul class="grid grid-cols-1 sm:grid-cols-2 gap-2">
          <li v-for="c in visibleChildren" :key="c.child_aphia_id">
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
        <div v-if="children.length > COLLAPSE_LIMIT" class="mt-3 pt-3 border-t border-dashed">
          <Button variant="ghost" size="sm" class="w-full text-xs text-muted-foreground" @click="showAllChildren = !showAllChildren">
            {{ showAllChildren ? '收起' : `展开全部 (${children.length})` }}
          </Button>
        </div>
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

      <p v-if="taxon.citation" class="text-xs text-muted-foreground leading-relaxed border-t pt-4">
        {{ taxon.citation }}
      </p>
      <p v-else class="text-xs text-muted-foreground/70 leading-relaxed border-t pt-4">
        Data source: {{ taxon.data_source }} · 完整分类学数据将随 WoRMS 同步后丰富
      </p>
    </div>
  </div>

  <Teleport to="body">
    <div v-if="correctionOpen" class="fixed inset-0 z-50 flex items-center justify-center bg-black/50" @click.self="correctionOpen = false">
      <div class="bg-background rounded-xl shadow-2xl w-full max-w-md mx-4 max-h-[90vh] overflow-y-auto">
        <div class="p-6 space-y-4">
          <h2 class="text-lg font-semibold">信息纠错</h2>
          <p class="text-sm text-muted-foreground">发现 {{ taxon?.scientificname }} 的信息有误？请在此提交修正，管理员审核后将更新数据。</p>

          <div>
            <label class="text-sm font-medium mb-1.5 block">纠错字段</label>
            <select
              v-model="correctionField"
              @change="onSelectField(correctionField)"
              class="flex w-full rounded-md border border-input bg-background px-3 py-2 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
            >
              <option value="" disabled selected>请选择字段</option>
              <option v-for="f in CORRECTION_FIELDS" :key="f.value" :value="f.value">{{ f.label }}</option>
            </select>
          </div>

          <div v-if="correctionField === 'vernaculars'">
            <label class="text-sm font-medium mb-1.5 block">选择俗名</label>
            <select
              v-model="correctionVernacularIdx"
              @change="onSelectVernacular(correctionVernacularIdx)"
              class="flex w-full rounded-md border border-input bg-background px-3 py-2 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
            >
              <option :value="-1" disabled selected>请选择</option>
              <option
                v-for="(v, idx) in sortedVernaculars"
                :key="idx"
                :value="idx"
              >{{ v.vernacular }} ({{ v.language_code }}{{ v.language ? ', ' + v.language : '' }})</option>
            </select>
          </div>

          <div v-if="correctionField === 'other'">
            <label class="text-sm font-medium mb-1.5 block">自定义字段名</label>
            <input
              v-model="correctionCustomField"
              type="text"
              class="flex w-full rounded-md border border-input bg-background px-3 py-2 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
              placeholder="请输入字段名称"
            />
          </div>

          <div v-if="correctionField">
            <label class="text-sm font-medium mb-1.5 block">当前值</label>
            <div class="rounded-md border bg-muted/30 px-3 py-2 text-sm text-muted-foreground">{{ correctionCurrent || '(空)' }}</div>
          </div>

          <div>
            <label class="text-sm font-medium mb-1.5 block">建议值</label>
            <textarea
              v-model="correctionSuggested"
              rows="3"
              class="flex w-full rounded-md border border-input bg-transparent px-3 py-2 text-sm shadow-sm placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring resize-none"
              placeholder="请输入正确的信息"
            />
          </div>

          <div>
            <label class="text-sm font-medium mb-1.5 block">补充说明 <span class="text-muted-foreground font-normal">(选填)</span></label>
            <textarea
              v-model="correctionNote"
              rows="2"
              class="flex w-full rounded-md border border-input bg-transparent px-3 py-2 text-sm shadow-sm placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring resize-none"
              placeholder="可附上参考来源或理由"
            />
          </div>

          <div class="flex gap-2 pt-2">
            <Button variant="outline" class="flex-1" @click="correctionOpen = false">取消</Button>
            <Button
              class="flex-1"
              :disabled="!correctionSuggested.trim() || !effectiveFieldName() || correctionSubmitting"
              :loading="correctionSubmitting"
              @click="submitCorrection"
            >提交纠错</Button>
          </div>
        </div>
      </div>
    </div>
  </Teleport>
</template>

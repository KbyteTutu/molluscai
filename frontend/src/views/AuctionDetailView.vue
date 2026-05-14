<script setup>
import { ref, onMounted, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { auctionApi } from '@/api'
import { ArrowLeft, Copy, Check, ExternalLink, GitCompareArrows, Sparkles, ShieldCheck, ShieldAlert, RefreshCw, Loader2, ChevronRight } from 'lucide-vue-next'
import Card from '@/components/ui/Card.vue'
import Badge from '@/components/ui/Badge.vue'
import Button from '@/components/ui/Button.vue'
import Skeleton from '@/components/ui/Skeleton.vue'
import Alert from '@/components/ui/Alert.vue'
import AlertTitle from '@/components/ui/AlertTitle.vue'
import AlertDescription from '@/components/ui/AlertDescription.vue'
import Separator from '@/components/ui/Separator.vue'
import TaxonName from '@/components/common/TaxonName.vue'
import ShellLogo from '@/components/brand/ShellLogo.vue'
import { useCompareStore } from '@/stores/compare'
import { useTaxonMatchStore } from '@/stores/taxonMatch'
import { formatPrice, formatDate, imageUrls, originalAuctionUrl } from '@/lib/utils'
import { toast } from 'vue-sonner'

const route = useRoute()
const router = useRouter()
const compare = useCompareStore()
const taxonMatch = useTaxonMatchStore()
const item = ref(null)
const loading = ref(true)
const error = ref('')
const copied = ref(false)

const originalUrl = computed(() => item.value ? originalAuctionUrl(item.value.item_no) : '#')
const imageList = computed(() => imageUrls(item.value || {}))
const activeImage = ref(0)

const inCompare = computed(() => item.value && compare.has(item.value.item_no))

async function load() {
  loading.value = true
  error.value = ''
  try {
    const { data } = await auctionApi.getDetail(route.params.itemNo)
    item.value = data
  } catch (e) {
    error.value = e.response?.status === 404 ? '未找到该拍品' : (e.response?.data?.detail || '加载失败')
  } finally {
    loading.value = false
  }
}

function copyLink() {
  navigator.clipboard.writeText(window.location.href)
  copied.value = true
  toast.success('链接已复制')
  setTimeout(() => (copied.value = false), 2000)
}

function toggleCompare() {
  if (!item.value) return
  if (inCompare.value) {
    compare.remove(item.value.item_no)
    toast.success('已从对比移除')
  } else {
    const ok = compare.add(item.value)
    if (ok) toast.success(`已加入对比 (${compare.count}/${compare.MAX_ITEMS})`)
    else toast.error(`对比列表已满（最多 ${compare.MAX_ITEMS} 项）`)
  }
}

const itemNo = computed(() => Number(route.params.itemNo))
const taxon = computed(() => taxonMatch.get(itemNo.value))
const taxonLoading = computed(() => taxonMatch.isLoading(itemNo.value))
const taxonError = computed(() => taxonMatch.getError(itemNo.value))

const confidenceMeta = computed(() => {
  const c = taxon.value?.confidence
  if (c === 'high') return { label: '高置信', variant: 'default', icon: ShieldCheck }
  if (c === 'medium') return { label: '中等置信', variant: 'secondary', icon: ShieldCheck }
  if (c === 'low') return { label: '低置信', variant: 'outline', icon: ShieldAlert }
  return { label: '未匹配', variant: 'muted', icon: ShieldAlert }
})

async function runTaxonMatch(force = false) {
  try {
    await taxonMatch.fetch(itemNo.value, { force })
  } catch (e) {
    toast.error(e.response?.data?.detail || e.message || '匹配失败')
  }
}

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

    <div v-if="loading" class="grid grid-cols-1 lg:grid-cols-5 gap-8">
      <Skeleton class="lg:col-span-2 aspect-square" />
      <div class="lg:col-span-3 space-y-3">
        <Skeleton class="h-10 w-3/4" />
        <Skeleton class="h-4 w-1/2" />
        <Skeleton class="h-32" />
      </div>
    </div>

    <Alert v-else-if="error" variant="destructive">
      <AlertTitle>错误</AlertTitle>
      <AlertDescription>{{ error }}</AlertDescription>
    </Alert>

    <div v-else-if="item" class="grid grid-cols-1 lg:grid-cols-5 gap-8">
      <div class="lg:col-span-2 space-y-3">
        <Card class="aspect-square bg-muted/40 flex items-center justify-center overflow-hidden">
          <img v-if="imageList.length" :src="imageList[activeImage]" :alt="item.name" class="h-full w-full object-contain" />
          <ShellLogo v-else :size="96" class="text-muted-foreground/30" />
        </Card>
        <div v-if="imageList.length > 1" class="grid grid-cols-5 gap-2">
          <button
            v-for="(src, i) in imageList"
            :key="i"
            :class="['aspect-square rounded border overflow-hidden transition-all', i === activeImage ? 'border-primary ring-2 ring-primary/30' : 'border-border opacity-60 hover:opacity-100']"
            @click="activeImage = i"
          >
            <img :src="src" class="h-full w-full object-cover" />
          </button>
        </div>
      </div>

      <div class="lg:col-span-3 space-y-6">
        <div>
          <div class="flex items-center gap-2 text-xs text-muted-foreground mb-2">
            <span class="font-mono">#{{ item.item_no }}</span>
            <Separator orientation="vertical" class="h-3" />
            <Badge :variant="item.is_sold ? 'default' : 'muted'" class="text-[10px] uppercase tracking-wider">
              {{ item.is_sold ? 'Sold' : 'Unsold' }}
            </Badge>
          </div>
          <TaxonName :name="item.name || '未命名标本'" class="text-3xl leading-tight" />
          <p v-if="item.family" class="mt-2 text-sm text-muted-foreground">{{ item.family }}</p>
        </div>

        <Card class="p-6">
          <dl class="grid grid-cols-1 sm:grid-cols-2 gap-x-8 gap-y-4 text-sm">
            <div>
              <dt class="text-[10px] uppercase tracking-widest text-muted-foreground mb-1">尺寸</dt>
              <dd>{{ item.size || '—' }}</dd>
            </div>
            <div>
              <dt class="text-[10px] uppercase tracking-widest text-muted-foreground mb-1">产地</dt>
              <dd>{{ item.locality || '—' }}</dd>
            </div>
            <div>
              <dt class="text-[10px] uppercase tracking-widest text-muted-foreground mb-1">卖家</dt>
              <dd>{{ item.seller || '—' }}</dd>
            </div>
            <div>
              <dt class="text-[10px] uppercase tracking-widest text-muted-foreground mb-1">买家</dt>
              <dd>{{ item.buyer || '—' }}</dd>
            </div>
            <div>
              <dt class="text-[10px] uppercase tracking-widest text-muted-foreground mb-1">起拍价</dt>
              <dd class="font-mono tabular-nums">{{ formatPrice(item.start_price) || '—' }}</dd>
            </div>
            <div>
              <dt class="text-[10px] uppercase tracking-widest text-muted-foreground mb-1">成交价</dt>
              <dd class="font-mono tabular-nums">{{ formatPrice(item.final_price) || '—' }}</dd>
            </div>
            <div>
              <dt class="text-[10px] uppercase tracking-widest text-muted-foreground mb-1">截拍日期</dt>
              <dd>{{ formatDate(item.end_date) }}</dd>
            </div>
          </dl>
          <template v-if="item.note">
            <Separator class="my-5" />
            <div>
              <div class="text-[10px] uppercase tracking-widest text-muted-foreground mb-2">备注</div>
              <p class="text-sm leading-relaxed text-foreground/90">{{ item.note }}</p>
            </div>
          </template>
        </Card>

        <Card class="p-5 space-y-3">
          <div class="flex items-start justify-between gap-3 flex-wrap">
            <div class="space-y-0.5">
              <div class="flex items-center gap-2">
                <Sparkles class="size-4 text-primary" />
                <span class="font-serif text-base">分类学校验</span>
                <span class="text-[11px] text-muted-foreground/80">基于 WoRMS / 智能检索</span>
              </div>
              <p v-if="!taxon && !taxonLoading && !taxonError" class="text-xs text-muted-foreground">
                将拍品名称与软体动物分类数据库做模糊+语义匹配，识别接受的拉丁学名与分类阶元
              </p>
            </div>
            <div class="flex items-center gap-2">
              <Button v-if="!taxon" size="sm" :disabled="taxonLoading" @click="runTaxonMatch(false)">
                <Loader2 v-if="taxonLoading" class="size-4 animate-spin" />
                <Sparkles v-else class="size-4" />
                {{ taxonLoading ? '匹配中…' : '智能匹配' }}
              </Button>
              <Button v-else size="sm" variant="outline" :disabled="taxonLoading" @click="runTaxonMatch(true)">
                <RefreshCw class="size-4" /> 重新匹配
              </Button>
            </div>
          </div>

          <div v-if="taxonError" class="text-sm text-destructive">{{ taxonError }}</div>

          <div v-if="taxon" class="space-y-3">
            <div class="text-xs text-muted-foreground">
              清洗后的查询词:
              <span class="font-mono text-foreground/80">{{ taxon.cleaned_query || '—' }}</span>
            </div>

            <div v-if="!taxon.matched" class="text-sm text-muted-foreground">
              <ShieldAlert class="inline size-4 mr-1 text-muted-foreground" />
              {{ taxon.reason || '未找到匹配项' }}
            </div>

            <template v-else>
              <div class="rounded-md border bg-card p-4 space-y-2">
                <div class="flex items-center gap-2 flex-wrap">
                  <component :is="confidenceMeta.icon" class="size-4 text-primary" />
                  <Badge :variant="confidenceMeta.variant" class="text-[10px] uppercase tracking-wider">
                    {{ confidenceMeta.label }}
                  </Badge>
                  <span class="text-[11px] text-muted-foreground font-mono">相似度 {{ (taxon.similarity * 100).toFixed(1) }}%</span>
                  <Badge v-if="taxon.matched.status" :variant="taxon.matched.status === 'accepted' ? 'default' : 'outline'" class="text-[10px] uppercase">
                    {{ taxon.matched.status }}
                  </Badge>
                </div>
                <div class="flex items-baseline gap-2 flex-wrap">
                  <TaxonName :name="taxon.matched.scientificname" class="text-lg" />
                  <span v-if="taxon.matched.authority" class="text-sm font-serif not-italic text-muted-foreground">{{ taxon.matched.authority }}</span>
                </div>
                <div class="text-xs text-muted-foreground">
                  <template v-for="(part, idx) in [taxon.matched.kingdom, taxon.matched.phylum, taxon.matched.class, taxon.matched.order, taxon.matched.family, taxon.matched.genus].filter(Boolean)" :key="idx">
                    <span v-if="idx > 0" class="text-muted-foreground/60"> › </span>
                    <span>{{ part }}</span>
                  </template>
                </div>
                <div class="flex flex-wrap items-center gap-2 pt-1">
                  <router-link :to="`/taxa/${taxon.matched.aphia_id}`">
                    <Button variant="outline" size="sm">在物种库查看 <ChevronRight class="size-3.5" /></Button>
                  </router-link>
                  <a v-if="taxon.matched.url" :href="taxon.matched.url" target="_blank" rel="noopener noreferrer">
                    <Button variant="ghost" size="sm"><ExternalLink class="size-3.5" /> WoRMS</Button>
                  </a>
                </div>
              </div>

              <Alert v-if="taxon.accepted">
                <ShieldCheck class="size-4" />
                <AlertTitle>这是一个同义名</AlertTitle>
                <AlertDescription>
                  接受的学名为
                  <router-link :to="`/taxa/${taxon.accepted.aphia_id}`" class="underline underline-offset-2 hover:text-primary">
                    <TaxonName :name="taxon.accepted.scientificname" class="text-sm" />
                    <span v-if="taxon.accepted.authority" class="font-serif not-italic ml-1">{{ taxon.accepted.authority }}</span>
                  </router-link>
                </AlertDescription>
              </Alert>

              <details v-if="taxon.alternatives?.length" class="text-xs text-muted-foreground">
                <summary class="cursor-pointer hover:text-foreground transition-colors">其它候选 ({{ taxon.alternatives.length }})</summary>
                <ul class="mt-2 space-y-1">
                  <li v-for="alt in taxon.alternatives" :key="alt.aphia_id" class="flex items-center justify-between gap-2 pl-2 border-l border-muted">
                    <router-link :to="`/taxa/${alt.aphia_id}`" class="hover:text-foreground transition-colors flex-1 min-w-0">
                      <TaxonName :name="alt.scientificname" class="text-xs" />
                      <span v-if="alt.authority" class="font-serif not-italic ml-1">{{ alt.authority }}</span>
                    </router-link>
                    <Badge v-if="alt.rank" variant="outline" class="text-[9px] uppercase shrink-0">{{ alt.rank }}</Badge>
                  </li>
                </ul>
              </details>
            </template>
          </div>
        </Card>

        <div class="flex flex-wrap items-center gap-2">
          <a :href="originalUrl" target="_blank" rel="noopener noreferrer">
            <Button variant="default" size="sm">
              <ExternalLink class="size-4" /> 访问原始拍品页面
            </Button>
          </a>
          <Button :variant="inCompare ? 'secondary' : 'outline'" size="sm" @click="toggleCompare">
            <GitCompareArrows class="size-4" />
            {{ inCompare ? '已加入对比' : '加入对比' }}
          </Button>
          <Button variant="outline" size="sm" @click="copyLink">
            <Check v-if="copied" class="size-4" /><Copy v-else class="size-4" />
            {{ copied ? '已复制' : '复制链接' }}
          </Button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, reactive } from 'vue'
import { useRouter } from 'vue-router'
import { ArrowLeft, ExternalLink, X } from 'lucide-vue-next'
import { useCompareStore } from '@/stores/compare'
import Card from '@/components/ui/Card.vue'
import Button from '@/components/ui/Button.vue'
import Badge from '@/components/ui/Badge.vue'
import TaxonName from '@/components/common/TaxonName.vue'
import ShellLogo from '@/components/brand/ShellLogo.vue'
import EmptyState from '@/components/common/EmptyState.vue'
import { formatPrice, formatDate, firstImagePair, originalAuctionUrl, xorId } from '@/lib/utils'

const store = useCompareStore()
const router = useRouter()

const imageFailed = reactive({})

function pairFor(item) {
  return firstImagePair(item)
}
function hasAnyImage(item) {
  const p = pairFor(item)
  return Boolean(p.cached || p.origin)
}
function currentSrc(item) {
  const p = pairFor(item)
  const failed = imageFailed[item.item_no] || {}
  if (p.cached && !failed.cached) return p.cached
  if (p.origin && !failed.origin) return p.origin
  return null
}
function onImageError(item) {
  const p = pairFor(item)
  const cur = currentSrc(item)
  const next = imageFailed[item.item_no] ? { ...imageFailed[item.item_no] } : {}
  if (cur === p.cached) next.cached = true
  else if (cur === p.origin) next.origin = true
  imageFailed[item.item_no] = next
}

const fields = [
  { key: 'family', label: '科' },
  { key: 'size', label: '尺寸' },
  { key: 'locality', label: '产地' },
  { key: 'seller', label: '卖家' },
  { key: 'buyer', label: '买家' },
  { key: 'start_price', label: '起拍价', format: formatPrice },
  { key: 'final_price', label: '成交价', format: formatPrice },
  { key: 'end_date', label: '截拍日期', format: formatDate }
]

function valueOf(item, f) {
  const v = item[f.key]
  if (v === null || v === undefined || v === '') return '—'
  return f.format ? (f.format(v) || '—') : v
}

const priceValues = computed(() =>
  store.items.map((it) => (it.final_price !== null && it.final_price !== undefined ? Number(it.final_price) : null))
)
const priceMax = computed(() => {
  const vals = priceValues.value.filter((v) => v !== null)
  return vals.length ? Math.max(...vals) : null
})
const priceMin = computed(() => {
  const vals = priceValues.value.filter((v) => v !== null)
  return vals.length ? Math.min(...vals) : null
})
</script>

<template>
  <div class="space-y-6">
    <button
      class="inline-flex items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground transition-colors"
      @click="router.back()"
    >
      <ArrowLeft class="size-4" /> 返回
    </button>

    <header class="flex items-end justify-between gap-4 flex-wrap">
      <div class="space-y-1">
        <h1 class="font-serif text-3xl font-semibold tracking-tight">拍品对比</h1>
        <p class="text-sm text-muted-foreground">
          共 {{ store.count }} 项 · 高亮标示为该组内 <span class="text-primary">最高</span> 与 <span class="text-muted-foreground">最低</span> 成交价
        </p>
      </div>
      <div v-if="store.count" class="flex gap-2">
        <Button variant="outline" size="sm" @click="store.clear">清空</Button>
      </div>
    </header>

    <EmptyState
      v-if="!store.count"
      title="对比列表为空"
      description="回到检索页，点击卡片右上角的 + 添加拍品"
    >
      <Button class="mt-4" @click="router.push('/')">去检索</Button>
    </EmptyState>

    <div v-else class="overflow-x-auto -mx-4 sm:mx-0 px-4 sm:px-0">
      <div
        class="grid gap-4 min-w-fit"
        :style="{ gridTemplateColumns: `minmax(7rem, 9rem) repeat(${store.count}, minmax(14rem, 1fr))` }"
      >
        <div></div>
        <Card v-for="item in store.items" :key="item.item_no" class="overflow-hidden">
          <div class="aspect-square bg-muted/40 flex items-center justify-center overflow-hidden">
            <img
              v-if="currentSrc(item)"
              :src="currentSrc(item)"
              :alt="item.name"
              class="h-full w-full object-cover"
              @error="onImageError(item)"
            />
            <span v-else-if="hasAnyImage(item)" class="text-[11px] text-muted-foreground px-2 text-center">图片源已被删除，不可用</span>
            <ShellLogo v-else :size="40" class="text-muted-foreground/30" />
          </div>
          <div class="p-3 space-y-2">
            <div class="flex items-start justify-between gap-2">
              <TaxonName :name="item.name || '—'" class="text-sm leading-snug" />
              <button
                class="shrink-0 text-muted-foreground hover:text-destructive"
                :aria-label="`移除 ${item.item_no}`"
                @click="store.remove(item.item_no)"
              >
                <X class="size-4" />
              </button>
            </div>
            <div class="flex items-center gap-2 text-[10px] font-mono text-muted-foreground">
              <span>#{{ item.item_no }}</span>
              <Badge :variant="item.is_sold ? 'default' : 'muted'" class="text-[9px] uppercase tracking-wider">
                {{ item.is_sold ? 'Sold' : 'Unsold' }}
              </Badge>
            </div>
          </div>
        </Card>

        <template v-for="f in fields" :key="f.key">
          <div class="text-[10px] uppercase tracking-widest text-muted-foreground self-center px-1">
            {{ f.label }}
          </div>
          <div
            v-for="(item, idx) in store.items"
            :key="f.key + item.item_no"
            class="px-3 py-2 rounded-md bg-card border text-sm flex items-center"
            :class="{
              'text-primary font-medium': f.key === 'final_price' && priceValues[idx] !== null && priceValues[idx] === priceMax,
              'text-muted-foreground': f.key === 'final_price' && priceValues[idx] !== null && priceValues[idx] === priceMin && priceMin !== priceMax
            }"
          >
            <span :class="f.key === 'start_price' || f.key === 'final_price' ? 'font-mono tabular-nums' : ''">
              {{ valueOf(item, f) }}
            </span>
          </div>
        </template>

        <div></div>
        <div v-for="item in store.items" :key="'actions-' + item.item_no" class="flex flex-col gap-1.5">
          <Button variant="outline" size="sm" class="w-full" @click="router.push(`/auctions/${xorId(item.item_no)}`)">
            查看详情
          </Button>
          <a v-if="!item.is_sold" :href="originalAuctionUrl(item.item_no)" target="_blank" rel="noopener noreferrer" class="block">
            <Button variant="ghost" size="sm" class="w-full">
              <ExternalLink class="size-3.5" /> 原始页面
            </Button>
          </a>
        </div>
      </div>
    </div>

    <div v-if="store.count" class="text-xs text-muted-foreground">
      提示：同一个科、不同产地的拍品对比，可以帮助识别地域变异；同一产地、不同年份的拍品对比，可以观察价格趋势。
    </div>
  </div>
</template>

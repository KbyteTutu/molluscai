<script setup>
import { ref, computed } from 'vue'
import { useRouter } from 'vue-router'
import Card from '@/components/ui/Card.vue'
import Badge from '@/components/ui/Badge.vue'
import TaxonName from '@/components/common/TaxonName.vue'
import ShellLogo from '@/components/brand/ShellLogo.vue'
import CompareToggle from '@/components/auction/CompareToggle.vue'
import { useCompareStore } from '@/stores/compare'
import { formatPrice, formatDate, firstImagePair, xorId, cn } from '@/lib/utils'

const props = defineProps({ item: { type: Object, required: true } })
const router = useRouter()
const compare = useCompareStore()
const cachedFailed = ref(false)
const originFailed = ref(false)

const inCompare = computed(() => compare.has(props.item.item_no))

const pair = computed(() => firstImagePair(props.item))
const hasAnyImage = computed(() => Boolean(pair.value.cached || pair.value.origin))
const currentSrc = computed(() => {
  const { cached, origin } = pair.value
  if (cached && !cachedFailed.value) return cached
  if (origin && !originFailed.value) return origin
  return null
})

function onImageError() {
  if (currentSrc.value === pair.value.cached) cachedFailed.value = true
  else if (currentSrc.value === pair.value.origin) originFailed.value = true
}

function open() {
  router.push(`/auctions/${xorId(props.item.item_no)}`)
}
</script>

<template>
  <Card
    :class="cn(
      'overflow-hidden cursor-pointer transition-all hover:shadow-md group',
      inCompare ? 'border-primary/60 ring-1 ring-primary/30' : 'hover:border-primary/30'
    )"
    @click="open"
  >
    <div class="relative aspect-[4/3] bg-muted/40 flex items-center justify-center overflow-hidden">
      <img
        v-if="currentSrc"
        :src="currentSrc"
        :alt="item.name"
        loading="lazy"
        class="h-full w-full object-cover"
        @error="onImageError"
      />
      <span v-else-if="hasAnyImage" class="text-[11px] text-muted-foreground px-2 text-center">图片源已被删除，不可用</span>
      <ShellLogo v-else :size="48" class="text-muted-foreground/30" />
      <CompareToggle
        :item="item"
        :class="cn(
          'absolute top-2 right-2 transition-opacity',
          inCompare ? 'opacity-100' : 'opacity-0 group-hover:opacity-100 focus-within:opacity-100'
        )"
      />
    </div>
    <div class="p-4 space-y-2">
      <div class="flex items-start justify-between gap-2">
        <TaxonName :name="item.name || '未命名标本'" class="text-sm leading-snug line-clamp-2" />
        <Badge :variant="item.is_sold ? 'default' : 'muted'" class="shrink-0 text-[10px] uppercase tracking-wider">
          {{ item.buyer === '- no Bids' ? '流拍' : (item.is_sold ? 'Sold' : 'Unsold') }}
        </Badge>
      </div>
      <div class="text-xs text-muted-foreground flex flex-wrap gap-x-2">
        <span v-if="item.family">{{ item.family }}</span>
        <span v-if="item.locality">· {{ item.locality }}</span>
      </div>
      <div class="flex items-end justify-between pt-1">
        <div class="text-right">
          <div v-if="item.final_price" class="font-mono text-sm tabular-nums">{{ formatPrice(item.final_price) }}</div>
          <div class="text-[10px] text-muted-foreground">{{ formatDate(item.end_date) }}</div>
        </div>
      </div>
    </div>
  </Card>
</template>

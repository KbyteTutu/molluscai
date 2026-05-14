<script setup>
import { ref, onMounted, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { taxaApi } from '@/api'
import { ArrowLeft, ExternalLink } from 'lucide-vue-next'
import Card from '@/components/ui/Card.vue'
import Badge from '@/components/ui/Badge.vue'
import Button from '@/components/ui/Button.vue'
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

async function load() {
  loading.value = true
  error.value = ''
  try {
    const { data } = await taxaApi.getDetail(route.params.aphiaId)
    taxon.value = data
  } catch (e) {
    error.value = e.response?.status === 404 ? '未找到该物种' : (e.response?.data?.detail || '加载失败')
  } finally {
    loading.value = false
  }
}

const classification = computed(() => {
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
        </div>
      </header>

      <Card class="p-6">
        <div class="text-[10px] uppercase tracking-widest text-muted-foreground mb-4">分类阶元 / Classification</div>
        <dl class="grid grid-cols-1 sm:grid-cols-2 gap-x-8 gap-y-3 text-sm">
          <div v-for="[label, value] in classification" :key="label" class="flex items-baseline justify-between gap-3 border-b border-dashed pb-1.5">
            <dt class="text-muted-foreground text-xs">{{ label }}</dt>
            <dd class="text-right">{{ value }}</dd>
          </div>
        </dl>
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

      <div class="flex flex-wrap gap-2">
        <a v-if="taxon.url" :href="taxon.url" target="_blank" rel="noopener noreferrer">
          <Button variant="default" size="sm"><ExternalLink class="size-4" /> 在 WoRMS 查看</Button>
        </a>
      </div>

      <p v-if="taxon.citation" class="text-xs text-muted-foreground leading-relaxed border-t pt-4">
        {{ taxon.citation }}
      </p>
      <p v-else class="text-xs text-muted-foreground/70 leading-relaxed border-t pt-4">
        Data source: {{ taxon.data_source }} · 完整分类学数据将随 WoRMS 同步后丰富
      </p>
    </div>
  </div>
</template>

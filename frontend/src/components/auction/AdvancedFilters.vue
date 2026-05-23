<script setup>
import { ref, watch } from 'vue'
import { auctionApi } from '@/api'
import Input from '@/components/ui/Input.vue'
import Label from '@/components/ui/Label.vue'
import Checkbox from '@/components/ui/Checkbox.vue'

const props = defineProps({ modelValue: { type: Object, required: true } })
const emit = defineEmits(['update:modelValue'])

function update(field, value) {
  emit('update:modelValue', { ...props.modelValue, [field]: value })
}

// ── Family autocomplete ────────────────────────────────────
const familyQ = ref('')
const familyOptions = ref([])
const familyOpen = ref(false)
let familyTimer = null

async function searchFamilies(query) {
  if (!query || query.length < 1) {
    familyOptions.value = []
    return
  }
  try {
    const res = await auctionApi.families(query)
    familyOptions.value = res.data || []
  } catch { /* ignore */ }
}

watch(familyQ, (v) => {
  clearTimeout(familyTimer)
  if (v && v.length >= 1) {
    familyTimer = setTimeout(() => searchFamilies(v), 200)
    familyOpen.value = true
  } else {
    familyOpen.value = false
  }
})

function selectFamily(family) {
  update('family', family)
  familyQ.value = family
  familyOpen.value = false
}

function clearFamily() {
  update('family', '')
  familyQ.value = ''
  familyOpen.value = false
}
</script>

<template>
  <div class="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3 p-[3px]">
    <!-- Family autocomplete -->
    <div class="space-y-1.5 relative">
      <Label for="f-family">科 / Family</Label>
      <div class="relative">
        <Input
          id="f-family"
          :model-value="familyQ || modelValue.family"
          placeholder="搜索科名…"
          @update:modelValue="familyQ = $event; if ($event === '') clearFamily()"
          @focus="modelValue.family && !familyQ ? (familyQ = modelValue.family) : null"
        />
        <!-- dropdown -->
        <ul
          v-if="familyOpen && familyOptions.length"
          class="absolute z-20 mt-1 w-full max-h-52 overflow-y-auto rounded-md border border-border bg-popover shadow-md"
        >
          <li
            v-for="f in familyOptions"
            :key="f.family"
            class="flex items-center justify-between px-3 py-1.5 text-sm cursor-pointer hover:bg-accent"
            @mousedown.prevent="selectFamily(f.family)"
          >
            <span>{{ f.family }}</span>
            <span class="text-[10px] text-muted-foreground tabular-nums">{{ f.count.toLocaleString() }}</span>
          </li>
        </ul>
      </div>
    </div>

    <!-- Size range -->
    <div class="space-y-1.5">
      <Label>尺寸 / Size (mm)</Label>
      <div class="flex items-center gap-2">
        <Input
          class="flex-1 min-w-0"
          type="number"
          :model-value="modelValue.size_min"
          placeholder="最小"
          @update:modelValue="update('size_min', $event === '' ? null : Number($event))"
        />
        <span class="text-muted-foreground shrink-0">—</span>
        <Input
          class="flex-1 min-w-0"
          type="number"
          :model-value="modelValue.size_max"
          placeholder="最大"
          @update:modelValue="update('size_max', $event === '' ? null : Number($event))"
        />
      </div>
      <div class="flex items-center gap-1.5 pt-1">
        <Checkbox
          id="f-no-size"
          :model-value="modelValue.has_no_size"
          @update:modelValue="update('has_no_size', $event)"
        />
        <Label for="f-no-size" class="text-xs text-muted-foreground cursor-pointer">无尺寸数据</Label>
      </div>
    </div>

    <!-- Locality (text, fuzzy on backend) -->
    <div class="space-y-1.5">
      <Label for="f-locality">产地 / Locality</Label>
      <Input id="f-locality" :model-value="modelValue.locality" placeholder="模糊搜索，如 Philippines" @update:modelValue="update('locality', $event)" />
    </div>

    <div class="space-y-1.5">
      <Label for="f-seller">卖家 / Seller</Label>
      <Input id="f-seller" :model-value="modelValue.seller" placeholder="" @update:modelValue="update('seller', $event)" />
    </div>
    <div class="space-y-1.5">
      <Label for="f-is-sold">成交状态</Label>
      <select
        id="f-is-sold"
        :value="modelValue.is_sold"
        @change="update('is_sold', $event.target.value)"
        class="flex h-9 w-full rounded-md border border-input bg-background px-3 py-1 text-sm shadow-sm transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
      >
        <option value="">全部</option>
        <option value="true">已卖出</option>
        <option value="false">未卖出</option>
      </select>
    </div>
    <div class="space-y-1.5">
      <Label>价格区间 / Price (€)</Label>
      <div class="flex items-center gap-2">
        <Input class="flex-1 min-w-0" type="number" :model-value="modelValue.price_min" placeholder="最低" @update:modelValue="update('price_min', $event === '' ? null : Number($event))" />
        <span class="text-muted-foreground shrink-0">—</span>
        <Input class="flex-1 min-w-0" type="number" :model-value="modelValue.price_max" placeholder="最高" @update:modelValue="update('price_max', $event === '' ? null : Number($event))" />
      </div>
    </div>
    <div class="space-y-1.5">
      <Label for="f-date-from">起始日期 / From</Label>
      <Input id="f-date-from" type="date" :model-value="modelValue.end_date_from" @update:modelValue="update('end_date_from', $event || null)" />
    </div>
    <div class="space-y-1.5">
      <Label for="f-date-to">截止日期 / To</Label>
      <Input id="f-date-to" type="date" :model-value="modelValue.end_date_to" @update:modelValue="update('end_date_to', $event || null)" />
    </div>
  </div>
</template>

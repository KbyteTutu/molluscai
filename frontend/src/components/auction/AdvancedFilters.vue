<script setup>
import Input from '@/components/ui/Input.vue'
import Label from '@/components/ui/Label.vue'

const props = defineProps({ modelValue: { type: Object, required: true } })
const emit = defineEmits(['update:modelValue'])

function update(field, value) {
  emit('update:modelValue', { ...props.modelValue, [field]: value })
}
</script>

<template>
  <div class="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
    <div class="space-y-1.5">
      <Label for="f-family">科 / Family</Label>
      <Input id="f-family" :model-value="modelValue.family" placeholder="例: Conidae" @update:modelValue="update('family', $event)" />
    </div>
    <div class="space-y-1.5">
      <Label for="f-size">尺寸 / Size</Label>
      <Input id="f-size" :model-value="modelValue.size" placeholder="例: 50 mm" @update:modelValue="update('size', $event)" />
    </div>
    <div class="space-y-1.5">
      <Label for="f-locality">产地 / Locality</Label>
      <Input id="f-locality" :model-value="modelValue.locality" placeholder="例: Philippines" @update:modelValue="update('locality', $event)" />
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
        <Input type="number" :model-value="modelValue.price_min" placeholder="最低" @update:modelValue="update('price_min', $event === '' ? null : Number($event))" />
        <span class="text-muted-foreground">—</span>
        <Input type="number" :model-value="modelValue.price_max" placeholder="最高" @update:modelValue="update('price_max', $event === '' ? null : Number($event))" />
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

<template>
  <div class="result-table-wrapper">
    <el-table
      :data="data"
      v-loading="loading"
      stripe
      highlight-current-row
      style="width: 100%"
      @row-click="handleRowClick"
      empty-text="暂无搜索结果"
      :default-sort="{ prop: 'item_no', order: 'descending' }"
    >
      <el-table-column
        prop="item_no"
        label="编号"
        width="80"
        sortable
      />

      <el-table-column
        prop="name"
        label="名称"
        min-width="180"
        show-overflow-tooltip
      />

      <el-table-column
        prop="family"
        label="科"
        width="120"
        show-overflow-tooltip
      />

      <el-table-column
        prop="size"
        label="尺寸"
        width="120"
        show-overflow-tooltip
      />

      <el-table-column
        prop="locality"
        label="产地"
        width="140"
        show-overflow-tooltip
      />

      <el-table-column
        prop="seller"
        label="卖家"
        width="120"
        show-overflow-tooltip
      />

      <el-table-column
        prop="start_price"
        label="起拍价"
        width="110"
        sortable
      >
        <template #default="{ row }">
          <span v-if="row.start_price">¥{{ formatPrice(row.start_price) }}</span>
          <span v-else class="text-muted">-</span>
        </template>
      </el-table-column>

      <el-table-column
        prop="final_price"
        label="成交价"
        width="110"
        sortable
      >
        <template #default="{ row }">
          <span v-if="row.final_price" class="price-highlight">
            ¥{{ formatPrice(row.final_price) }}
          </span>
          <span v-else class="text-muted">-</span>
        </template>
      </el-table-column>

      <el-table-column
        prop="end_date"
        label="结束日期"
        width="120"
        sortable
      />

      <el-table-column
        prop="is_sold"
        label="状态"
        width="80"
        align="center"
      >
        <template #default="{ row }">
          <el-tag :type="row.is_sold ? 'success' : 'danger'" size="small">
            {{ row.is_sold ? '已售' : '未售' }}
          </el-tag>
        </template>
      </el-table-column>
    </el-table>
  </div>
</template>

<script setup>
defineProps({
  data: {
    type: Array,
    default: () => []
  },
  loading: {
    type: Boolean,
    default: false
  }
})

const emit = defineEmits(['rowClick'])

function handleRowClick(row) {
  emit('rowClick', row)
}

function formatPrice(price) {
  if (price === null || price === undefined) return '-'
  return Number(price).toLocaleString('zh-CN', {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2
  })
}
</script>

<style scoped>
.result-table-wrapper {
  width: 100%;
  overflow-x: auto;
}

.result-table-wrapper :deep(.el-table__row) {
  cursor: pointer;
}

.text-muted {
  color: #c0c4cc;
}

.price-highlight {
  color: #e6a23c;
  font-weight: 600;
}
</style>

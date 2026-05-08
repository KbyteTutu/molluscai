<template>
  <div class="auction-search-page">
    <el-card class="search-section" shadow="hover">
      <h2 class="section-title">拍卖数据搜索</h2>
      <SearchForm @search="handleSearch" :loading="searchStore.loading" />
    </el-card>

    <el-card class="results-section" shadow="hover" v-if="searchStore.hasResults || searchStore.loading">
      <h3 class="section-title">
        搜索结果
        <span class="result-count" v-if="searchStore.total > 0">
          共 {{ searchStore.total }} 条
        </span>
      </h3>

      <el-alert
        v-if="searchStore.error"
        :title="searchStore.error"
        type="error"
        show-icon
        :closable="true"
        class="error-alert"
        @close="searchStore.clearResults()"
      />

      <ResultTable
        :data="searchStore.results"
        :loading="searchStore.loading"
        @row-click="showDetail"
      />

      <div class="pagination-wrapper" v-if="searchStore.total > 0">
        <el-pagination
          v-model:current-page="searchStore.currentPage"
          :page-size="searchStore.pageSize"
          :total="Math.min(searchStore.total, 500)"
          layout="prev, pager, next"
          :disabled="searchStore.loading"
          @current-change="handlePageChange"
        />
      </div>
    </el-card>

    <div class="empty-hint" v-if="!searchStore.hasResults && !searchStore.loading">
      <el-empty description="请使用上方搜索栏查询拍卖数据">
        <template #image>
          <el-icon :size="64" color="#c0c4cc"><Search /></el-icon>
        </template>
      </el-empty>
    </div>

    <!-- Auction Detail Dialog -->
    <el-dialog
      v-model="detailVisible"
      :title="detailItem ? `拍品 #${detailItem.item_no}` : '拍品详情'"
      width="700px"
      destroy-on-close
    >
      <template v-if="detailItem">
        <el-descriptions :column="2" border>
          <el-descriptions-item label="拍品编号">{{ detailItem.item_no }}</el-descriptions-item>
          <el-descriptions-item label="名称">{{ detailItem.name }}</el-descriptions-item>
          <el-descriptions-item label="科">{{ detailItem.family || '-' }}</el-descriptions-item>
          <el-descriptions-item label="尺寸">{{ detailItem.size || '-' }}</el-descriptions-item>
          <el-descriptions-item label="产地">{{ detailItem.locality || '-' }}</el-descriptions-item>
          <el-descriptions-item label="卖家">{{ detailItem.seller || '-' }}</el-descriptions-item>
          <el-descriptions-item label="起拍价">
            <span v-if="detailItem.start_price">¥{{ formatPrice(detailItem.start_price) }}</span>
            <span v-else>-</span>
          </el-descriptions-item>
          <el-descriptions-item label="成交价">
            <span v-if="detailItem.final_price" class="price-highlight">
              ¥{{ formatPrice(detailItem.final_price) }}
            </span>
            <span v-else>-</span>
          </el-descriptions-item>
          <el-descriptions-item label="结束日期">{{ detailItem.end_date || '-' }}</el-descriptions-item>
          <el-descriptions-item label="买家">{{ detailItem.buyer || '-' }}</el-descriptions-item>
          <el-descriptions-item label="状态" :span="2">
            <el-tag :type="detailItem.is_sold ? 'success' : 'danger'">
              {{ detailItem.is_sold ? '已售' : '未售' }}
            </el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="备注" :span="2">
            {{ detailItem.note || '无' }}
          </el-descriptions-item>
        </el-descriptions>
      </template>
      <div v-else v-loading="detailLoading" style="min-height: 200px"></div>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useSearchStore } from '@/stores/search'
import { auctionApi } from '@/api'
import SearchForm from '@/components/SearchForm.vue'
import ResultTable from '@/components/ResultTable.vue'
import { Search } from '@element-plus/icons-vue'

const searchStore = useSearchStore()

const detailVisible = ref(false)
const detailItem = ref(null)
const detailLoading = ref(false)

let lastSearchParams = null

async function handleSearch(params) {
  lastSearchParams = { ...params, offset: 0, limit: searchStore.pageSize }
  searchStore.currentPage = 1
  await searchStore.searchAuctions(lastSearchParams)
}

async function handlePageChange(page) {
  if (!lastSearchParams) return
  const offset = (page - 1) * searchStore.pageSize
  if (offset > 500) {
    return // Block deep pagination per design.md
  }
  lastSearchParams.offset = offset
  await searchStore.searchAuctions(lastSearchParams)
}

async function showDetail(item) {
  detailVisible.value = true
  detailItem.value = null
  detailLoading.value = true
  try {
    const response = await auctionApi.getDetail(item.item_no)
    detailItem.value = response.data
  } catch (err) {
    detailItem.value = null
  } finally {
    detailLoading.value = false
  }
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
.auction-search-page {
  max-width: 1200px;
  margin: 0 auto;
}

.search-section {
  margin-bottom: 20px;
}

.results-section {
  margin-bottom: 20px;
}

.section-title {
  margin: 0 0 16px 0;
  font-size: 18px;
  color: #303133;
}

.result-count {
  font-size: 14px;
  font-weight: normal;
  color: #909399;
  margin-left: 12px;
}

.error-alert {
  margin-bottom: 16px;
}

.pagination-wrapper {
  display: flex;
  justify-content: center;
  margin-top: 20px;
}

.empty-hint {
  padding: 40px 0;
}

.price-highlight {
  color: #e6a23c;
  font-weight: 600;
}
</style>

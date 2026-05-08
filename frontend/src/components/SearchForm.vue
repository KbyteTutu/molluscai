<template>
  <el-form
    ref="formRef"
    :model="formData"
    label-position="top"
    class="search-form"
  >
    <el-row :gutter="16">
      <el-col :span="8">
        <el-form-item label="名称">
          <el-input
            v-model="formData.name"
            placeholder="拍品名称（支持模糊搜索）"
            clearable
            @keyup.enter="emitSearch"
          />
        </el-form-item>
      </el-col>

      <el-col :span="8">
        <el-form-item label="科">
          <el-input
            v-model="formData.family"
            placeholder="科名"
            clearable
            @keyup.enter="emitSearch"
          />
        </el-form-item>
      </el-col>

      <el-col :span="8">
        <el-form-item label="尺寸">
          <el-input
            v-model="formData.size"
            placeholder="尺寸描述"
            clearable
            @keyup.enter="emitSearch"
          />
        </el-form-item>
      </el-col>
    </el-row>

    <el-row :gutter="16">
      <el-col :span="8">
        <el-form-item label="产地">
          <el-input
            v-model="formData.locality"
            placeholder="产地"
            clearable
            @keyup.enter="emitSearch"
          />
        </el-form-item>
      </el-col>

      <el-col :span="8">
        <el-form-item label="卖家">
          <el-input
            v-model="formData.seller"
            placeholder="卖家名称"
            clearable
            @keyup.enter="emitSearch"
          />
        </el-form-item>
      </el-col>

      <el-col :span="8">
        <el-form-item label="买家">
          <el-input
            v-model="formData.buyer"
            placeholder="买家名称"
            clearable
            @keyup.enter="emitSearch"
          />
        </el-form-item>
      </el-col>
    </el-row>

    <el-row :gutter="16">
      <el-col :span="6">
        <el-form-item label="最低价格">
          <el-input-number
            v-model="formData.price_min"
            :min="0"
            :precision="2"
            :controls="true"
            placeholder="¥"
            style="width: 100%"
          />
        </el-form-item>
      </el-col>

      <el-col :span="6">
        <el-form-item label="最高价格">
          <el-input-number
            v-model="formData.price_max"
            :min="0"
            :precision="2"
            :controls="true"
            placeholder="¥"
            style="width: 100%"
          />
        </el-form-item>
      </el-col>

      <el-col :span="6">
        <el-form-item label="结束日期起">
          <el-date-picker
            v-model="formData.end_date_from"
            type="date"
            placeholder="开始日期"
            value-format="YYYY-MM-DD"
            style="width: 100%"
          />
        </el-form-item>
      </el-col>

      <el-col :span="6">
        <el-form-item label="结束日期止">
          <el-date-picker
            v-model="formData.end_date_to"
            type="date"
            placeholder="结束日期"
            value-format="YYYY-MM-DD"
            style="width: 100%"
          />
        </el-form-item>
      </el-col>
    </el-row>

    <el-row>
      <el-col :span="24">
        <el-form-item>
          <el-button
            type="primary"
            :loading="loading"
            :icon="Search"
            @click="emitSearch"
          >
            搜索
          </el-button>
          <el-button
            :disabled="loading"
            @click="resetForm"
          >
            重置
          </el-button>
        </el-form-item>
      </el-col>
    </el-row>
  </el-form>
</template>

<script setup>
import { reactive, ref } from 'vue'
import { Search } from '@element-plus/icons-vue'

const props = defineProps({
  loading: {
    type: Boolean,
    default: false
  }
})

const emit = defineEmits(['search'])

const formRef = ref(null)

const formData = reactive({
  name: '',
  family: '',
  size: '',
  locality: '',
  seller: '',
  buyer: '',
  price_min: null,
  price_max: null,
  end_date_from: '',
  end_date_to: ''
})

function buildSearchParams() {
  const params = {}
  for (const [key, value] of Object.entries(formData)) {
    if (value !== '' && value !== null && value !== undefined) {
      params[key] = value
    }
  }
  return params
}

function emitSearch() {
  const params = buildSearchParams()
  emit('search', params)
}

function resetForm() {
  formData.name = ''
  formData.family = ''
  formData.size = ''
  formData.locality = ''
  formData.seller = ''
  formData.buyer = ''
  formData.price_min = null
  formData.price_max = null
  formData.end_date_from = ''
  formData.end_date_to = ''
}
</script>

<style scoped>
.search-form {
  margin-top: 8px;
}
</style>

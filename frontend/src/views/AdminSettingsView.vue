<script setup>
import { ref, onMounted } from 'vue'
import { adminApi } from '@/api'
import { toast } from 'vue-sonner'
import { Settings, Database } from 'lucide-vue-next'
import Card from '@/components/ui/Card.vue'
import CardHeader from '@/components/ui/CardHeader.vue'
import CardTitle from '@/components/ui/CardTitle.vue'
import CardDescription from '@/components/ui/CardDescription.vue'
import CardContent from '@/components/ui/CardContent.vue'
import Switch from '@/components/ui/Switch.vue'
import Button from '@/components/ui/Button.vue'

const settings = ref({
  smart_search_auction: false,
  smart_search_taxa: false,
  smart_search_documents: false
})
const loading = ref(true)

async function fetchSettings() {
  loading.value = true
  try {
    const res = await adminApi.getSettings()
    if (res.data) {
      settings.value = res.data
    }
  } catch (error) {
    toast.error('加载设置失败')
  } finally {
    loading.value = false
  }
}

async function updateSetting(key, value) {
  const originalValue = settings.value[key]
  settings.value[key] = value
  
  try {
    await adminApi.updateSettings({ [key]: value })
    toast.success('设置已保存')
  } catch (error) {
    settings.value[key] = originalValue
    toast.error('保存设置失败')
  }
}

async function handleCleanup(target) {
  if (!confirm('确定要删除所有向量数据吗？此操作不可撤销。')) return
  
  try {
    await adminApi.cleanupVectors(target)
    toast.success('向量数据清理任务已提交')
  } catch (error) {
    toast.error('清理向量数据失败')
  }
}

onMounted(() => {
  fetchSettings()
})
</script>

<template>
  <div class="space-y-6">
    <div class="flex items-center gap-2">
      <Settings class="h-6 w-6 text-slate-500" />
      <h1 class="text-2xl font-bold tracking-tight text-slate-900 dark:text-slate-100">系统设置</h1>
    </div>

    <div class="grid gap-6 md:grid-cols-2">
      <Card>
        <CardHeader>
          <CardTitle>智能检索开关</CardTitle>
          <CardDescription>控制各模块的向量检索功能</CardDescription>
        </CardHeader>
        <CardContent class="space-y-6">
          <div class="flex items-center justify-between">
            <div class="space-y-0.5">
              <label class="text-sm font-medium text-slate-900 dark:text-slate-100">拍卖智能检索</label>
              <p class="text-sm text-slate-500 dark:text-slate-400">启用后拍卖搜索支持语义匹配（消耗 embedding API 费用）</p>
            </div>
            <Switch
              :checked="settings.smart_search_auction"
              @update:checked="(val) => updateSetting('smart_search_auction', val)"
              :disabled="loading"
            />
          </div>
          <div class="flex items-center justify-between">
            <div class="space-y-0.5">
              <label class="text-sm font-medium text-slate-900 dark:text-slate-100">物种智能检索</label>
              <p class="text-sm text-slate-500 dark:text-slate-400">启用后物种搜索支持向量混合检索</p>
            </div>
            <Switch
              :checked="settings.smart_search_taxa"
              @update:checked="(val) => updateSetting('smart_search_taxa', val)"
              :disabled="loading"
            />
          </div>
          <div class="flex items-center justify-between">
            <div class="space-y-0.5">
              <label class="text-sm font-medium text-slate-900 dark:text-slate-100">文献智能检索</label>
              <p class="text-sm text-slate-500 dark:text-slate-400">启用后知识库文献支持语义检索（P2 阶段）</p>
            </div>
            <Switch
              :checked="settings.smart_search_documents"
              @update:checked="(val) => updateSetting('smart_search_documents', val)"
              :disabled="loading"
            />
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle class="flex items-center gap-2">
            <Database class="h-5 w-5" />
            向量数据管理
          </CardTitle>
          <CardDescription>清理已生成的向量嵌入数据</CardDescription>
        </CardHeader>
        <CardContent class="space-y-6">
          <div class="flex items-center justify-between">
            <div class="space-y-0.5">
              <label class="text-sm font-medium text-slate-900 dark:text-slate-100">拍卖向量</label>
              <p class="text-sm text-slate-500 dark:text-slate-400">已嵌入约 152 万条（约 21 GB）</p>
            </div>
            <Button variant="destructive" size="sm" @click="handleCleanup('auctions')">
              清理
            </Button>
          </div>
          <div class="flex items-center justify-between">
            <div class="space-y-0.5">
              <label class="text-sm font-medium text-slate-900 dark:text-slate-100">物种向量</label>
              <p class="text-sm text-slate-500 dark:text-slate-400">已嵌入约 31.5 万条（约 4 GB）</p>
            </div>
            <Button variant="destructive" size="sm" @click="handleCleanup('taxa')">
              清理
            </Button>
          </div>
        </CardContent>
      </Card>
    </div>
  </div>
</template>

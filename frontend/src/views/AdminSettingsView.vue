<script setup>
import { ref, onMounted, onBeforeUnmount } from 'vue'
import { adminApi } from '@/api'
import { toast } from 'vue-sonner'
import { Settings, Database, Bell, Plus, Trash2 } from 'lucide-vue-next'
import Card from '@/components/ui/Card.vue'
import CardHeader from '@/components/ui/CardHeader.vue'
import CardTitle from '@/components/ui/CardTitle.vue'
import CardDescription from '@/components/ui/CardDescription.vue'
import CardContent from '@/components/ui/CardContent.vue'
import Switch from '@/components/ui/Switch.vue'
import Button from '@/components/ui/Button.vue'
import Input from '@/components/ui/Input.vue'

const settings = ref({
  smart_search_auction: false,
  smart_search_taxa: false,
  smart_search_documents: false
})
const loading = ref(true)
const noticeSaving = ref(false)
const updateNotices = ref([])

const REFRESH_INTERVAL = 15000
let pollTimer = null

function startPolling() { stopPolling(); pollTimer = setInterval(fetchSettings, REFRESH_INTERVAL) }
function stopPolling() { if (pollTimer) { clearInterval(pollTimer); pollTimer = null } }

function normalizeNotices(items) {
  if (!Array.isArray(items)) return []
  return items.map((item) => ({
    date: item.date || '',
    title: item.title || '',
    text: item.text || ''
  }))
}

async function fetchSettings() {
  loading.value = true
  try {
    const res = await adminApi.getSettings()
    if (res.data) {
      settings.value = {
        smart_search_auction: res.data.smart_search_auction === 'true',
        smart_search_taxa: res.data.smart_search_taxa === 'true',
        smart_search_documents: res.data.smart_search_documents === 'true',
      }
      updateNotices.value = normalizeNotices(res.data.update_notices?.items)
    }
  } catch (error) {
    toast.error('加载设置失败')
  } finally {
    loading.value = false
  }
}

function addNotice() {
  updateNotices.value.push({ date: new Date().toISOString().slice(0, 10), title: '', text: '' })
}

function removeNotice(index) {
  updateNotices.value.splice(index, 1)
}

async function saveNotices() {
  const items = updateNotices.value
    .map((item) => ({
      date: item.date.trim(),
      title: item.title.trim(),
      text: item.text.trim()
    }))
    .filter((item) => item.date || item.title || item.text)

  if (items.some((item) => !item.date || !item.title || !item.text)) {
    toast.error('公告日期、标题和内容都不能为空')
    return
  }

  noticeSaving.value = true
  try {
    const res = await adminApi.updateNotices({ items })
    updateNotices.value = normalizeNotices(res.data.items)
    toast.success('公告已保存')
  } catch (error) {
    toast.error(error.response?.data?.detail || '保存公告失败')
  } finally {
    noticeSaving.value = false
  }
}

async function updateSetting(key, value) {
  const originalValue = settings.value[key]
  settings.value[key] = value

  try {
    await adminApi.updateSettings({ [key]: value ? 'true' : 'false' })
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
  startPolling()
})
onBeforeUnmount(stopPolling)
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
          <div v-if="false" class="flex items-center justify-between">
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

      <Card class="md:col-span-2">
        <CardHeader>
          <CardTitle class="flex items-center gap-2">
            <Bell class="h-5 w-5" />
            功能更新公告
          </CardTitle>
          <CardDescription>控制左下角“更新”面板展示的简短公告</CardDescription>
        </CardHeader>
        <CardContent class="space-y-4">
          <div v-if="!updateNotices.length" class="rounded-md border border-dashed p-4 text-sm text-slate-500 dark:text-slate-400">
            暂无公告
          </div>

          <div v-for="(notice, index) in updateNotices" :key="index" class="grid gap-3 rounded-md border p-3 md:grid-cols-[9rem_1fr_auto]">
            <Input v-model="notice.date" placeholder="YYYY-MM-DD" class="h-9" />
            <div class="grid gap-3 md:grid-cols-2">
              <Input v-model="notice.title" placeholder="标题" class="h-9" />
              <Input v-model="notice.text" placeholder="一句话内容" class="h-9" />
            </div>
            <Button variant="ghost" size="icon" title="删除" @click="removeNotice(index)">
              <Trash2 class="h-4 w-4" />
            </Button>
          </div>

          <div class="flex flex-col gap-2 sm:flex-row sm:justify-between">
            <Button variant="outline" size="sm" @click="addNotice">
              <Plus class="h-4 w-4" /> 添加公告
            </Button>
            <Button size="sm" :disabled="noticeSaving" @click="saveNotices">
              {{ noticeSaving ? '保存中…' : '保存公告' }}
            </Button>
          </div>
        </CardContent>
      </Card>
    </div>
  </div>
</template>

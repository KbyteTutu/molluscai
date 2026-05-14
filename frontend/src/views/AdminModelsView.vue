<script setup>
import { ref, onMounted, computed } from 'vue'
import { adminApi } from '@/api'
import {
  Plus, Trash2, PlayCircle, CheckCircle2, XCircle, Loader2, RefreshCw, Zap
} from 'lucide-vue-next'
import Card from '@/components/ui/Card.vue'
import CardHeader from '@/components/ui/CardHeader.vue'
import CardTitle from '@/components/ui/CardTitle.vue'
import CardDescription from '@/components/ui/CardDescription.vue'
import CardContent from '@/components/ui/CardContent.vue'
import CardFooter from '@/components/ui/CardFooter.vue'
import Input from '@/components/ui/Input.vue'
import Label from '@/components/ui/Label.vue'
import Button from '@/components/ui/Button.vue'
import Badge from '@/components/ui/Badge.vue'
import Separator from '@/components/ui/Separator.vue'
import Alert from '@/components/ui/Alert.vue'
import AlertTitle from '@/components/ui/AlertTitle.vue'
import AlertDescription from '@/components/ui/AlertDescription.vue'
import Dialog from '@/components/ui/Sheet.vue'
import DialogContent from '@/components/ui/SheetContent.vue'
import DialogHeader from '@/components/ui/SheetHeader.vue'
import DialogTitle from '@/components/ui/SheetTitle.vue'
import DialogDescription from '@/components/ui/SheetDescription.vue'
import { toast } from 'vue-sonner'

const models = ref([])
const loading = ref(false)
const rebuilding = ref(false)
const testing = ref({})
const testResult = ref({})

const openDialog = ref(false)
const editing = ref(null)
const form = ref({
  model_name: '', provider: 'siliconflow', api_key: '', base_url: '',
  model_id: '', purpose: 'embedding',
  price_input: null, price_unit: 'per_1k_tokens', is_active: true
})

const PURPOSES = [
  { value: 'embedding', label: '向量嵌入' },
  { value: 'rerank', label: '重排序' }
]
const PROVIDERS = [
  { value: 'siliconflow', label: 'SiliconFlow', default_base: 'https://api.siliconflow.cn/v1' },
  { value: 'jina', label: 'Jina AI', default_base: 'https://api.jina.ai/v1' },
  { value: 'openai', label: 'OpenAI', default_base: 'https://api.openai.com/v1' },
  { value: 'voyage', label: 'Voyage AI', default_base: 'https://api.voyageai.com/v1' },
  { value: 'openai_compat', label: '其它 OpenAI 兼容', default_base: '' }
]

const embedModels = computed(() => models.value.filter(m => m.purpose === 'embedding'))
const rerankModels = computed(() => models.value.filter(m => m.purpose === 'rerank'))
const activeEmbed = computed(() => embedModels.value.find(m => m.is_active))

async function load() {
  loading.value = true
  try {
    const { data } = await adminApi.listModels()
    models.value = data
  } catch (e) {
    toast.error(e.response?.data?.detail || '加载失败')
  } finally { loading.value = false }
}

function openCreate(purpose = 'embedding') {
  editing.value = null
  const tmpl = {
    embedding: {
      model_name: 'Qwen/Qwen3-Embedding-8B', provider: 'siliconflow',
      model_id: 'Qwen/Qwen3-Embedding-8B', base_url: 'https://api.siliconflow.cn/v1'
    },
    rerank: {
      model_name: 'Qwen/Qwen3-Reranker-8B', provider: 'siliconflow',
      model_id: 'Qwen/Qwen3-Reranker-8B', base_url: 'https://api.siliconflow.cn/v1'
    }
  }
  form.value = {
    ...tmpl[purpose],
    api_key: '', purpose,
    price_input: null, price_unit: 'per_1k_tokens', is_active: true
  }
  openDialog.value = true
}

function openEdit(m) {
  editing.value = m
  form.value = {
    model_name: m.model_name, provider: m.provider, api_key: '',
    base_url: m.base_url, model_id: m.model_id, purpose: m.purpose,
    price_input: m.price_input, price_unit: m.price_unit,
    is_active: m.is_active
  }
  openDialog.value = true
}

function applyProviderDefaults() {
  const pv = PROVIDERS.find(p => p.value === form.value.provider)
  if (pv?.default_base && !form.value.base_url) form.value.base_url = pv.default_base
}

async function save() {
  const payload = { ...form.value }
  if (payload.price_input === '' || payload.price_input === null) delete payload.price_input
  try {
    if (editing.value) {
      if (!payload.api_key) delete payload.api_key
      await adminApi.updateModel(editing.value.id, payload)
      toast.success('已更新')
    } else {
      if (!payload.api_key) { toast.error('API Key 必填'); return }
      await adminApi.createModel(payload)
      toast.success('已创建')
    }
    openDialog.value = false
    await load()
  } catch (e) {
    toast.error(e.response?.data?.detail || '保存失败')
  }
}

async function remove(m) {
  if (!confirm(`删除 ${m.model_name} ?`)) return
  try {
    await adminApi.deleteModel(m.id)
    toast.success('已删除')
    await load()
  } catch (e) { toast.error(e.response?.data?.detail || '删除失败') }
}

async function activate(m) {
  try {
    await adminApi.updateModel(m.id, { is_active: true })
    toast.success(`已启用 ${m.model_name}`)
    await load()
  } catch (e) { toast.error(e.response?.data?.detail || '启用失败') }
}

async function test(m) {
  testing.value = { ...testing.value, [m.id]: true }
  try {
    const { data } = await adminApi.testModel(m.id)
    testResult.value = { ...testResult.value, [m.id]: data }
    if (data.success) toast.success(`连通 · ${data.latency_ms}ms${data.sample_dim ? ' · dim=' + data.sample_dim : ''}`)
    else toast.error(`失败 · ${data.message}`)
  } catch (e) {
    testResult.value = { ...testResult.value, [m.id]: { success: false, message: e.message } }
    toast.error('测试失败 · ' + e.message)
  } finally {
    testing.value = { ...testing.value, [m.id]: false }
  }
}

async function runEmbed(rebuild = false) {
  if (rebuild && !confirm('确认对全部物种重新生成向量？旧向量将被丢弃。')) return
  rebuilding.value = true
  try {
    const { data } = await adminApi.runEmbed({ rebuild })
    toast.success(`任务已派发 · ${data.task_id.slice(0, 8)}…`, {
      description: rebuild ? '全量重建中，可前往用量统计查看进度' : '增量嵌入中'
    })
  } catch (e) {
    toast.error(e.response?.data?.detail || '派发失败')
  } finally { rebuilding.value = false }
}

onMounted(load)
</script>

<template>
  <div class="space-y-6">
    <header class="flex items-end justify-between flex-wrap gap-3">
      <div class="space-y-1">
        <h1 class="font-serif text-3xl font-semibold tracking-tight">模型配置</h1>
        <p class="text-sm text-muted-foreground">管理向量嵌入与重排序模型 · 仅超级管理员可见</p>
      </div>
      <Button variant="outline" size="sm" @click="load">
        <RefreshCw class="size-4" /> 刷新
      </Button>
    </header>

    <Alert v-if="!activeEmbed" variant="destructive">
      <AlertTitle>未启用 embedding 模型</AlertTitle>
      <AlertDescription>
        未配置或未启用向量嵌入模型 · 检索将回退到纯词法模糊匹配
      </AlertDescription>
    </Alert>

    <Card v-if="activeEmbed">
      <CardHeader>
        <div class="flex items-center gap-2 text-primary">
          <Zap class="size-5" />
          <CardTitle class="text-lg">向量生成</CardTitle>
        </div>
        <CardDescription>
          使用 <span class="font-mono">{{ activeEmbed.model_name }}</span> 对全部 141,670 条物种生成向量。
          增量模式只嵌入尚未处理的条目；重建模式会先清空再全量。
        </CardDescription>
      </CardHeader>
      <CardFooter class="gap-2">
        <Button size="sm" :disabled="rebuilding" @click="runEmbed(false)">
          增量嵌入
        </Button>
        <Button size="sm" variant="destructive" :disabled="rebuilding" @click="runEmbed(true)">
          全量重建
        </Button>
      </CardFooter>
    </Card>

    <section class="space-y-3">
      <div class="flex items-center justify-between">
        <h2 class="font-serif text-xl">向量嵌入模型 · Embedding</h2>
        <Button size="sm" variant="outline" @click="openCreate('embedding')">
          <Plus class="size-4" /> 添加
        </Button>
      </div>
      <Card v-if="!embedModels.length" class="p-8 text-center text-sm text-muted-foreground">
        暂无配置 · 点「添加」创建第一个
      </Card>
      <Card v-for="m in embedModels" :key="m.id" class="p-4">
        <div class="flex items-start justify-between gap-4 flex-wrap">
          <div class="flex-1 min-w-0 space-y-1.5">
            <div class="flex items-center gap-2 flex-wrap">
              <span class="font-mono text-sm font-medium">{{ m.model_name }}</span>
              <Badge v-if="m.is_active" variant="default" class="text-[10px] uppercase">启用</Badge>
              <Badge v-else variant="muted" class="text-[10px] uppercase">停用</Badge>
              <Badge variant="outline" class="text-[10px]">{{ m.provider }}</Badge>
            </div>
            <div class="text-xs text-muted-foreground space-x-3">
              <span v-if="m.base_url">base: <span class="font-mono">{{ m.base_url }}</span></span>
              <span v-if="m.model_id">id: <span class="font-mono">{{ m.model_id }}</span></span>
              <span v-if="m.api_key_tail">key: <span class="font-mono">{{ m.api_key_tail }}</span></span>
            </div>
            <div v-if="m.price_input" class="text-xs text-muted-foreground">
              单价: ¥{{ m.price_input }} / {{ m.price_unit === 'per_1k_tokens' ? '1K' : '1M' }} tokens
            </div>
            <div v-if="testResult[m.id]" class="text-xs">
              <CheckCircle2 v-if="testResult[m.id].success" class="inline size-3 text-primary mr-1" />
              <XCircle v-else class="inline size-3 text-destructive mr-1" />
              <span class="text-muted-foreground">{{ testResult[m.id].message }}</span>
            </div>
          </div>
          <div class="flex items-center gap-1.5">
            <Button size="sm" variant="ghost" :disabled="testing[m.id]" @click="test(m)">
              <Loader2 v-if="testing[m.id]" class="size-4 animate-spin" />
              <PlayCircle v-else class="size-4" />
              测试
            </Button>
            <Button v-if="!m.is_active" size="sm" variant="outline" @click="activate(m)">启用</Button>
            <Button size="sm" variant="ghost" @click="openEdit(m)">编辑</Button>
            <Button size="sm" variant="ghost" class="text-destructive" @click="remove(m)">
              <Trash2 class="size-4" />
            </Button>
          </div>
        </div>
      </Card>
    </section>

    <section class="space-y-3">
      <div class="flex items-center justify-between">
        <h2 class="font-serif text-xl">重排序模型 · Rerank</h2>
        <Button size="sm" variant="outline" @click="openCreate('rerank')">
          <Plus class="size-4" /> 添加
        </Button>
      </div>
      <Card v-if="!rerankModels.length" class="p-8 text-center text-sm text-muted-foreground">
        暂无配置
      </Card>
      <Card v-for="m in rerankModels" :key="m.id" class="p-4">
        <div class="flex items-start justify-between gap-4 flex-wrap">
          <div class="flex-1 min-w-0 space-y-1.5">
            <div class="flex items-center gap-2 flex-wrap">
              <span class="font-mono text-sm font-medium">{{ m.model_name }}</span>
              <Badge v-if="m.is_active" variant="default" class="text-[10px] uppercase">启用</Badge>
              <Badge v-else variant="muted" class="text-[10px] uppercase">停用</Badge>
              <Badge variant="outline" class="text-[10px]">{{ m.provider }}</Badge>
            </div>
            <div class="text-xs text-muted-foreground space-x-3">
              <span v-if="m.base_url">base: <span class="font-mono">{{ m.base_url }}</span></span>
              <span v-if="m.model_id">id: <span class="font-mono">{{ m.model_id }}</span></span>
              <span v-if="m.api_key_tail">key: <span class="font-mono">{{ m.api_key_tail }}</span></span>
            </div>
            <div v-if="testResult[m.id]" class="text-xs">
              <CheckCircle2 v-if="testResult[m.id].success" class="inline size-3 text-primary mr-1" />
              <XCircle v-else class="inline size-3 text-destructive mr-1" />
              <span class="text-muted-foreground">{{ testResult[m.id].message }}</span>
            </div>
          </div>
          <div class="flex items-center gap-1.5">
            <Button size="sm" variant="ghost" :disabled="testing[m.id]" @click="test(m)">
              <Loader2 v-if="testing[m.id]" class="size-4 animate-spin" />
              <PlayCircle v-else class="size-4" /> 测试
            </Button>
            <Button v-if="!m.is_active" size="sm" variant="outline" @click="activate(m)">启用</Button>
            <Button size="sm" variant="ghost" @click="openEdit(m)">编辑</Button>
            <Button size="sm" variant="ghost" class="text-destructive" @click="remove(m)">
              <Trash2 class="size-4" />
            </Button>
          </div>
        </div>
      </Card>
    </section>

    <Dialog v-model:open="openDialog">
      <DialogContent side="right" class="w-full sm:max-w-lg">
        <DialogHeader>
          <DialogTitle>{{ editing ? '编辑模型' : '添加模型' }}</DialogTitle>
          <DialogDescription>
            填写 Provider、base URL、API Key、模型 ID。API Key 以明文形式保存于数据库（仅 superadmin 可读取列表）
          </DialogDescription>
        </DialogHeader>
        <div class="space-y-4">
          <div class="space-y-1.5">
            <Label>用途 Purpose</Label>
            <select v-model="form.purpose" class="h-9 w-full rounded-md border border-input bg-background px-2 text-sm" :disabled="!!editing">
              <option v-for="p in PURPOSES" :key="p.value" :value="p.value">{{ p.label }}</option>
            </select>
          </div>
          <div class="space-y-1.5">
            <Label>Provider</Label>
            <select v-model="form.provider" @change="applyProviderDefaults" class="h-9 w-full rounded-md border border-input bg-background px-2 text-sm">
              <option v-for="p in PROVIDERS" :key="p.value" :value="p.value">{{ p.label }}</option>
            </select>
          </div>
          <div class="space-y-1.5">
            <Label>显示名称 Model Name</Label>
            <Input v-model="form.model_name" placeholder="Qwen/Qwen3-Embedding-8B" />
          </div>
          <div class="space-y-1.5">
            <Label>Provider 侧模型 ID</Label>
            <Input v-model="form.model_id" placeholder="与 API 请求中的 model 字段一致" />
          </div>
          <div class="space-y-1.5">
            <Label>Base URL</Label>
            <Input v-model="form.base_url" placeholder="https://api.siliconflow.cn/v1" />
          </div>
          <div class="space-y-1.5">
            <Label>API Key <span v-if="editing" class="text-xs text-muted-foreground ml-1">（留空则不变）</span></Label>
            <Input v-model="form.api_key" type="password" :placeholder="editing ? '•••••• 保留现有' : 'sk-...'" />
          </div>
          <div class="grid grid-cols-2 gap-2">
            <div class="space-y-1.5">
              <Label>单价 (可选)</Label>
              <Input v-model.number="form.price_input" type="number" step="0.000001" placeholder="0.007" />
            </div>
            <div class="space-y-1.5">
              <Label>计价单位</Label>
              <select v-model="form.price_unit" class="h-9 w-full rounded-md border border-input bg-background px-2 text-sm">
                <option value="per_1k_tokens">每 1K tokens</option>
                <option value="per_1m_tokens">每 1M tokens</option>
              </select>
            </div>
          </div>
          <label class="flex items-center gap-2 text-sm">
            <input v-model="form.is_active" type="checkbox" /> 启用此模型（同用途将自动停用其它）
          </label>
          <div class="flex justify-end gap-2 pt-4 border-t">
            <Button variant="ghost" @click="openDialog = false">取消</Button>
            <Button @click="save">{{ editing ? '保存' : '创建' }}</Button>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  </div>
</template>

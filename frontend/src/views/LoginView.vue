<script setup>
import { ref, reactive, computed } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import ShellLogo from '@/components/brand/ShellLogo.vue'
import Card from '@/components/ui/Card.vue'
import CardHeader from '@/components/ui/CardHeader.vue'
import CardTitle from '@/components/ui/CardTitle.vue'
import CardDescription from '@/components/ui/CardDescription.vue'
import CardContent from '@/components/ui/CardContent.vue'
import Tabs from '@/components/ui/Tabs.vue'
import TabsList from '@/components/ui/TabsList.vue'
import TabsTrigger from '@/components/ui/TabsTrigger.vue'
import TabsContent from '@/components/ui/TabsContent.vue'
import Input from '@/components/ui/Input.vue'
import Label from '@/components/ui/Label.vue'
import Button from '@/components/ui/Button.vue'
import Alert from '@/components/ui/Alert.vue'
import AlertTitle from '@/components/ui/AlertTitle.vue'
import AlertDescription from '@/components/ui/AlertDescription.vue'
import { AlertCircle } from 'lucide-vue-next'
import ThemeToggle from '@/components/layout/ThemeToggle.vue'

const router = useRouter()
const route = useRoute()
const authStore = useAuthStore()

const tab = ref('login')
const loading = ref(false)
const error = ref('')

const loginForm = reactive({ username: '', password: '' })
const registerForm = reactive({ username: '', email: '', password: '' })

const validLogin = computed(() => loginForm.username.trim() && loginForm.password.trim())
const validRegister = computed(() =>
  registerForm.username.trim().length >= 3 &&
  /\S+@\S+\.\S+/.test(registerForm.email) &&
  registerForm.password.length >= 8
)

async function doLogin() {
  if (!validLogin.value) {
    error.value = '请填写完整的用户名和密码'
    return
  }
  loading.value = true
  error.value = ''
  try {
    await authStore.login(loginForm.username, loginForm.password)
    router.push(route.query.redirect || '/')
  } catch (e) {
    error.value = e.response?.data?.detail || '登录失败，请检查凭据'
  } finally {
    loading.value = false
  }
}

async function doRegister() {
  if (!validRegister.value) {
    error.value = '用户名 ≥ 3 字符，邮箱格式正确，密码 ≥ 8 字符'
    return
  }
  loading.value = true
  error.value = ''
  try {
    await authStore.register(registerForm.username, registerForm.email, registerForm.password)
    router.push('/')
  } catch (e) {
    error.value = e.response?.data?.detail || '注册失败'
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="min-h-screen flex items-center justify-center bg-background relative overflow-hidden p-4">
    <div class="absolute -top-24 -right-24 opacity-5 pointer-events-none">
      <ShellLogo :size="480" />
    </div>
    <div class="absolute top-4 right-4">
      <ThemeToggle />
    </div>

    <div class="w-full max-w-md relative">
      <div class="text-center mb-8">
        <div class="inline-flex items-center gap-2.5 mb-3">
          <ShellLogo :size="32" class="text-primary" />
          <h1 class="font-serif text-3xl font-semibold tracking-tight">MolluscAI</h1>
        </div>
        <p class="text-sm text-muted-foreground">软体动物学知识检索平台</p>
        <p class="text-xs text-muted-foreground/70 mt-0.5">Malacology reference platform</p>
      </div>

      <Card>
        <CardHeader class="pb-4">
          <Tabs v-model="tab" class="w-full">
            <TabsList class="w-full grid grid-cols-2">
              <TabsTrigger value="login">登录</TabsTrigger>
              <TabsTrigger value="register">注册</TabsTrigger>
            </TabsList>
          </Tabs>
        </CardHeader>
        <CardContent>
          <Alert v-if="error" variant="destructive" class="mb-4">
            <AlertCircle class="size-4" />
            <AlertTitle>错误</AlertTitle>
            <AlertDescription>{{ error }}</AlertDescription>
          </Alert>

          <form v-if="tab === 'login'" @submit.prevent="doLogin" class="space-y-4">
            <div class="space-y-1.5">
              <Label for="login-username">用户名 / 邮箱</Label>
              <Input id="login-username" v-model="loginForm.username" autocomplete="username" placeholder="用户名或邮箱" />
            </div>
            <div class="space-y-1.5">
              <Label for="login-password">密码</Label>
              <Input id="login-password" v-model="loginForm.password" type="password" autocomplete="current-password" />
            </div>
            <Button type="submit" class="w-full" :disabled="loading">
              {{ loading ? '验证中…' : '登录' }}
            </Button>
          </form>

          <form v-else @submit.prevent="doRegister" class="space-y-4">
            <div class="space-y-1.5">
              <Label for="reg-username">用户名</Label>
              <Input id="reg-username" v-model="registerForm.username" autocomplete="username" />
            </div>
            <div class="space-y-1.5">
              <Label for="reg-email">邮箱</Label>
              <Input id="reg-email" v-model="registerForm.email" type="email" autocomplete="email" />
            </div>
            <div class="space-y-1.5">
              <Label for="reg-password">密码 <span class="text-muted-foreground text-xs ml-1">至少 8 位</span></Label>
              <Input id="reg-password" v-model="registerForm.password" type="password" autocomplete="new-password" />
            </div>
            <Button type="submit" class="w-full" :disabled="loading">
              {{ loading ? '创建中…' : '创建账户' }}
            </Button>
          </form>
        </CardContent>
      </Card>

      <p class="text-center text-xs text-muted-foreground/70 mt-6">
        © 2025 MolluscAI · 仅供学术与个人参考使用
      </p>
    </div>
  </div>
</template>

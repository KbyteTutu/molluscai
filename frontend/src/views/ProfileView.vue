<script setup>
import { computed } from 'vue'
import { useRouter } from 'vue-router'
import { LogOut } from 'lucide-vue-next'
import { useAuthStore } from '@/stores/auth'
import Card from '@/components/ui/Card.vue'
import CardHeader from '@/components/ui/CardHeader.vue'
import CardTitle from '@/components/ui/CardTitle.vue'
import CardContent from '@/components/ui/CardContent.vue'
import Avatar from '@/components/ui/Avatar.vue'
import Badge from '@/components/ui/Badge.vue'
import Button from '@/components/ui/Button.vue'
import Separator from '@/components/ui/Separator.vue'
import { formatDate } from '@/lib/utils'
import { toast } from 'vue-sonner'

const authStore = useAuthStore()
const router = useRouter()

const roleLabel = {
  user: '普通用户',
  vip: 'VIP 会员',
  doc_admin: '文献管理员',
  superadmin: '超级管理员'
}
const roleVariant = {
  user: 'muted',
  vip: 'secondary',
  doc_admin: 'outline',
  superadmin: 'destructive'
}

const u = computed(() => authStore.currentUser || {})

function logout() {
  authStore.logout()
  toast.success('已退出登录')
  router.push('/login')
}
</script>

<template>
  <div class="max-w-2xl space-y-6">
    <header class="space-y-2">
      <h1 class="font-serif text-3xl font-semibold tracking-tight">个人中心</h1>
      <p class="text-sm text-muted-foreground">账户信息与偏好设置</p>
    </header>

    <Card>
      <CardHeader>
        <div class="flex items-center gap-4">
          <Avatar class="size-14 bg-primary/10 p-1.5">
            <img src="/logo.png" alt="logo" class="size-full object-contain" />
          </Avatar>
          <div class="flex-1">
            <CardTitle class="text-xl">{{ u.username || '—' }}</CardTitle>
            <p class="text-sm text-muted-foreground mt-1">{{ u.email || '—' }}</p>
          </div>
          <Badge :variant="roleVariant[u.role] || 'muted'">{{ roleLabel[u.role] || u.role }}</Badge>
        </div>
      </CardHeader>
      <CardContent>
        <Separator class="mb-5" />
        <dl class="grid grid-cols-1 sm:grid-cols-2 gap-x-8 gap-y-4 text-sm">
          <div>
            <dt class="text-[10px] uppercase tracking-widest text-muted-foreground mb-1">账户余额</dt>
            <dd class="font-mono tabular-nums">€ {{ Number(u.balance || 0).toFixed(2) }}</dd>
          </div>
          <div>
            <dt class="text-[10px] uppercase tracking-widest text-muted-foreground mb-1">每日检索配额</dt>
            <dd>{{ u.daily_query_limit ?? '按角色默认' }}</dd>
          </div>
          <div>
            <dt class="text-[10px] uppercase tracking-widest text-muted-foreground mb-1">注册时间</dt>
            <dd>{{ formatDate(u.created_at) }}</dd>
          </div>
          <div>
            <dt class="text-[10px] uppercase tracking-widest text-muted-foreground mb-1">账户状态</dt>
            <dd>{{ u.is_active ? '正常' : '已停用' }}</dd>
          </div>
        </dl>
      </CardContent>
    </Card>

    <div>
      <Button variant="destructive" @click="logout">
        <LogOut class="size-4" /> 退出登录
      </Button>
    </div>
  </div>
</template>

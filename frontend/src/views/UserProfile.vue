<template>
  <div class="user-profile-page">
    <el-card class="profile-card" shadow="hover">
      <div class="profile-header">
        <div class="avatar">
          <el-icon :size="48"><UserFilled /></el-icon>
        </div>
        <div class="profile-info">
          <h2>{{ authStore.currentUser?.username || '用户' }}</h2>
          <el-tag :type="roleTagType" size="small">
            {{ roleLabel }}
          </el-tag>
        </div>
      </div>

      <el-divider />

      <el-descriptions :column="1" border>
        <el-descriptions-item label="用户名">
          {{ authStore.currentUser?.username || '-' }}
        </el-descriptions-item>
        <el-descriptions-item label="邮箱">
          {{ authStore.currentUser?.email || '-' }}
        </el-descriptions-item>
        <el-descriptions-item label="角色">
          {{ roleLabel }}
        </el-descriptions-item>
        <el-descriptions-item label="注册时间">
          {{ authStore.currentUser?.created_at || '-' }}
        </el-descriptions-item>
      </el-descriptions>

      <div class="logout-section">
        <el-button type="danger" @click="handleLogout" :icon="SwitchButton">
          退出登录
        </el-button>
      </div>
    </el-card>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { UserFilled, SwitchButton } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'

const router = useRouter()
const authStore = useAuthStore()

const roleLabelMap = {
  user: '普通用户',
  vip: '会员',
  doc_admin: '文献管理员',
  superadmin: '超级管理员'
}

const roleTagTypeMap = {
  user: 'info',
  vip: 'warning',
  doc_admin: 'success',
  superadmin: 'danger'
}

const roleLabel = computed(() => {
  return roleLabelMap[authStore.currentUser?.role] || '普通用户'
})

const roleTagType = computed(() => {
  return roleTagTypeMap[authStore.currentUser?.role] || 'info'
})

async function handleLogout() {
  try {
    await ElMessageBox.confirm('确定要退出登录吗？', '提示', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning'
    })
    authStore.logout()
    ElMessage.success('已退出登录')
    router.push('/login')
  } catch {
    // user cancelled
  }
}
</script>

<style scoped>
.user-profile-page {
  max-width: 600px;
  margin: 0 auto;
}

.profile-card {
  border-radius: 8px;
}

.profile-header {
  display: flex;
  align-items: center;
  gap: 20px;
  padding: 8px 0;
}

.avatar {
  width: 64px;
  height: 64px;
  border-radius: 50%;
  background: #ecf5ff;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #409eff;
}

.profile-info h2 {
  margin: 0 0 8px 0;
  font-size: 20px;
  color: #303133;
}

.logout-section {
  margin-top: 24px;
  display: flex;
  justify-content: center;
}
</style>

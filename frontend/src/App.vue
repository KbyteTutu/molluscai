<template>
  <el-container class="layout-container">
    <el-header class="layout-header">
      <div class="header-left">
        <router-link to="/" class="logo-link">
          <h1 class="logo">MalacoAgent</h1>
        </router-link>
        <span class="subtitle">智能贝壳知识平台</span>
      </div>
      <div class="header-right" v-if="authStore.isAuthenticated">
        <el-dropdown @command="handleCommand">
          <span class="user-info">
            <el-icon><User /></el-icon>
            {{ authStore.currentUser?.username }}
            <el-icon class="arrow"><ArrowDown /></el-icon>
          </span>
          <template #dropdown>
            <el-dropdown-menu>
              <el-dropdown-item command="profile">
                <el-icon><User /></el-icon>个人中心
              </el-dropdown-item>
              <el-dropdown-item command="logout" divided>
                <el-icon><SwitchButton /></el-icon>退出登录
              </el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>
      </div>
    </el-header>

    <el-main class="layout-main">
      <router-view />
    </el-main>

    <el-footer class="layout-footer">
      <span>MalacoAgent &copy; 2025 - 智能贝壳知识平台</span>
    </el-footer>
  </el-container>
</template>

<script setup>
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { User, ArrowDown, SwitchButton } from '@element-plus/icons-vue'

const router = useRouter()
const authStore = useAuthStore()

function handleCommand(command) {
  if (command === 'profile') {
    router.push('/me')
  } else if (command === 'logout') {
    authStore.logout()
    router.push('/login')
  }
}
</script>

<style scoped>
.layout-container {
  min-height: 100vh;
}

.layout-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  background: #1a3a5c;
  color: #ffffff;
  padding: 0 24px;
  height: 60px;
}

.header-left {
  display: flex;
  align-items: baseline;
  gap: 12px;
}

.logo-link {
  text-decoration: none;
  color: inherit;
}

.logo {
  margin: 0;
  font-size: 20px;
  font-weight: 700;
  color: #ffffff;
}

.subtitle {
  font-size: 13px;
  color: #a8c4e0;
}

.header-right {
  display: flex;
  align-items: center;
}

.user-info {
  display: flex;
  align-items: center;
  gap: 6px;
  cursor: pointer;
  color: #ffffff;
  font-size: 14px;
  padding: 4px 8px;
  border-radius: 4px;
  transition: background 0.2s;
}

.user-info:hover {
  background: rgba(255, 255, 255, 0.15);
}

.arrow {
  font-size: 12px;
  margin-left: 2px;
}

.layout-main {
  background: #f5f7fa;
  min-height: calc(100vh - 100px);
  padding: 20px;
}

.layout-footer {
  display: flex;
  justify-content: center;
  align-items: center;
  height: 40px;
  font-size: 12px;
  color: #909399;
  border-top: 1px solid #ebeef5;
  background: #ffffff;
}
</style>

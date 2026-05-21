import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const routes = [
  {
    path: '/login',
    name: 'Login',
    component: () => import('@/views/LoginView.vue'),
    meta: { requiresGuest: true }
  },
  {
    path: '/',
    name: 'Home',
    component: () => import('@/views/HomeView.vue'),
    meta: { requiresAuth: false }
  },
  {
    path: '/auctions/:itemNo',
    name: 'AuctionDetail',
    component: () => import('@/views/AuctionDetailView.vue'),
    meta: { requiresAuth: true }
  },
  {
    path: '/taxa',
    name: 'Taxa',
    component: () => import('@/views/TaxaSearchView.vue'),
    meta: { requiresAuth: true }
  },
  {
    path: '/taxa/:aphiaId',
    name: 'TaxonDetail',
    component: () => import('@/views/TaxonDetailView.vue'),
    meta: { requiresAuth: true }
  },
  {
    path: '/compare',
    name: 'Compare',
    component: () => import('@/views/CompareView.vue'),
    meta: { requiresAuth: true }
  },
  {
    path: '/me',
    name: 'Profile',
    component: () => import('@/views/ProfileView.vue'),
    meta: { requiresAuth: true }
  },
  {
    path: '/admin/scraper',
    name: 'AdminScraper',
    component: () => import('@/views/AdminScraperView.vue'),
    meta: { requiresAuth: true, requiresSuperadmin: true }
  },
  {
    path: '/admin/models',
    name: 'AdminModels',
    component: () => import('@/views/AdminModelsView.vue'),
    meta: { requiresAuth: true, requiresSuperadmin: true }
  },
  {
    path: '/admin/embeddings',
    name: 'AdminEmbeddings',
    component: () => import('@/views/AdminEmbeddingsView.vue'),
    meta: { requiresAuth: true, requiresSuperadmin: true }
  },
  {
    path: '/admin/tasks',
    name: 'AdminTasks',
    component: () => import('@/views/AdminTasksView.vue'),
    meta: { requiresAuth: true, requiresSuperadmin: true }
  },
  {
    path: '/admin/usage',
    name: 'AdminUsage',
    component: () => import('@/views/AdminUsageView.vue'),
    meta: { requiresAuth: true, requiresSuperadmin: true }
  },
  {
    path: '/admin/quotas',
    name: 'AdminQuotas',
    component: () => import('@/views/AdminQuotasView.vue'),
    meta: { requiresAuth: true, requiresSuperadmin: true }
  },
  {
    path: '/admin/queries',
    name: 'AdminQueries',
    component: () => import('@/views/AdminQueriesView.vue'),
    meta: { requiresAuth: true, requiresSuperadmin: true }
  }
]

const router = createRouter({ history: createWebHistory(), routes })

router.beforeEach((to, from, next) => {
  const authStore = useAuthStore()
  if (to.meta.requiresAuth && !authStore.isAuthenticated) {
    next({ name: 'Login', query: { redirect: to.fullPath } })
  } else if (to.meta.requiresGuest && authStore.isAuthenticated) {
    next({ name: 'Home' })
  } else if (to.meta.requiresSuperadmin && authStore.currentUser?.role !== 'superadmin') {
    next({ name: 'Home' })
  } else {
    next()
  }
})

export default router

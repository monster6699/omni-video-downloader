import { createRouter, createWebHistory } from 'vue-router'
import Home from './pages/Home.vue'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', name: 'home', component: Home },
    {
      path: '/history',
      name: 'history',
      component: () => import('./pages/HistoryPage.vue'),
    },
    {
      path: '/admin',
      name: 'admin',
      component: () => import('./pages/AdminPage.vue'),
    },
    {
      path: '/pricing',
      name: 'pricing',
      component: () => import('./pages/PricingPage.vue'),
    },
    {
      path: '/guide',
      name: 'guide',
      component: () => import('./pages/GuidePage.vue'),
    },
  ],
})

export default router

import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '../stores/auth'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/login',
      name: 'Login',
      component: () => import('../views/LoginView.vue'),
      meta: { public: true },
    },
    {
      path: '/',
      name: 'Dashboard',
      component: () => import('../views/DashboardView.vue'),
    },
    {
      path: '/guests',
      name: 'Guests',
      component: () => import('../views/GuestsView.vue'),
    },
    {
      path: '/rooms',
      name: 'Rooms',
      component: () => import('../views/RoomsView.vue'),
    },
    {
      path: '/reservations',
      name: 'Reservations',
      component: () => import('../views/ReservationsView.vue'),
    },
    {
      path: '/checkin',
      name: 'CheckIn',
      component: () => import('../views/CheckInView.vue'),
    },
    {
      path: '/breakfast',
      name: 'Breakfast',
      component: () => import('../views/BreakfastView.vue'),
    },
    {
      path: '/users',
      name: 'Users',
      component: () => import('../views/UsersView.vue'),
      meta: { adminOnly: true },
    },
    {
      path: '/cleaning',
      name: 'Cleaning',
      component: () => import('../views/CleaningView.vue'),
    },
    {
      path: '/api-keys',
      name: 'ApiKeys',
      meta: { adminOnly: true },
      component: () => import('../views/ApiKeysView.vue'),
    },
    {
      path: '/self-checkin',
      name: 'SelfCheckIn',
      component: () => import('../views/SelfCheckInView.vue'),
      meta: { public: true },
    },
  ],
})

router.beforeEach(async (to) => {
  const auth = useAuthStore()
  if (!auth.isLoggedIn && !to.meta.public) {
    return '/login'
  }
  if (to.meta.adminOnly && !auth.isAdmin) {
    return '/'
  }
})

export default router

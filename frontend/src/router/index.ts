import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '../stores/auth'

type RouteMeta = {
  public?: boolean
  adminOnly?: boolean
  roles?: Array<'admin' | 'staff' | 'cleaner' | 'readonly'>
}

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/login', name: 'Login', component: () => import('../views/LoginView.vue'), meta: { public: true } as RouteMeta },
    { path: '/', name: 'Dashboard', component: () => import('../views/DashboardView.vue'), meta: { roles: ['admin', 'staff', 'readonly'] } as RouteMeta },
    { path: '/guests', name: 'Guests', component: () => import('../views/GuestsView.vue'), meta: { roles: ['admin', 'staff', 'readonly'] } as RouteMeta },
    { path: '/rooms', name: 'Rooms', component: () => import('../views/RoomsView.vue'), meta: { roles: ['admin', 'staff', 'readonly'] } as RouteMeta },
    { path: '/reservations', name: 'Reservations', component: () => import('../views/ReservationsView.vue'), meta: { roles: ['admin', 'staff', 'readonly'] } as RouteMeta },
    { path: '/checkin', name: 'CheckIn', component: () => import('../views/CheckInView.vue'), meta: { roles: ['admin', 'staff'] } as RouteMeta },
    { path: '/breakfast', name: 'Breakfast', component: () => import('../views/BreakfastView.vue'), meta: { roles: ['admin', 'staff'] } as RouteMeta },
    { path: '/users', name: 'Users', component: () => import('../views/UsersView.vue'), meta: { adminOnly: true } as RouteMeta },
    { path: '/housekeeping', name: 'Housekeeping', component: () => import('../views/HousekeepingView.vue'), meta: { roles: ['admin', 'staff', 'cleaner'] } as RouteMeta },
    { path: '/cleaning', redirect: '/housekeeping' },
    { path: '/api-keys', name: 'ApiKeys', component: () => import('../views/ApiKeysView.vue'), meta: { adminOnly: true } as RouteMeta },
    { path: '/self-checkin', name: 'SelfCheckIn', component: () => import('../views/SelfCheckInView.vue'), meta: { public: true } as RouteMeta },
  ],
})

router.beforeEach(async (to) => {
  const auth = useAuthStore()
  const meta = to.meta as RouteMeta
  if (!auth.isLoggedIn && !meta.public) {
    return '/login'
  }
  if (meta.adminOnly && !auth.isAdmin) {
    return auth.homeRoute
  }
  if (meta.roles && auth.user && !meta.roles.includes(auth.user.role)) {
    return auth.homeRoute
  }
})

export default router

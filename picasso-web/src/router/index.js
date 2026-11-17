import { createRouter, createWebHistory } from 'vue-router'

import { LOGIN_ROUTE, useAuthStore } from '@/stores/auth.store.js'

const routes = [
  { path: LOGIN_ROUTE, name: 'login', component: () => import('@/views/LoginView.vue'), meta: { public: true, title: 'Entrar' } },
  { path: '/', name: 'inicio', component: () => import('@/views/InicioView.vue'), meta: { title: 'Inicio' } },
  {
    path: '/revision/:id',
    name: 'revision',
    component: () => import('@/views/RevisionView.vue'),
    meta: { title: 'Revisión', inmersiva: true },
  },
  { path: '/folios', name: 'folios', component: () => import('@/views/FoliosView.vue'), meta: { title: 'Folios' } },
  { path: '/folios/:id', name: 'folio', component: () => import('@/views/FolioView.vue'), meta: { title: 'Folio' } },
  { path: '/habitacion/:id', name: 'habitacion', component: () => import('@/views/HabitacionView.vue'), meta: { title: 'Habitación' } },
  { path: '/reportes', name: 'reportes', component: () => import('@/views/ReportesView.vue'), meta: { title: 'Reportes' } },
  { path: '/perfil', name: 'perfil', component: () => import('@/views/PerfilView.vue'), meta: { title: 'Perfil' } },
  { path: '/admin', name: 'admin', component: () => import('@/views/AdminView.vue'), meta: { title: 'Ajustes' } },
  { path: '/:pathMatch(.*)*', redirect: '/' },
]

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes,
  scrollBehavior: (to, from, guardado) => guardado ?? { top: 0 },
})

// Todo es privado salvo la entrada.
router.beforeEach((to) => {
  if (to.meta?.public || useAuthStore().isAuthenticated) return true
  return { name: 'login', query: { next: to.fullPath } }
})

router.afterEach((to) => {
  document.title = to.meta?.title ? `${to.meta.title} · Picasso` : 'Picasso'
})

export default router

import { createRouter, createWebHistory } from 'vue-router'


export const routes = [
  {
    path: '/',
    name: 'Workspace',
    component: () => import('../views/WorkspaceView.vue'),
  },
  {
    path: '/photo',
    name: 'PhotoStudio',
    component: () => import('../views/PhotoStudio.vue'),
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
  scrollBehavior: () => ({ top: 0 }),
})

export default router

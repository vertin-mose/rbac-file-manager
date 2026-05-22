import { createRouter, createWebHistory, type RouteRecordRaw } from 'vue-router'

const routes: RouteRecordRaw[] = [
    {
        path: '/login',
        name: 'Login',
        component: () => import('@/views/login/LoginView.vue'),
        meta: { requiresAuth: false },
    },
    {
        path: '/',
        component: () => import('@/components/AppLayout.vue'),
        meta: { requiresAuth: true },
        redirect: '/dashboard',
        children: [
            {
                path: 'dashboard',
                name: 'Dashboard',
                component: () => import('@/views/dashboard/DashboardView.vue'),
            },
            {
                path: 'files',
                name: 'FileManager',
                component: () => import('@/views/file/FileManager.vue'),
            },
            {
                path: 'roles',
                name: 'RoleManagement',
                component: () => import('@/views/role/RoleManagement.vue'),
                meta: { roles: ['ADMIN', 'SUPER_ADMIN'] },
            },
            {
                path: 'audit',
                name: 'AuditLog',
                component: () => import('@/views/audit/AuditLogView.vue'),
                meta: { roles: ['MANAGER', 'ADMIN', 'SUPER_ADMIN'] },
            },
            {
                path: 'system-config',
                name: 'SystemConfig',
                component: () => import('@/views/system/SystemConfigView.vue'),
                meta: { roles: ['SUPER_ADMIN'] },
            },
        ],
    },
]

const router = createRouter({
    history: createWebHistory(),
    routes,
})

// Navigation guard: check authentication
router.beforeEach((to, _from, next) => {
    const token = localStorage.getItem('token')
    if (to.meta.requiresAuth && !token) {
        next('/login')
    } else if (to.path === '/login' && token) {
        next('/dashboard')
    } else {
        next()
    }
})

export default router

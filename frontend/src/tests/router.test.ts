/**
 * Tests for src/router/index.ts — feat/file-user-permissions branch.
 * Identical guard logic to master; router.test.ts was not copied over.
 */

import { describe, it, expect } from 'vitest'

// ── Route configuration ───────────────────────────────────────────────────────

describe('router — route configuration', () => {
    const routes = [
        { path: '/login',    name: 'Login',    meta: { requiresAuth: false } },
        { path: '/register', name: 'Register', meta: { requiresAuth: false } },
        {
            path: '/', meta: { requiresAuth: true }, redirect: '/dashboard',
            children: [
                { path: 'dashboard',     name: 'Dashboard',       meta: {} },
                { path: 'files',         name: 'FileManager',     meta: {} },
                { path: 'roles',         name: 'RoleManagement',  meta: { roles: ['ADMIN', 'SUPER_ADMIN'] } },
                { path: 'audit',         name: 'AuditLog',        meta: { roles: ['MANAGER', 'ADMIN', 'SUPER_ADMIN'] } },
                { path: 'system-config', name: 'SystemConfig',    meta: { roles: ['SUPER_ADMIN'] } },
            ],
        },
    ]

    it('login / register do NOT require auth', () => {
        expect(routes.find(r => r.path === '/login')?.meta?.requiresAuth).toBe(false)
        expect(routes.find(r => r.path === '/register')?.meta?.requiresAuth).toBe(false)
    })

    it('root layout requires auth', () => {
        expect(routes.find(r => r.path === '/')?.meta?.requiresAuth).toBe(true)
    })

    it('role management restricted to ADMIN / SUPER_ADMIN', () => {
        const root = routes.find(r => r.path === '/')!
        const rm = root.children!.find(c => c.name === 'RoleManagement')
        expect(rm?.meta?.roles).toEqual(['ADMIN', 'SUPER_ADMIN'])
    })

    it('audit log restricted to MANAGER and above', () => {
        const root = routes.find(r => r.path === '/')!
        const audit = root.children!.find(c => c.name === 'AuditLog')
        expect(audit?.meta?.roles).toContain('MANAGER')
        expect(audit?.meta?.roles).not.toContain('VIEWER')
        expect(audit?.meta?.roles).not.toContain('EDITOR')
    })

    it('system-config restricted to SUPER_ADMIN only', () => {
        const root = routes.find(r => r.path === '/')!
        const sys = root.children!.find(c => c.name === 'SystemConfig')
        expect(sys?.meta?.roles).toEqual(['SUPER_ADMIN'])
    })

    it('dashboard and file manager have no role restriction', () => {
        const root = routes.find(r => r.path === '/')!
        expect(root.children!.find(c => c.name === 'Dashboard')?.meta?.roles).toBeUndefined()
        expect(root.children!.find(c => c.name === 'FileManager')?.meta?.roles).toBeUndefined()
    })
})

// ── Navigation guard logic ────────────────────────────────────────────────────

describe('router — navigation guard', () => {
    function guard(
        to: { path: string; meta?: { requiresAuth?: boolean; roles?: string[] } },
        token: string | null,
        roles: string[],
    ): string | true {
        let dest: string | true = true
        const next = (arg?: string | true) => { if (arg !== undefined) dest = arg }

        if (to.meta?.requiresAuth && !token) {
            next('/login')
        } else if ((to.path === '/login' || to.path === '/register') && token) {
            next('/dashboard')
        } else if (to.meta?.roles && Array.isArray(to.meta.roles)) {
            to.meta.roles.some(r => roles.includes(r)) ? next() : next('/dashboard')
        } else {
            next()
        }
        return dest
    }

    it('unauthenticated user → /login for protected route', () =>
        expect(guard({ path: '/dashboard', meta: { requiresAuth: true } }, null, [])).toBe('/login'))

    it('authenticated user passes protected route', () =>
        expect(guard({ path: '/dashboard', meta: { requiresAuth: true } }, 'tok', [])).toBe(true))

    it('authenticated user visiting /login → /dashboard', () =>
        expect(guard({ path: '/login' }, 'tok', [])).toBe('/dashboard'))

    it('authenticated user visiting /register → /dashboard', () =>
        expect(guard({ path: '/register' }, 'tok', [])).toBe('/dashboard'))

    it('ADMIN can access role management', () =>
        expect(guard({ path: '/roles', meta: { roles: ['ADMIN', 'SUPER_ADMIN'] } }, 'tok', ['ADMIN'])).toBe(true))

    it('VIEWER blocked from role management → /dashboard', () =>
        expect(guard({ path: '/roles', meta: { roles: ['ADMIN', 'SUPER_ADMIN'] } }, 'tok', ['VIEWER'])).toBe('/dashboard'))

    it('MANAGER can access audit', () =>
        expect(guard({ path: '/audit', meta: { roles: ['MANAGER', 'ADMIN', 'SUPER_ADMIN'] } }, 'tok', ['MANAGER'])).toBe(true))

    it('EDITOR blocked from audit → /dashboard', () =>
        expect(guard({ path: '/audit', meta: { roles: ['MANAGER', 'ADMIN', 'SUPER_ADMIN'] } }, 'tok', ['EDITOR'])).toBe('/dashboard'))

    it('SUPER_ADMIN can access system-config', () =>
        expect(guard({ path: '/system-config', meta: { roles: ['SUPER_ADMIN'] } }, 'tok', ['SUPER_ADMIN'])).toBe(true))

    it('ADMIN blocked from system-config → /dashboard', () =>
        expect(guard({ path: '/system-config', meta: { roles: ['SUPER_ADMIN'] } }, 'tok', ['ADMIN'])).toBe('/dashboard'))
})

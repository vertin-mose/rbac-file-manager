/**
 * Tests for src/store/user.ts — Pinia user store.
 * Covers: login state hydration, hasRole, hasPermission,
 * highestLevel, roleDisplayName, logout cleanup.
 */

import { describe, it, expect, beforeEach, vi } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { useUserStore } from '@/store/user'

// Mock the api/auth module so we don't make real HTTP calls
vi.mock('@/api/auth', () => ({
    login: vi.fn(),
}))

import { login as apiLogin } from '@/api/auth'

// ── Helpers ───────────────────────────────────────────────────────────────────

function makeLoginResponse(overrides = {}) {
    return {
        data: {
            token: 'jwt.token.here',
            user_id: 42,
            username: 'alice',
            display_name: 'Alice Smith',
            roles: ['EDITOR'],
            role_info: [{ name: 'EDITOR', display_name: '文档编辑员', level: 4 }],
            permissions: ['doc:create', 'doc:read', 'doc:update'],
            ...overrides,
        },
    }
}

// ── Setup ─────────────────────────────────────────────────────────────────────

beforeEach(() => {
    setActivePinia(createPinia())
    localStorage.clear()
    vi.clearAllMocks()
})

// ── Initial state ─────────────────────────────────────────────────────────────

describe('userStore — initial state', () => {
    it('is unauthenticated by default', () => {
        const store = useUserStore()
        expect(store.token).toBe('')
        expect(store.username).toBe('')
        expect(store.roles).toEqual([])
        expect(store.permissions).toEqual([])
    })

    it('reads persisted state from localStorage', () => {
        localStorage.setItem('token', 'existing.token')
        localStorage.setItem('username', 'bob')
        localStorage.setItem('roles', JSON.stringify(['VIEWER']))
        localStorage.setItem('permissions', JSON.stringify(['doc:read']))
        localStorage.setItem('roleInfo', JSON.stringify([{ name: 'VIEWER', display_name: '访客', level: 5 }]))
        const store = useUserStore()
        expect(store.token).toBe('existing.token')
        expect(store.username).toBe('bob')
        expect(store.roles).toEqual(['VIEWER'])
        expect(store.permissions).toContain('doc:read')
    })
})

// ── login ─────────────────────────────────────────────────────────────────────

describe('userStore — login()', () => {
    it('populates all state fields after login', async () => {
        vi.mocked(apiLogin).mockResolvedValue(makeLoginResponse() as any)
        const store = useUserStore()
        await store.login({ username: 'alice', password: 'pass' })
        expect(store.token).toBe('jwt.token.here')
        expect(store.userId).toBe(42)
        expect(store.username).toBe('alice')
        expect(store.displayName).toBe('Alice Smith')
        expect(store.roles).toEqual(['EDITOR'])
        expect(store.permissions).toContain('doc:create')
    })

    it('persists token and roles to localStorage', async () => {
        vi.mocked(apiLogin).mockResolvedValue(makeLoginResponse() as any)
        const store = useUserStore()
        await store.login({ username: 'alice', password: 'pass' })
        expect(localStorage.getItem('token')).toBe('jwt.token.here')
        expect(JSON.parse(localStorage.getItem('roles') || '[]')).toContain('EDITOR')
    })

    it('stores role_info correctly', async () => {
        vi.mocked(apiLogin).mockResolvedValue(makeLoginResponse() as any)
        const store = useUserStore()
        await store.login({ username: 'alice', password: 'pass' })
        expect(store.roleInfo[0].name).toBe('EDITOR')
        expect(store.roleInfo[0].level).toBe(4)
    })

    it('handles missing display_name gracefully', async () => {
        vi.mocked(apiLogin).mockResolvedValue(
            makeLoginResponse({ display_name: null }) as any
        )
        const store = useUserStore()
        await store.login({ username: 'alice', password: 'pass' })
        expect(store.displayName).toBe('')
    })
})

// ── logout ────────────────────────────────────────────────────────────────────

describe('userStore — logout()', () => {
    it('clears all state', async () => {
        vi.mocked(apiLogin).mockResolvedValue(makeLoginResponse() as any)
        const store = useUserStore()
        await store.login({ username: 'alice', password: 'pass' })
        store.logout()
        expect(store.token).toBe('')
        expect(store.userId).toBe(0)
        expect(store.username).toBe('')
        expect(store.roles).toEqual([])
        expect(store.permissions).toEqual([])
        expect(store.roleInfo).toEqual([])
    })

    it('removes all localStorage keys', async () => {
        vi.mocked(apiLogin).mockResolvedValue(makeLoginResponse() as any)
        const store = useUserStore()
        await store.login({ username: 'alice', password: 'pass' })
        store.logout()
        expect(localStorage.getItem('token')).toBeNull()
        expect(localStorage.getItem('roles')).toBeNull()
        expect(localStorage.getItem('permissions')).toBeNull()
    })
})

// ── hasRole ───────────────────────────────────────────────────────────────────

describe('userStore — hasRole()', () => {
    it('returns true for assigned role', async () => {
        vi.mocked(apiLogin).mockResolvedValue(makeLoginResponse({ roles: ['MANAGER'] }) as any)
        const store = useUserStore()
        await store.login({ username: 'x', password: 'y' })
        expect(store.hasRole('MANAGER')).toBe(true)
    })

    it('returns false for unassigned role', async () => {
        vi.mocked(apiLogin).mockResolvedValue(makeLoginResponse() as any)
        const store = useUserStore()
        await store.login({ username: 'x', password: 'y' })
        expect(store.hasRole('SUPER_ADMIN')).toBe(false)
    })

    it('is case-sensitive', async () => {
        vi.mocked(apiLogin).mockResolvedValue(makeLoginResponse({ roles: ['VIEWER'] }) as any)
        const store = useUserStore()
        await store.login({ username: 'x', password: 'y' })
        expect(store.hasRole('viewer')).toBe(false)
    })
})

// ── hasPermission ─────────────────────────────────────────────────────────────

describe('userStore — hasPermission()', () => {
    it('returns true for a held permission', async () => {
        vi.mocked(apiLogin).mockResolvedValue(
            makeLoginResponse({ permissions: ['doc:read', 'doc:create'] }) as any
        )
        const store = useUserStore()
        await store.login({ username: 'x', password: 'y' })
        expect(store.hasPermission('doc:read')).toBe(true)
        expect(store.hasPermission('doc:create')).toBe(true)
    })

    it('returns false for a missing permission', async () => {
        vi.mocked(apiLogin).mockResolvedValue(makeLoginResponse() as any)
        const store = useUserStore()
        await store.login({ username: 'x', password: 'y' })
        expect(store.hasPermission('system:config')).toBe(false)
    })

    it('file:permission:manage is present only for admin roles', async () => {
        vi.mocked(apiLogin).mockResolvedValue(
            makeLoginResponse({
                roles: ['ADMIN'],
                permissions: ['file:permission:manage', 'role:create'],
            }) as any
        )
        const store = useUserStore()
        await store.login({ username: 'x', password: 'y' })
        expect(store.hasPermission('file:permission:manage')).toBe(true)
    })
})

// ── highestLevel (computed) ───────────────────────────────────────────────────

describe('userStore — highestLevel (computed)', () => {
    it('returns 99 when no roles', () => {
        const store = useUserStore()
        expect(store.highestLevel).toBe(99)
    })

    it('returns level 1 for SUPER_ADMIN', async () => {
        vi.mocked(apiLogin).mockResolvedValue(
            makeLoginResponse({
                roles: ['SUPER_ADMIN'],
                role_info: [{ name: 'SUPER_ADMIN', display_name: '超级管理员', level: 1 }],
            }) as any
        )
        const store = useUserStore()
        await store.login({ username: 'x', password: 'y' })
        expect(store.highestLevel).toBe(1)
    })

    it('returns minimum level when user has multiple roles', async () => {
        vi.mocked(apiLogin).mockResolvedValue(
            makeLoginResponse({
                roles: ['EDITOR', 'VIEWER'],
                role_info: [
                    { name: 'EDITOR', display_name: '编辑', level: 4 },
                    { name: 'VIEWER', display_name: '访客', level: 5 },
                ],
            }) as any
        )
        const store = useUserStore()
        await store.login({ username: 'x', password: 'y' })
        expect(store.highestLevel).toBe(4)
    })
})

// ── roleDisplayName (computed) ────────────────────────────────────────────────

describe('userStore — roleDisplayName (computed)', () => {
    it('returns empty string when no role info', () => {
        const store = useUserStore()
        expect(store.roleDisplayName).toBe('')
    })

    it('returns display name of highest-level role', async () => {
        vi.mocked(apiLogin).mockResolvedValue(
            makeLoginResponse({
                role_info: [
                    { name: 'EDITOR', display_name: '文档编辑员', level: 4 },
                    { name: 'MANAGER', display_name: '部门经理', level: 3 },
                ],
            }) as any
        )
        const store = useUserStore()
        await store.login({ username: 'x', password: 'y' })
        // MANAGER has lower level number (more senior), so its display name is returned
        expect(store.roleDisplayName).toBe('部门经理')
    })
})

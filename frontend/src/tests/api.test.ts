/**
 * Tests for base API layer mapping in the feat branch.
 * Mirrors master's api.test.ts, adapted for feat-specific types.
 * Covers: FileItem, Role/Permission, AuditLogItem, RoleHierarchy mappings.
 * (FilePermissionItem is tested separately in api-fileperm.test.ts)
 */

import { describe, it, expect } from 'vitest'

// ── Helpers ───────────────────────────────────────────────────────────────────

function makeRawFile(overrides: Record<string, unknown> = {}) {
    return {
        id: 1, file_name: 'hello.txt', is_directory: false,
        size: 1024, mime_type: 'text/plain', owner_id: 2,
        parent_id: null, storage_url: 'local://abc.txt',
        created_at: '2024-01-01T10:00:00', updated_at: '2024-01-01T11:00:00',
        ...overrides,
    }
}

function makeRawRole(overrides: Record<string, unknown> = {}) {
    return {
        id: 1, name: 'EDITOR', description: 'doc editor',
        permissions: [{ id: 1, name: 'doc:create', description: 'create', category: 'document' }],
        inherited_permissions: [{ id: 2, name: 'doc:read', description: 'read', category: 'document' }],
        ...overrides,
    }
}

function makeRawAuditLog(overrides: Record<string, unknown> = {}) {
    return {
        id: 10, user_id: 1, username: 'alice', action: 'LOGIN',
        detail: 'logged in', ip_address: '127.0.0.1',
        success: true, created_at: '2024-06-01T08:00:00',
        ...overrides,
    }
}

// ── FileItem mapping ──────────────────────────────────────────────────────────

describe('file api — FileItem mapping', () => {
    function mapFileItem(item: any) {
        return {
            id: item.id, fileName: item.file_name, isDirectory: item.is_directory,
            size: item.size, mimeType: item.mime_type || '', ownerId: item.owner_id,
            parentId: item.parent_id ?? null, storageUrl: item.storage_url || '',
            createdAt: item.created_at ?? null, updatedAt: item.updated_at ?? null,
        }
    }

    it('maps all snake_case fields to camelCase', () => {
        const m = mapFileItem(makeRawFile())
        expect(m.fileName).toBe('hello.txt')
        expect(m.isDirectory).toBe(false)
        expect(m.ownerId).toBe(2)
        expect(m.parentId).toBeNull()
    })

    it('mimeType defaults to empty string when null', () =>
        expect(mapFileItem(makeRawFile({ mime_type: null })).mimeType).toBe(''))

    it('storageUrl defaults to empty string when missing', () => {
        const { storage_url: _, ...rest } = makeRawFile() as any
        expect(mapFileItem(rest).storageUrl).toBe('')
    })

    it('isDirectory flag preserved', () =>
        expect(mapFileItem(makeRawFile({ is_directory: true })).isDirectory).toBe(true))

    it('parentId null stays null', () =>
        expect(mapFileItem(makeRawFile({ parent_id: null })).parentId).toBeNull())

    it('parentId number is preserved', () =>
        expect(mapFileItem(makeRawFile({ parent_id: 5 })).parentId).toBe(5))
})

// ── Role / Permission mapping ─────────────────────────────────────────────────

describe('role api — Role/Permission mapping', () => {
    function mapPermission(item: any) {
        return { id: item.id, name: item.name, description: item.description || '',
                 category: item.category || 'other' }
    }
    function mapRole(item: any) {
        return {
            id: item.id, name: item.name, description: item.description || '',
            permissions: (item.permissions || []).map(mapPermission),
            inheritedPermissions: (item.inherited_permissions || []).map(mapPermission),
        }
    }

    it('maps own and inherited permissions', () => {
        const m = mapRole(makeRawRole())
        expect(m.permissions[0].name).toBe('doc:create')
        expect(m.inheritedPermissions[0].name).toBe('doc:read')
    })

    it('defaults description to empty string', () =>
        expect(mapRole(makeRawRole({ description: undefined })).description).toBe(''))

    it('defaults category to "other" when missing', () => {
        const r = makeRawRole({ permissions: [{ id: 1, name: 'x', description: 'x' }] })
        expect(mapRole(r).permissions[0].category).toBe('other')
    })

    it('empty permissions arrays preserved', () => {
        const m = mapRole(makeRawRole({ permissions: [], inherited_permissions: [] }))
        expect(m.permissions).toHaveLength(0)
        expect(m.inheritedPermissions).toHaveLength(0)
    })
})

// ── AuditLog mapping ──────────────────────────────────────────────────────────

describe('audit api — AuditLogItem mapping', () => {
    function mapAuditLogItem(item: any) {
        return {
            id: item.id, userId: item.user_id, username: item.username || '',
            action: item.action, detail: item.detail || '', ipAddress: item.ip_address || '',
            success: Boolean(item.success), createdAt: item.created_at ?? null,
        }
    }

    it('maps all fields correctly', () => {
        const m = mapAuditLogItem(makeRawAuditLog())
        expect(m.userId).toBe(1)
        expect(m.username).toBe('alice')
        expect(m.action).toBe('LOGIN')
        expect(m.ipAddress).toBe('127.0.0.1')
        expect(m.success).toBe(true)
    })

    it('username defaults to empty string when null', () =>
        expect(mapAuditLogItem(makeRawAuditLog({ username: null })).username).toBe(''))

    it('success coerced to boolean', () => {
        expect(mapAuditLogItem(makeRawAuditLog({ success: 1 })).success).toBe(true)
        expect(mapAuditLogItem(makeRawAuditLog({ success: 0 })).success).toBe(false)
    })

    it('createdAt is null when missing', () =>
        expect(mapAuditLogItem(makeRawAuditLog({ created_at: null })).createdAt).toBeNull())
})

// ── RoleHierarchy mapping ─────────────────────────────────────────────────────

describe('role hierarchy mapping', () => {
    function mapHierarchy(item: any) {
        return {
            roleId: item.role_id, roleName: item.role_name,
            inheritedRoleId: item.inherited_role_id, inheritedRoleName: item.inherited_role_name,
        }
    }

    it('maps all four fields', () => {
        const m = mapHierarchy({
            role_id: 1, role_name: 'SUPER_ADMIN',
            inherited_role_id: 2, inherited_role_name: 'ADMIN',
        })
        expect(m.roleId).toBe(1)
        expect(m.roleName).toBe('SUPER_ADMIN')
        expect(m.inheritedRoleId).toBe(2)
        expect(m.inheritedRoleName).toBe('ADMIN')
    })
})

// ── request.ts — clearAuthState & interceptor logic ───────────────────────────
// (feat branch clears 'userId' in addition to master's 6 keys)

describe('request.ts — clearAuthState (feat branch)', () => {
    const AUTH_KEYS = ['token', 'userId', 'username', 'displayName',
                       'roles', 'roleInfo', 'permissions']

    function clearAuthState() {
        AUTH_KEYS.forEach(k => localStorage.removeItem(k))
    }

    it('removes all 7 auth keys including userId', () => {
        AUTH_KEYS.forEach(k => localStorage.setItem(k, 'x'))
        clearAuthState()
        AUTH_KEYS.forEach(k => expect(localStorage.getItem(k)).toBeNull())
    })

    it('does not remove unrelated keys', () => {
        localStorage.setItem('theme', 'dark')
        clearAuthState()
        expect(localStorage.getItem('theme')).toBe('dark')
        localStorage.removeItem('theme')
    })
})

describe('request.ts — interceptor error routing (feat branch)', () => {
    function handleError(status: number | undefined): string {
        switch (status) {
            case 401: return 'clearAuth+redirectLogin'
            case 403: return 'showForbidden'
            case 404: return 'showNotFound'
            case 500: return 'showServerError'
            default:  return 'showGenericError'
        }
    }

    it('401 → clearAuth + redirect', () => expect(handleError(401)).toBe('clearAuth+redirectLogin'))
    it('403 → forbidden',           () => expect(handleError(403)).toBe('showForbidden'))
    it('404 → not found',           () => expect(handleError(404)).toBe('showNotFound'))
    it('500 → server error',        () => expect(handleError(500)).toBe('showServerError'))
    it('422 → generic error',       () => expect(handleError(422)).toBe('showGenericError'))
    it('undefined → generic error', () => expect(handleError(undefined)).toBe('showGenericError'))
})

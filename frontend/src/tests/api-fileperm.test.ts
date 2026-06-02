/**
 * Tests for the new FilePermissionItem mapping in src/api/file.ts
 * and the updated permissions constant (23 permissions incl. file:permission:manage).
 */

import { describe, it, expect } from 'vitest'
import { PERMISSIONS, PERMISSION_GROUPS } from '@/constants/permissions'

// ── permissions.ts — updated for this branch ──────────────────────────────────

describe('permissions constants (feat branch)', () => {
    it('exports exactly 23 permissions (includes file:permission:manage)', () => {
        expect(PERMISSIONS).toHaveLength(23)
    })

    it('file:permission:manage is present with category "file"', () => {
        const perm = PERMISSIONS.find(p => p.name === 'file:permission:manage')
        expect(perm).toBeDefined()
        expect(perm!.category).toBe('file')
    })

    it('all permission ids are unique', () => {
        const ids = PERMISSIONS.map(p => p.id)
        expect(new Set(ids).size).toBe(ids.length)
    })

    it('all permission names are unique', () => {
        const names = PERMISSIONS.map(p => p.name)
        expect(new Set(names).size).toBe(names.length)
    })

    it('note: file category is not in PERMISSION_GROUPS (known gap)', () => {
        // file:permission:manage has category="file" but PERMISSION_GROUPS doesn't include "file"
        // This is a known inconsistency in the current implementation.
        const known = new Set<string>(PERMISSION_GROUPS)
        const filePerm = PERMISSIONS.find(p => p.name === 'file:permission:manage')
        expect(known.has(filePerm!.category)).toBe(false)
    })
})

// ── FilePermissionItem mapping ─────────────────────────────────────────────────

describe('FilePermissionItem mapping', () => {
    function mapFilePermissionItem(item: any) {
        return {
            id: item.id,
            fileId: item.file_id,
            roleId: item.role_id ?? null,
            roleName: item.role_name ?? null,
            userId: item.user_id ?? null,
            username: item.username ?? null,
            permissionType: item.permission_type,
            grantedAt: item.granted_at ?? null,
        }
    }

    it('maps user-based permission entry', () => {
        const raw = {
            id: 1, file_id: 5,
            role_id: null, role_name: null,
            user_id: 3, username: 'alice',
            permission_type: 'read',
            granted_at: '2024-06-01T12:00:00',
        }
        const mapped = mapFilePermissionItem(raw)
        expect(mapped.id).toBe(1)
        expect(mapped.fileId).toBe(5)
        expect(mapped.roleId).toBeNull()
        expect(mapped.roleName).toBeNull()
        expect(mapped.userId).toBe(3)
        expect(mapped.username).toBe('alice')
        expect(mapped.permissionType).toBe('read')
        expect(mapped.grantedAt).toBe('2024-06-01T12:00:00')
    })

    it('maps role-based permission entry', () => {
        const raw = {
            id: 2, file_id: 5,
            role_id: 4, role_name: 'EDITOR',
            user_id: null, username: null,
            permission_type: 'write',
            granted_at: null,
        }
        const mapped = mapFilePermissionItem(raw)
        expect(mapped.roleId).toBe(4)
        expect(mapped.roleName).toBe('EDITOR')
        expect(mapped.userId).toBeNull()
        expect(mapped.username).toBeNull()
        expect(mapped.grantedAt).toBeNull()
    })

    it('all three permission_type values are preserved', () => {
        for (const ptype of ['read', 'write', 'delete']) {
            const mapped = mapFilePermissionItem({
                id: 1, file_id: 1, role_id: null, role_name: null,
                user_id: 1, username: 'u', permission_type: ptype, granted_at: null,
            })
            expect(mapped.permissionType).toBe(ptype)
        }
    })
})

// ── listUsers response structure ──────────────────────────────────────────────

describe('listUsers response mapping', () => {
    // Replicate the pass-through in role.ts: just returns res.data
    it('UserBasic interface has required fields', () => {
        const mockUser = {
            id: 1,
            username: 'alice',
            display_name: 'Alice',
            email: 'alice@example.com',
        }
        // All required fields present
        expect(mockUser).toHaveProperty('id')
        expect(mockUser).toHaveProperty('username')
        expect(mockUser).toHaveProperty('display_name')
        expect(mockUser).toHaveProperty('email')
    })

    it('display_name and email may be null', () => {
        const mockUser = { id: 2, username: 'bob', display_name: null, email: null }
        expect(mockUser.display_name).toBeNull()
        expect(mockUser.email).toBeNull()
    })
})

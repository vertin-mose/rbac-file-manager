/**
 * Unit tests for src/constants/permissions.ts
 * Verifies that the permission catalogue is complete and self-consistent.
 */

import { describe, it, expect } from 'vitest'
import { PERMISSIONS, PERMISSION_GROUPS } from '@/constants/permissions'

describe('permissions constants', () => {
    it('exports exactly 23 permissions (includes file:permission:manage)', () => {
        expect(PERMISSIONS).toHaveLength(23)
    })

    it('all permission ids are unique', () => {
        const ids = PERMISSIONS.map(p => p.id)
        const unique = new Set(ids)
        expect(unique.size).toBe(ids.length)
    })

    it('all permission names are unique', () => {
        const names = PERMISSIONS.map(p => p.name)
        const unique = new Set(names)
        expect(unique.size).toBe(names.length)
    })

    it('all permissions belong to a known group', () => {
        const known = new Set<string>(PERMISSION_GROUPS)
        for (const perm of PERMISSIONS) {
            expect(known.has(perm.category),
                `"${perm.name}" has unknown category "${perm.category}"`
            ).toBe(true)
        }
    })

    it('document permission group is populated', () => {
        const docPerms = PERMISSIONS.filter(p => p.category === 'document')
        expect(docPerms.length).toBeGreaterThanOrEqual(9)
    })

    it('system:config exists and belongs to system category', () => {
        const sc = PERMISSIONS.find(p => p.name === 'system:config')
        expect(sc).toBeDefined()
        expect(sc!.category).toBe('system')
    })

    it('file:permission:manage exists and belongs to file category', () => {
        const fp = PERMISSIONS.find(p => p.name === 'file:permission:manage')
        expect(fp).toBeDefined()
        expect(fp!.category).toBe('file')
    })

    it('doc:create and doc:read exist', () => {
        const names = PERMISSIONS.map(p => p.name)
        expect(names).toContain('doc:create')
        expect(names).toContain('doc:read')
    })

    it('every permission has a non-empty name and description', () => {
        for (const p of PERMISSIONS) {
            expect(p.name.trim().length).toBeGreaterThan(0)
            expect(p.description.trim().length).toBeGreaterThan(0)
        }
    })

    it('permission ids are sequential starting from 1', () => {
        const ids = [...PERMISSIONS].sort((a, b) => a.id - b.id).map(p => p.id)
        ids.forEach((id, idx) => {
            expect(id).toBe(idx + 1)
        })
    })
})

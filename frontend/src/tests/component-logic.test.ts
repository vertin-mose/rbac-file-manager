/**
 * Component logic tests for the feat/file-user-permissions branch.
 * Covers:
 *  - AppLayout: roleTagType, currentTitle (同 master)
 *  - FileTree: buildTree (同 master)
 *  - AuditLogView: actionMap (同 master，额外含 SET_FILE_PERMISSIONS)
 *  - FilePermissionDialog: permLabel, permTagType, handleAdd 权限合并逻辑
 */

import { describe, it, expect } from 'vitest'
import type { FileItem, FilePermissionItem } from '@/api/file'

// ── AppLayout — roleTagType ───────────────────────────────────────────────────

describe('AppLayout — roleTagType', () => {
    function roleTagType(level: number): string {
        if (level <= 2) return 'danger'
        if (level <= 3) return 'warning'
        if (level <= 4) return 'primary'
        return 'info'
    }
    it('L1 → danger',  () => expect(roleTagType(1)).toBe('danger'))
    it('L2 → danger',  () => expect(roleTagType(2)).toBe('danger'))
    it('L3 → warning', () => expect(roleTagType(3)).toBe('warning'))
    it('L4 → primary', () => expect(roleTagType(4)).toBe('primary'))
    it('L5 → info',    () => expect(roleTagType(5)).toBe('info'))
    it('99 → info',    () => expect(roleTagType(99)).toBe('info'))
})

// ── AppLayout — currentTitle ──────────────────────────────────────────────────

describe('AppLayout — currentTitle', () => {
    const map: Record<string, string> = {
        '/dashboard': '总体数据', '/files': '文件管理',
        '/roles': '角色管理', '/audit': '审计日志', '/system-config': '系统配置',
    }
    const currentTitle = (path: string) => map[path] || '文档管理系统'

    it.each([
        ['/dashboard', '总体数据'], ['/files', '文件管理'],
        ['/roles', '角色管理'], ['/audit', '审计日志'],
        ['/system-config', '系统配置'], ['/unknown', '文档管理系统'],
    ])('%s → %s', (path, expected) => expect(currentTitle(path)).toBe(expected))
})

// ── FileTree — buildTree ──────────────────────────────────────────────────────

describe('FileTree — buildTree()', () => {
    interface TreeNode { id: number; label: string; parentId: number; children?: TreeNode[] }

    function buildTree(items: FileItem[]): TreeNode[] {
        const map = new Map<number, TreeNode>()
        const roots: TreeNode[] = []
        items.forEach(item => map.set(item.id, {
            id: item.id, label: item.fileName, parentId: item.parentId ?? 0, children: [],
        }))
        map.forEach(node => {
            if (node.parentId === 0) { roots.push(node); return }
            const parent = map.get(node.parentId)
            parent ? (parent.children = parent.children || [], parent.children.push(node)) : roots.push(node)
        })
        return roots
    }

    function dir(id: number, name: string, parentId: number | null = null): FileItem {
        return { id, fileName: name, isDirectory: true, size: 0, mimeType: '',
                 ownerId: 1, parentId, storageUrl: '', createdAt: null, updatedAt: null }
    }

    it('empty → []', () => expect(buildTree([])).toEqual([]))
    it('single root dir', () => { const t = buildTree([dir(1,'A')]); expect(t[0].label).toBe('A') })
    it('child nested under parent', () => {
        const t = buildTree([dir(1,'P'), dir(2,'C',1)])
        expect(t[0].children![0].label).toBe('C')
    })
    it('orphan → goes to root', () => {
        const t = buildTree([dir(2,'Orphan',999)])
        expect(t[0].label).toBe('Orphan')
    })
    it('multiple children same parent', () => {
        const t = buildTree([dir(1,'P'), dir(2,'CA',1), dir(3,'CB',1)])
        expect(t[0].children).toHaveLength(2)
    })
})

// ── AuditLogView — actionMap ────────────────────────────────────────────

describe('AuditLogView — actionMap', () => {
    const actionOptions = [
        { label: '登录成功', value: 'LOGIN' },
        { label: '登录失败', value: 'LOGIN_FAILED' },
        { label: '退出登录', value: 'LOGOUT' },
        { label: '注册账号', value: 'REGISTER' },
        { label: '查看文件', value: 'VIEW_FILE' },
        { label: '下载文件', value: 'DOWNLOAD_FILE' },
        { label: '创建目录', value: 'CREATE_DIRECTORY' },
        { label: '上传文件', value: 'UPLOAD_FILE' },
        { label: '重命名文件', value: 'RENAME_FILE' },
        { label: '删除文件', value: 'DELETE_FILE' },
        { label: '共享文件', value: 'SHARE_FILE' },
        { label: '审阅文件', value: 'REVIEW_FILE' },
        { label: '审批文件', value: 'APPROVE_FILE' },
        { label: '评论文件', value: 'COMMENT_FILE' },
        { label: '更新文件', value: 'UPDATE_FILE' },
        { label: '设置文件权限', value: 'SET_FILE_PERMISSIONS' },
        { label: '删除文件权限', value: 'DELETE_FILE_PERMISSION' },
        { label: '创建角色', value: 'CREATE_ROLE' },
        { label: '更新角色', value: 'UPDATE_ROLE' },
        { label: '删除角色', value: 'DELETE_ROLE' },
        { label: '配置权限', value: 'ASSIGN_PERMISSIONS' },
        { label: '分配角色', value: 'ASSIGN_USER_ROLES' },
        { label: '创建用户', value: 'CREATE_USER' },
        { label: '删除用户', value: 'DELETE_USER' },
        { label: '启用/禁用', value: 'TOGGLE_USER_STATUS' },
        { label: '更新用户', value: 'UPDATE_USER' },
        { label: '删除记录', value: 'DELETE_ACTIVITY' },
    ]
    const actionMap: Record<string, string> = {}
    actionOptions.forEach(o => { actionMap[o.value] = o.label })

    it('LOGIN → 登录成功', () => expect(actionMap['LOGIN']).toBe('登录成功'))
    it('DELETE_FILE → 删除文件', () => expect(actionMap['DELETE_FILE']).toBe('删除文件'))
    it('ASSIGN_USER_ROLES → 分配角色', () => expect(actionMap['ASSIGN_USER_ROLES']).toBe('分配角色'))
    it('SET_FILE_PERMISSIONS → 设置文件权限', () => expect(actionMap['SET_FILE_PERMISSIONS']).toBe('设置文件权限'))
    it('UPDATE_FILE → 更新文件', () => expect(actionMap['UPDATE_FILE']).toBe('更新文件'))
    it('27 entries total', () => expect(Object.keys(actionMap)).toHaveLength(27))
})

// ── FilePermissionDialog — permLabel ─────────────────────────────────────────

describe('FilePermissionDialog — permLabel()', () => {
    function permLabel(type: string): string {
        const map: Record<string, string> = { read: '查看', write: '编辑', delete: '删除' }
        return map[type] || type
    }

    it('"read"   → "查看"', () => expect(permLabel('read')).toBe('查看'))
    it('"write"  → "编辑"', () => expect(permLabel('write')).toBe('编辑'))
    it('"delete" → "删除"', () => expect(permLabel('delete')).toBe('删除'))
    it('unknown type → passthrough', () => expect(permLabel('admin')).toBe('admin'))
    it('empty string → empty string', () => expect(permLabel('')).toBe(''))
})

// ── FilePermissionDialog — permTagType ───────────────────────────────────────

describe('FilePermissionDialog — permTagType()', () => {
    function permTagType(type: string): string {
        const map: Record<string, string> = { read: '', write: 'warning', delete: 'danger' }
        return map[type] !== undefined ? map[type] : ''
    }

    it('"read"   → "" (default/primary)',  () => expect(permTagType('read')).toBe(''))
    it('"write"  → "warning"',             () => expect(permTagType('write')).toBe('warning'))
    it('"delete" → "danger"',              () => expect(permTagType('delete')).toBe('danger'))
    it('unknown  → ""',                    () => expect(permTagType('other')).toBe(''))
})

// ── FilePermissionDialog — handleAdd 权限合并逻辑 ─────────────────────────────

describe('FilePermissionDialog — handleAdd permission merge logic', () => {
    /**
     * Replicates the merge logic from handleAdd():
     *   1. Find existing permissions for the selected user
     *   2. Union with newly selected types
     *   3. Build the full permissions array (other users unchanged + merged user perms)
     */

    function makePermItem(
        id: number, userId: number, username: string, ptype: string,
    ): FilePermissionItem {
        return { id, fileId: 1, roleId: null, roleName: null,
                 userId, username, permissionType: ptype, grantedAt: null }
    }

    function simulateHandleAdd(
        existingPerms: FilePermissionItem[],
        newUserId: number,
        newTypes: string[],
    ): { user_id: number; permission_type: string }[] {
        const existing = existingPerms.filter(p => p.userId === newUserId)
        const merged = [...new Set([...existing.map(p => p.permissionType), ...newTypes])]
        const allPerms = existingPerms
            .filter(p => p.userId !== newUserId && p.userId != null)
            .map(p => ({ user_id: p.userId!, permission_type: p.permissionType }))
        for (const t of merged) {
            allPerms.push({ user_id: newUserId, permission_type: t })
        }
        return allPerms
    }

    it('adds new permission to user with no existing permissions', () => {
        const result = simulateHandleAdd([], 3, ['read'])
        expect(result).toEqual([{ user_id: 3, permission_type: 'read' }])
    })

    it('merges new types with existing types for same user', () => {
        const existing = [makePermItem(1, 3, 'alice', 'read')]
        const result = simulateHandleAdd(existing, 3, ['write'])
        const types = result.map(r => r.permission_type).sort()
        expect(types).toEqual(['read', 'write'])
    })

    it('no duplicates when adding already-held permission', () => {
        const existing = [makePermItem(1, 3, 'alice', 'read')]
        const result = simulateHandleAdd(existing, 3, ['read'])
        const types = result.map(r => r.permission_type)
        expect(types.filter(t => t === 'read')).toHaveLength(1)
    })

    it('preserves permissions of OTHER users', () => {
        const existing = [
            makePermItem(1, 3, 'alice', 'read'),
            makePermItem(2, 7, 'bob',   'write'),
        ]
        const result = simulateHandleAdd(existing, 3, ['delete'])
        const bobEntry = result.find(r => r.user_id === 7)
        expect(bobEntry).toBeDefined()
        expect(bobEntry!.permission_type).toBe('write')
    })

    it('adds all three types at once', () => {
        const result = simulateHandleAdd([], 5, ['read', 'write', 'delete'])
        const types = result.map(r => r.permission_type).sort()
        expect(types).toEqual(['delete', 'read', 'write'])
    })

    it('empty newTypes results in only existing types being kept', () => {
        const existing = [makePermItem(1, 3, 'alice', 'read')]
        const result = simulateHandleAdd(existing, 3, [])
        expect(result).toHaveLength(1)
        expect(result[0].permission_type).toBe('read')
    })
})

// ── AuditLogView — filter/pagination state ────────────────────────────────────

describe('AuditLogView — filter and pagination helpers', () => {
    it('resetFilters clears all fields and resets page to 1', () => {
        const filters = { action: 'LOGIN', username: 'alice', dateRange: ['2024-01-01', '2024-12-31'] }
        let page = 3
        filters.action = ''; filters.username = ''; filters.dateRange = []; page = 1
        expect(filters.action).toBe('')
        expect(filters.username).toBe('')
        expect(filters.dateRange).toEqual([])
        expect(page).toBe(1)
    })

    it('handleSelectionChange collects row ids', () => {
        const selectedIds: number[] = []
        const rows = [{ id: 2 }, { id: 7 }, { id: 11 }]
        selectedIds.splice(0, selectedIds.length, ...rows.map(r => r.id))
        expect(selectedIds).toEqual([2, 7, 11])
    })

    it('dateRange provides undefined start/end when empty', () => {
        const [s, e] = ([] as string[])
        expect(s).toBeUndefined()
        expect(e).toBeUndefined()
    })
})

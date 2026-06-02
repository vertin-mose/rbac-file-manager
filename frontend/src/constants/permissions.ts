import type { Permission } from '@/api/role'

export type PermissionCategory = 'document' | 'user' | 'role' | 'audit' | 'system' | 'file'
export type PermissionTagType = 'primary' | 'success' | 'warning' | 'danger' | 'info'

export const PERMISSION_GROUPS = ['document', 'user', 'role', 'audit', 'system', 'file'] as const

export const PERMISSION_CATEGORY_META: Record<
    PermissionCategory,
    { label: string; shortLabel: string; tagType: PermissionTagType }
> = {
    document: { label: '文档权限', shortLabel: '文档', tagType: 'primary' },
    user: { label: '用户权限', shortLabel: '用户', tagType: 'success' },
    role: { label: '角色权限', shortLabel: '角色', tagType: 'warning' },
    audit: { label: '审计权限', shortLabel: '审计', tagType: 'info' },
    system: { label: '系统权限', shortLabel: '系统', tagType: 'danger' },
    file: { label: '文件权限', shortLabel: '文件', tagType: 'warning' },
}

export const PERMISSIONS: Permission[] = [
    { id: 1, name: 'doc:create', description: '创建目录、上传文件与新增文档', category: 'document' },
    { id: 2, name: 'doc:read', description: '查看文件列表、打开与下载文档', category: 'document' },
    { id: 3, name: 'doc:update', description: '编辑文档信息、重命名文件或目录', category: 'document' },
    { id: 4, name: 'doc:delete', description: '删除文件、目录与文档内容', category: 'document' },
    { id: 5, name: 'doc:review', description: '提交或处理文档审阅', category: 'document' },
    { id: 6, name: 'doc:approve', description: '审批文档流转结果', category: 'document' },
    { id: 7, name: 'doc:comment', description: '评论文档并添加批注', category: 'document' },
    { id: 8, name: 'doc:share', description: '向用户或角色共享文档', category: 'document' },
    { id: 9, name: 'doc:export', description: '导出文档或文档数据', category: 'document' },
    { id: 10, name: 'user:read', description: '查看用户资料与用户列表', category: 'user' },
    { id: 11, name: 'user:create', description: '创建新用户账号', category: 'user' },
    { id: 12, name: 'user:update', description: '修改用户资料、状态或基础信息', category: 'user' },
    { id: 13, name: 'user:delete', description: '删除或停用用户账号', category: 'user' },
    { id: 14, name: 'role:read', description: '查看角色、角色层级与权限配置', category: 'role' },
    { id: 15, name: 'role:create', description: '创建新角色', category: 'role' },
    { id: 16, name: 'role:update', description: '更新角色名称、说明或基础信息', category: 'role' },
    { id: 17, name: 'role:delete', description: '删除已有角色', category: 'role' },
    { id: 18, name: 'role:assign', description: '为用户分配或调整角色', category: 'role' },
    { id: 19, name: 'audit:read', description: '查看审计日志', category: 'audit' },
    { id: 20, name: 'audit:export', description: '导出审计日志数据', category: 'audit' },
    { id: 21, name: 'system:config', description: '修改系统配置与运行参数', category: 'system' },
    { id: 22, name: 'system:backup', description: '执行系统备份与恢复', category: 'system' },
    { id: 23, name: 'file:permission:manage', description: '管理文件用户权限', category: 'file' },
]

const RESOURCE_LABELS: Record<string, string> = {
    doc: '文档',
    user: '用户',
    role: '角色',
    audit: '审计',
    system: '系统',
}

const ACTION_LABELS: Record<string, string> = {
    create: '创建',
    read: '查看',
    update: '编辑',
    delete: '删除',
    review: '审阅',
    approve: '审批',
    comment: '评论',
    share: '共享',
    export: '导出',
    assign: '分配',
    config: '配置',
    backup: '备份',
}

const CATEGORY_BY_RESOURCE: Record<string, PermissionCategory> = {
    doc: 'document',
    user: 'user',
    role: 'role',
    audit: 'audit',
    system: 'system',
    file: 'file',
}

const permissionsByName = new Map(PERMISSIONS.map((permission) => [permission.name, permission]))

export interface PermissionMeta extends Permission {
    displayName: string
    categoryLabel: string
    categoryShortLabel: string
    tagType: PermissionTagType
}

export function resolvePermission(permission: Permission | string): PermissionMeta {
    const name = typeof permission === 'string' ? permission : permission.name
    const known = permissionsByName.get(name)
    const [resource = '', action = ''] = name.split(':')
    const category = (known?.category || CATEGORY_BY_RESOURCE[resource] || 'system') as PermissionCategory
    const categoryMeta = PERMISSION_CATEGORY_META[category] || PERMISSION_CATEGORY_META.system
    const resourceLabel = RESOURCE_LABELS[resource] || resource || '权限'
    const actionLabel = ACTION_LABELS[action] || action || '访问'
    const displayName = resource && action ? `${actionLabel}${resourceLabel}` : name

    return {
        id: typeof permission === 'string' ? known?.id ?? 0 : permission.id,
        name,
        description: known?.description || (typeof permission === 'string' ? displayName : permission.description || displayName),
        category,
        displayName,
        categoryLabel: categoryMeta.label,
        categoryShortLabel: categoryMeta.shortLabel,
        tagType: categoryMeta.tagType,
    }
}

export function permissionDisplayName(permission: Permission | string) {
    return resolvePermission(permission).displayName
}

export function permissionDescription(permission: Permission | string) {
    return resolvePermission(permission).description
}

export function permissionTagType(permission: Permission | string) {
    return resolvePermission(permission).tagType
}

export function permissionCategoryLabel(category: string) {
    return PERMISSION_CATEGORY_META[category as PermissionCategory]?.label || category
}

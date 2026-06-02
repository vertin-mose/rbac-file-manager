import type { Permission } from '@/api/role'

export const PERMISSIONS: Permission[] = [
    { id: 1, name: 'doc:create', description: '创建文档和目录', category: 'document' },
    { id: 2, name: 'doc:read', description: '查看和下载文档', category: 'document' },
    { id: 3, name: 'doc:update', description: '编辑文档', category: 'document' },
    { id: 4, name: 'doc:delete', description: '删除文档', category: 'document' },
    { id: 5, name: 'doc:review', description: '审阅文档', category: 'document' },
    { id: 6, name: 'doc:approve', description: '审批文档', category: 'document' },
    { id: 7, name: 'doc:comment', description: '评论和批注', category: 'document' },
    { id: 8, name: 'doc:share', description: '共享文档', category: 'document' },
    { id: 9, name: 'doc:export', description: '导出文档', category: 'document' },
    { id: 10, name: 'user:read', description: '查看用户', category: 'user' },
    { id: 11, name: 'user:create', description: '创建用户', category: 'user' },
    { id: 12, name: 'user:update', description: '修改用户', category: 'user' },
    { id: 13, name: 'user:delete', description: '删除用户', category: 'user' },
    { id: 14, name: 'role:read', description: '查看角色', category: 'role' },
    { id: 15, name: 'role:create', description: '创建角色', category: 'role' },
    { id: 16, name: 'role:update', description: '更新角色', category: 'role' },
    { id: 17, name: 'role:delete', description: '删除角色', category: 'role' },
    { id: 18, name: 'role:assign', description: '分配角色', category: 'role' },
    { id: 19, name: 'audit:read', description: '查看审计日志', category: 'audit' },
    { id: 20, name: 'audit:export', description: '导出审计日志', category: 'audit' },
    { id: 21, name: 'system:config', description: '修改系统配置', category: 'system' },
    { id: 22, name: 'system:backup', description: '系统备份恢复', category: 'system' },
    { id: 23, name: 'file:permission:manage', description: '管理文件角色权限', category: 'file' },
]

export const PERMISSION_GROUPS = ['document', 'user', 'role', 'audit', 'system', 'file'] as const

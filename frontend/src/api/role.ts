import request from './request'

export interface Permission {
    id: number
    name: string
    description: string
    category: string
}

export interface Role {
    id: number
    name: string
    description: string
    permissions: Permission[]
    inheritedPermissions: Permission[]
}

export interface RoleHierarchyItem {
    roleId: number
    roleName: string
    inheritedRoleId: number
    inheritedRoleName: string
}

function mapPermission(item: any): Permission {
    return {
        id: item.id,
        name: item.name,
        description: item.description || '',
        category: item.category || 'other',
    }
}

function mapRole(item: any): Role {
    return {
        id: item.id,
        name: item.name,
        description: item.description || '',
        permissions: (item.permissions || []).map(mapPermission),
        inheritedPermissions: (item.inherited_permissions || []).map(mapPermission),
    }
}

export async function getRoles(): Promise<Role[]> {
    const res: any = await request.get('/roles')
    return (res.data || []).map(mapRole)
}

export async function getRoleHierarchy(): Promise<RoleHierarchyItem[]> {
    const res: any = await request.get('/roles/hierarchy')
    return (res.data || []).map((item: any) => ({
        roleId: item.role_id,
        roleName: item.role_name,
        inheritedRoleId: item.inherited_role_id,
        inheritedRoleName: item.inherited_role_name,
    }))
}

export function createRole(data: { name: string; description: string; permissionIds: number[] }) {
    return request.post('/roles', {
        name: data.name,
        description: data.description,
        permission_ids: data.permissionIds,
    })
}

export function updateRole(id: number, data: Partial<Role>) {
    return request.put(`/roles/${id}`, {
        name: data.name,
        description: data.description,
    })
}

export function deleteRole(id: number) {
    return request.delete(`/roles/${id}`)
}

export function assignPermissions(roleId: number, permissionIds: number[]) {
    return request.put(`/roles/${roleId}/permissions`, { permission_ids: permissionIds })
}

export function assignUserRoles(userId: number, roleIds: number[]) {
    return request.put(`/users/${userId}/roles`, { role_ids: roleIds })
}

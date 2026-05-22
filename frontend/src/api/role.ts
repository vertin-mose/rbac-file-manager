import request from './request'

export interface Role {
    id: number
    name: string
    description: string
    enabled: boolean
    permissions: Permission[]
}

export interface Permission {
    id: number
    name: string
    description: string
    category: string
}

export function getRoles() {
    return request.get('/roles')
}

export function createRole(data: { name: string; description: string; permissionIds: number[] }) {
    return request.post('/roles', data)
}

export function updateRole(id: number, data: Partial<Role>) {
    return request.put(`/roles/${id}`, data)
}

export function deleteRole(id: number) {
    return request.delete(`/roles/${id}`)
}

export function assignPermissions(roleId: number, permissionIds: number[]) {
    return request.put(`/roles/${roleId}/permissions`, { permissionIds })
}

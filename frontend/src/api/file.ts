import request from './request'

export interface FileItem {
    id: number
    fileName: string
    isDirectory: boolean
    size: number
    mimeType: string
    ownerId: number
    parentId: number | null
    storageUrl: string
    createdAt: string | null
    updatedAt: string | null
}

function mapFileItem(item: any): FileItem {
    return {
        id: item.id,
        fileName: item.file_name,
        isDirectory: item.is_directory,
        size: item.size,
        mimeType: item.mime_type || '',
        ownerId: item.owner_id,
        parentId: item.parent_id ?? null,
        storageUrl: item.storage_url || '',
        createdAt: item.created_at ?? null,
        updatedAt: item.updated_at ?? null,
    }
}

export async function getFiles(parentId: number = 0): Promise<FileItem[]> {
    const res: any = await request.get('/files', { params: { parentId } })
    return (res.data || []).map(mapFileItem)
}

export async function getFile(id: number): Promise<FileItem> {
    const res: any = await request.get(`/files/${id}`)
    return mapFileItem(res.data)
}

export function uploadFile(file: File, parentId: number) {
    const formData = new FormData()
    formData.append('file', file)
    formData.append('parentId', String(parentId))
    return request.post('/files', formData, {
        headers: { 'Content-Type': undefined },
        timeout: 120000,
    })
}

export function updateFile(fileId: number, file: File) {
    const formData = new FormData()
    formData.append('file', file)
    return request.put(`/files/${fileId}/content`, formData, {
        headers: { 'Content-Type': undefined },
        timeout: 120000,
    })
}

export function updateFileTextContent(fileId: number, content: string): Promise<any> {
    return request.put(`/files/${fileId}/content/text`, { content })
}

export function createDirectory(name: string, parentId: number = 0) {
    return request.post('/files/directory', { file_name: name, parent_id: parentId })
}

export function deleteFile(id: number) {
    return request.delete(`/files/${id}`)
}

export function renameFile(id: number, newName: string) {
    return request.put(`/files/${id}`, { file_name: newName })
}

export function shareFile(id: number, payload: { userIds?: number[] }) {
    return request.post(`/files/${id}/share`, {
        user_ids: payload.userIds || [],
        permission_type: 'read',
    })
}

export function deleteActivity(fileId: number, activityId: number): Promise<void> {
    return request.delete(`/files/${fileId}/activities/${activityId}`)
}

export function reviewFile(id: number, content: string) {
    return request.post(`/files/${id}/review`, { content })
}

export function approveFile(id: number, content: string, approved: boolean = true) {
    return request.post(`/files/${id}/approve`, { content, approved })
}

export function commentFile(id: number, content: string) {
    return request.post(`/files/${id}/comment`, { content })
}

export interface FileActivityItem {
    id: number
    fileId: number
    userId: number
    username: string
    activityType: string
    content: string
    approved: boolean | null
    isHistory: boolean
    createdAt: string | null
}

function mapActivityItem(item: any): FileActivityItem {
    return {
        id: item.id,
        fileId: item.file_id,
        userId: item.user_id,
        username: item.username,
        activityType: item.activity_type,
        content: item.content || '',
        approved: item.approved ?? null,
        isHistory: item.is_history,
        createdAt: item.created_at ?? null,
    }
}

export async function getFileActivities(fileId: number): Promise<FileActivityItem[]> {
    const res: any = await request.get(`/files/${fileId}/activities`)
    return (res.data || []).map(mapActivityItem)
}

export async function downloadFile(id: number): Promise<Blob> {
    const res = await request.get(`/files/${id}/download`, {
        responseType: 'blob',
    })
    return res as unknown as Blob
}

export async function getFileTextContent(id: number): Promise<string> {
    const res = await request.get(`/files/${id}/content/text`, {
        responseType: 'text',
    })
    return res as unknown as string
}

export function getDownloadUrl(id: number): string {
    return `/api/files/${id}/download`
}

export interface FilePermissionItem {
    id: number
    fileId: number
    roleId: number | null
    roleName: string | null
    userId: number | null
    username: string | null
    permissionType: string
    grantedAt: string | null
}

function mapFilePermissionItem(item: any): FilePermissionItem {
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

export async function getFilePermissions(fileId: number): Promise<FilePermissionItem[]> {
    const res: any = await request.get(`/files/${fileId}/permissions`)
    return (res.data || []).map(mapFilePermissionItem)
}

export async function setFilePermissions(
    fileId: number,
    permissions: { role_id?: number; user_id?: number; permission_type: string }[],
): Promise<void> {
    await request.put(`/files/${fileId}/permissions`, { permissions })
}

export async function deleteFilePermission(fileId: number, permId: number): Promise<void> {
    await request.delete(`/files/${fileId}/permissions/${permId}`)
}

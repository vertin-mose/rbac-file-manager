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
    })
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

export function shareFile(id: number, payload: { userIds?: number[]; roleIds?: number[] }) {
    return request.post(`/files/${id}/share`, {
        user_ids: payload.userIds || [],
        role_ids: payload.roleIds || [],
    })
}

export function reviewFile(id: number, content: string) {
    return request.post(`/files/${id}/review`, { content })
}

export function approveFile(id: number, content: string) {
    return request.post(`/files/${id}/approve`, { content })
}

export function commentFile(id: number, content: string) {
    return request.post(`/files/${id}/comment`, { content })
}

export async function downloadFile(id: number): Promise<Blob> {
    const res = await request.get(`/files/${id}/download`, {
        responseType: 'blob',
    })
    return res as unknown as Blob
}

export function getDownloadUrl(id: number): string {
    return `/api/files/${id}/download`
}

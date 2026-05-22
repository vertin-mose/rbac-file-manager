import request from './request'

export interface FileItem {
    id: number
    fileName: string
    isDirectory: boolean
    size: number
    mimeType: string
    ownerId: number
    parentId: number | null
    createdAt: string
    updatedAt: string
}

export function getFiles(parentId: number = 0) {
    return request.get('/files', { params: { parentId } })
}

export function uploadFile(file: File, parentId: number) {
    const formData = new FormData()
    formData.append('file', file)
    formData.append('parentId', String(parentId))
    return request.post('/files', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
    })
}

export function createDirectory(name: string, parentId: number = 0) {
    return request.post('/files/directory', { fileName: name, parentId })
}

export function deleteFile(id: number) {
    return request.delete(`/files/${id}`)
}

export function renameFile(id: number, newName: string) {
    return request.put(`/files/${id}`, { fileName: newName })
}

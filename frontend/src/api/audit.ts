import request from './request'

export interface AuditLogItem {
    id: number
    userId: number
    username: string
    action: string
    detail: string
    ipAddress: string
    success: boolean
    createdAt: string
}

export function getAuditLogs(params?: {
    page?: number
    size?: number
    action?: string
    userId?: number
}) {
    return request.get('/audit-logs', { params })
}

export function exportAuditLogs() {
    return request.get('/audit-logs/export', { responseType: 'blob' })
}

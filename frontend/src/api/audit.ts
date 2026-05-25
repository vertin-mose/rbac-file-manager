import request from './request'

export interface AuditLogItem {
    id: number
    userId: number
    username: string
    action: string
    detail: string
    ipAddress: string
    success: boolean
    createdAt: string | null
}

export interface AuditLogPage {
    items: AuditLogItem[]
    total: number
    page: number
    size: number
}

function mapAuditLogItem(item: any): AuditLogItem {
    return {
        id: item.id,
        userId: item.user_id,
        username: item.username || '',
        action: item.action,
        detail: item.detail || '',
        ipAddress: item.ip_address || '',
        success: Boolean(item.success),
        createdAt: item.created_at ?? null,
    }
}

export async function getAuditLogs(params?: {
    page?: number
    size?: number
    action?: string
    userId?: number
}): Promise<AuditLogPage> {
    const res: any = await request.get('/audit-logs', { params })
    return {
        items: (res.data?.items || []).map(mapAuditLogItem),
        total: res.data?.total || 0,
        page: res.data?.page || params?.page || 1,
        size: res.data?.size || params?.size || 20,
    }
}

export function exportAuditLogs() {
    return request.get('/audit-logs/export', { responseType: 'blob' }) as Promise<Blob>
}

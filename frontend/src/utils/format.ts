export function formatBytes(size: number): string {
    if (!Number.isFinite(size) || size <= 0) return '0 B'
    const units = ['B', 'KB', 'MB', 'GB', 'TB']
    const index = Math.min(Math.floor(Math.log(size) / Math.log(1024)), units.length - 1)
    const value = size / (1024 ** index)
    return `${value >= 100 ? value.toFixed(0) : value.toFixed(1)} ${units[index]}`
}

export function formatDateTime(value?: string | null): string {
    if (!value) return '--'
    const date = new Date(value)
    if (Number.isNaN(date.getTime())) return value
    return date.toLocaleString('zh-CN', {
        year: 'numeric',
        month: '2-digit',
        day: '2-digit',
        hour: '2-digit',
        minute: '2-digit',
    })
}

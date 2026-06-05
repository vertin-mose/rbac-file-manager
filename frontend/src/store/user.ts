import { defineStore } from 'pinia'
import { computed, ref } from 'vue'
import { login as apiLogin, fetchMe, type LoginRequest, type RoleInfo } from '@/api/auth'

export const useUserStore = defineStore('user', () => {
    const token = ref(localStorage.getItem('token') || '')
    const userId = ref(Number(localStorage.getItem('userId') || 0))
    const username = ref(localStorage.getItem('username') || '')
    const displayName = ref(localStorage.getItem('displayName') || '')
    const roles = ref<string[]>(JSON.parse(localStorage.getItem('roles') || '[]'))
    const roleInfo = ref<RoleInfo[]>(JSON.parse(localStorage.getItem('roleInfo') || '[]'))
    const permissions = ref<string[]>(JSON.parse(localStorage.getItem('permissions') || '[]'))

    async function login(credentials: LoginRequest) {
        const res: any = await apiLogin(credentials)
        token.value = res.data.token
        userId.value = res.data.user_id || 0
        username.value = res.data.username
        displayName.value = res.data.display_name || ''
        roles.value = res.data.roles || []
        roleInfo.value = res.data.role_info || []
        permissions.value = res.data.permissions || []
        localStorage.setItem('token', res.data.token)
        localStorage.setItem('userId', String(res.data.user_id || 0))
        localStorage.setItem('username', res.data.username)
        localStorage.setItem('displayName', res.data.display_name || '')
        localStorage.setItem('roles', JSON.stringify(res.data.roles || []))
        localStorage.setItem('roleInfo', JSON.stringify(res.data.role_info || []))
        localStorage.setItem('permissions', JSON.stringify(res.data.permissions || []))
    }

    /** Refresh permissions from backend (resolves stale localStorage issues). */
    async function refreshPermissions() {
        if (!token.value) return
        try {
            const res: any = await fetchMe()
            const data = res.data
            if (data) {
                permissions.value = data.permissions || []
                localStorage.setItem('permissions', JSON.stringify(data.permissions || []))
            }
        } catch {
            // Silent — cached permissions stay visible
        }
    }

    function logout() {
        token.value = ''
        userId.value = 0
        username.value = ''
        displayName.value = ''
        roles.value = []
        roleInfo.value = []
        permissions.value = []
        localStorage.removeItem('token')
        localStorage.removeItem('userId')
        localStorage.removeItem('username')
        localStorage.removeItem('displayName')
        localStorage.removeItem('roles')
        localStorage.removeItem('roleInfo')
        localStorage.removeItem('permissions')
    }

    function hasRole(role: string): boolean {
        return roles.value.includes(role)
    }

    function hasPermission(perm: string): boolean {
        return permissions.value.includes(perm)
    }

    /** Highest role level (smallest number = most senior) */
    const highestLevel = computed(() => {
        if (roleInfo.value.length === 0) return 99
        return Math.min(...roleInfo.value.map(r => r.level))
    })

    /** Display name of the highest role */
    const roleDisplayName = computed(() => {
        if (roleInfo.value.length === 0) return ''
        const sorted = [...roleInfo.value].sort((a, b) => a.level - b.level)
        return sorted[0]?.display_name || ''
    })

    return {
        token, userId, username, displayName, roles, roleInfo, permissions,
        login, logout, refreshPermissions, hasRole, hasPermission,
        highestLevel, roleDisplayName,
    }
})

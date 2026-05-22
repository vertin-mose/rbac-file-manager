import request from './request'

export interface LoginRequest {
    username: string
    password: string
}

export interface RoleInfo {
    name: string
    display_name: string
    level: number
}

export interface LoginResponse {
    token: string
    username: string
    display_name: string
    roles: string[]
    role_info: RoleInfo[]
    permissions: string[]
}

export function login(data: LoginRequest) {
    return request.post('/auth/login', data)
}

export function register(data: { username: string; password: string; displayName?: string }) {
    return request.post('/auth/register', data)
}

export function logout() {
    return request.post('/auth/logout')
}

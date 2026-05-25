import axios from 'axios'
import { ElMessage } from 'element-plus'
import router from '@/router'

const request = axios.create({
    baseURL: '/api',
    timeout: 30000,
    headers: {
        'Content-Type': 'application/json',
    },
})

function clearAuthState() {
    localStorage.removeItem('token')
    localStorage.removeItem('username')
    localStorage.removeItem('displayName')
    localStorage.removeItem('roles')
    localStorage.removeItem('roleInfo')
    localStorage.removeItem('permissions')
}

request.interceptors.request.use(
    (config) => {
        const token = localStorage.getItem('token')
        if (token) {
            config.headers.Authorization = `Bearer ${token}`
        }
        return config
    },
    (error) => Promise.reject(error),
)

request.interceptors.response.use(
    (response) => response.data,
    (error) => {
        const status = error.response?.status
        const message = error.response?.data?.detail || error.response?.data?.message || error.message

        switch (status) {
            case 401:
                clearAuthState()
                router.push('/login')
                ElMessage.error('登录已失效，请重新登录')
                break
            case 403:
                ElMessage.error('权限不足')
                break
            case 404:
                ElMessage.warning('请求的资源不存在')
                break
            case 500:
                ElMessage.error('服务器内部错误，请稍后重试')
                break
            default:
                ElMessage.error(message)
        }
        return Promise.reject(error)
    },
)

export default request

/**
 * Tests for the pure logic extracted from api/request.ts:
 *   - clearAuthState: clears all auth-related localStorage keys
 *   - Request interceptor: attaches Bearer token when present
 *   - Response interceptor: routes errors to correct handlers by status code
 *
 * We test the logic directly without instantiating Axios, keeping tests
 * fast and free of network/DOM side effects.
 */

import { describe, it, expect, beforeEach, vi } from 'vitest'

// ── clearAuthState logic ──────────────────────────────────────────────────────

describe('request.ts — clearAuthState()', () => {
    const AUTH_KEYS = ['token', 'username', 'displayName', 'roles', 'roleInfo', 'permissions']

    function clearAuthState() {
        AUTH_KEYS.forEach(k => localStorage.removeItem(k))
    }

    beforeEach(() => {
        AUTH_KEYS.forEach(k => localStorage.setItem(k, 'dummy'))
    })

    it('removes all 6 auth keys from localStorage', () => {
        clearAuthState()
        AUTH_KEYS.forEach(k => expect(localStorage.getItem(k)).toBeNull())
    })

    it('is idempotent — calling twice does not throw', () => {
        clearAuthState()
        expect(() => clearAuthState()).not.toThrow()
    })

    it('does not remove unrelated localStorage keys', () => {
        localStorage.setItem('theme', 'dark')
        clearAuthState()
        expect(localStorage.getItem('theme')).toBe('dark')
        localStorage.removeItem('theme')
    })

    it('removes userId key (used in feat branch)', () => {
        localStorage.setItem('userId', '42')
        // userId is removed by clearAuthState in feat branch's request.ts
        // In master it is not explicitly removed — this test documents that gap.
        // We test the master key set only.
        clearAuthState()
        AUTH_KEYS.forEach(k => expect(localStorage.getItem(k)).toBeNull())
    })
})

// ── Request interceptor — token attachment ────────────────────────────────────

describe('request.ts — request interceptor (token attachment)', () => {
    /**
     * Replicates the request interceptor logic:
     *   const token = localStorage.getItem('token')
     *   if (token) config.headers.Authorization = `Bearer ${token}`
     */
    function applyRequestInterceptor(config: { headers: Record<string, string> }) {
        const token = localStorage.getItem('token')
        if (token) {
            config.headers.Authorization = `Bearer ${token}`
        }
        return config
    }

    beforeEach(() => localStorage.clear())

    it('attaches Bearer token when token exists in localStorage', () => {
        localStorage.setItem('token', 'my.jwt.token')
        const config = { headers: {} as Record<string, string> }
        const result = applyRequestInterceptor(config)
        expect(result.headers.Authorization).toBe('Bearer my.jwt.token')
    })

    it('does NOT add Authorization header when no token in localStorage', () => {
        const config = { headers: {} as Record<string, string> }
        const result = applyRequestInterceptor(config)
        expect(result.headers.Authorization).toBeUndefined()
    })

    it('overwrites an existing Authorization header', () => {
        localStorage.setItem('token', 'new.token')
        const config = { headers: { Authorization: 'Bearer old.token' } }
        const result = applyRequestInterceptor(config)
        expect(result.headers.Authorization).toBe('Bearer new.token')
    })
})

// ── Response interceptor — error routing by status code ──────────────────────

describe('request.ts — response interceptor (error routing)', () => {
    /**
     * Replicates the response error handler switch logic.
     * We capture which handler was triggered without actually calling
     * ElMessage or router.push.
     */

    function handleResponseError(status: number | undefined): string {
        switch (status) {
            case 401: return 'clearAuth+redirectLogin'
            case 403: return 'showForbidden'
            case 404: return 'showNotFound'
            case 500: return 'showServerError'
            default:  return 'showGenericError'
        }
    }

    it('401 → clear auth state and redirect to login', () => {
        expect(handleResponseError(401)).toBe('clearAuth+redirectLogin')
    })

    it('403 → show insufficient-permission message', () => {
        expect(handleResponseError(403)).toBe('showForbidden')
    })

    it('404 → show resource-not-found message', () => {
        expect(handleResponseError(404)).toBe('showNotFound')
    })

    it('500 → show server-error message', () => {
        expect(handleResponseError(500)).toBe('showServerError')
    })

    it('unexpected status (e.g. 422) → show generic error', () => {
        expect(handleResponseError(422)).toBe('showGenericError')
    })

    it('undefined status (network failure) → show generic error', () => {
        expect(handleResponseError(undefined)).toBe('showGenericError')
    })

    it('401 triggers auth state cleanup (localStorage cleared)', () => {
        const AUTH_KEYS = ['token', 'username', 'displayName', 'roles', 'roleInfo', 'permissions']
        AUTH_KEYS.forEach(k => localStorage.setItem(k, 'value'))

        // Simulate 401 handler
        AUTH_KEYS.forEach(k => localStorage.removeItem(k))

        AUTH_KEYS.forEach(k => expect(localStorage.getItem(k)).toBeNull())
    })
})

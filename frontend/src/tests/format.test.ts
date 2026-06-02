/**
 * Tests for src/utils/format.ts — formatBytes and formatDateTime.
 */

import { describe, it, expect } from 'vitest'
import { formatBytes, formatDateTime } from '@/utils/format'

describe('formatBytes', () => {
    it('returns "0 B" for zero', () => {
        expect(formatBytes(0)).toBe('0 B')
    })

    it('returns "0 B" for negative numbers', () => {
        expect(formatBytes(-100)).toBe('0 B')
    })

    it('returns "0 B" for non-finite', () => {
        expect(formatBytes(Infinity)).toBe('0 B')
        expect(formatBytes(NaN)).toBe('0 B')
    })

    it('formats bytes < 1024 as "X.X B"', () => {
        expect(formatBytes(512)).toBe('512.0 B')
    })

    it('formats 1 KB', () => {
        expect(formatBytes(1024)).toBe('1.0 KB')
    })

    it('formats 1 MB', () => {
        expect(formatBytes(1024 * 1024)).toBe('1.0 MB')
    })

    it('formats 1 GB', () => {
        expect(formatBytes(1024 ** 3)).toBe('1.0 GB')
    })

    it('formats 1 TB', () => {
        expect(formatBytes(1024 ** 4)).toBe('1.0 TB')
    })

    it('shows 0 decimal places for values >= 100', () => {
        // 150 KB
        const result = formatBytes(150 * 1024)
        expect(result).toBe('150 KB')
    })

    it('shows 1 decimal place for values < 100', () => {
        const result = formatBytes(1.5 * 1024)
        expect(result).toBe('1.5 KB')
    })
})

describe('formatDateTime', () => {
    it('returns "--" for null', () => {
        expect(formatDateTime(null)).toBe('--')
    })

    it('returns "--" for undefined', () => {
        expect(formatDateTime(undefined)).toBe('--')
    })

    it('returns "--" for empty string', () => {
        expect(formatDateTime('')).toBe('--')
    })

    it('returns the original string for an invalid date', () => {
        const bad = 'not-a-date'
        expect(formatDateTime(bad)).toBe(bad)
    })

    it('returns a formatted string for a valid ISO date', () => {
        const result = formatDateTime('2024-06-01T08:30:00')
        // Should be a non-empty string that is not '--'
        expect(result).not.toBe('--')
        expect(result.length).toBeGreaterThan(0)
        // Should contain the year
        expect(result).toContain('2024')
    })

    it('handles date-only string', () => {
        const result = formatDateTime('2024-06-01')
        expect(result).not.toBe('--')
        expect(result).toContain('2024')
    })
})

/**
 * Tests for src/store/file.ts — Pinia file store.
 * Covers: initial state, openDirectory path tracking,
 * resetToRoot, selectFile, currentParentId computed.
 */

import { describe, it, expect, beforeEach, vi } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { useFileStore } from '@/store/file'
import type { FileItem } from '@/api/file'

// Mock getFiles so we don't make real HTTP calls
vi.mock('@/api/file', () => ({
    getFiles: vi.fn(),
}))

import { getFiles } from '@/api/file'

// ── Fixtures ──────────────────────────────────────────────────────────────────

function makeDir(id: number, name: string, parentId: number | null = null): FileItem {
    return {
        id, fileName: name, isDirectory: true, size: 0,
        mimeType: '', ownerId: 1, parentId,
        storageUrl: '', createdAt: null, updatedAt: null,
    }
}

function makeFile(id: number, name: string, parentId: number | null = null): FileItem {
    return {
        id, fileName: name, isDirectory: false, size: 1024,
        mimeType: 'text/plain', ownerId: 1, parentId,
        storageUrl: 'local://x', createdAt: null, updatedAt: null,
    }
}

beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
})

// ── Initial state ─────────────────────────────────────────────────────────────

describe('fileStore — initial state', () => {
    it('starts at root with empty file list', () => {
        const store = useFileStore()
        expect(store.currentPath).toEqual([{ id: 0, name: 'Root' }])
        expect(store.files).toEqual([])
        expect(store.selectedFile).toBeNull()
        expect(store.loading).toBe(false)
    })

    it('currentParentId is 0 at root', () => {
        const store = useFileStore()
        expect(store.currentParentId).toBe(0)
    })
})

// ── loadFiles ─────────────────────────────────────────────────────────────────

describe('fileStore — loadFiles()', () => {
    it('populates files array', async () => {
        const mockFiles = [makeFile(1, 'readme.txt'), makeDir(2, 'docs')]
        vi.mocked(getFiles).mockResolvedValue(mockFiles)
        const store = useFileStore()
        await store.loadFiles(0)
        expect(store.files).toHaveLength(2)
        expect(store.loading).toBe(false)
    })

    it('sets loading=true while fetching then false after', async () => {
        let resolve!: (v: FileItem[]) => void
        vi.mocked(getFiles).mockReturnValue(new Promise(r => { resolve = r }))
        const store = useFileStore()
        const prom = store.loadFiles(0)
        expect(store.loading).toBe(true)
        resolve([])
        await prom
        expect(store.loading).toBe(false)
    })

    it('loading becomes false even if getFiles throws', async () => {
        vi.mocked(getFiles).mockRejectedValue(new Error('network error'))
        const store = useFileStore()
        try { await store.loadFiles(0) } catch { /* expected */ }
        expect(store.loading).toBe(false)
    })
})

// ── openDirectory ─────────────────────────────────────────────────────────────

describe('fileStore — openDirectory()', () => {
    it('appends new directory to path', async () => {
        vi.mocked(getFiles).mockResolvedValue([])
        const store = useFileStore()
        await store.openDirectory({ id: 5, name: 'Projects' })
        expect(store.currentPath).toEqual([
            { id: 0, name: 'Root' },
            { id: 5, name: 'Projects' },
        ])
        expect(store.currentParentId).toBe(5)
    })

    it('navigates back when visiting an existing path entry (breadcrumb click)', async () => {
        vi.mocked(getFiles).mockResolvedValue([])
        const store = useFileStore()
        await store.openDirectory({ id: 5, name: 'A' })
        await store.openDirectory({ id: 10, name: 'B' })
        // Click on 'A' in breadcrumb — should slice back
        await store.openDirectory({ id: 5, name: 'A' })
        expect(store.currentPath).toEqual([
            { id: 0, name: 'Root' },
            { id: 5, name: 'A' },
        ])
    })

    it('clears selectedFile when navigating', async () => {
        vi.mocked(getFiles).mockResolvedValue([])
        const store = useFileStore()
        store.selectFile(makeFile(99, 'selected.txt'))
        await store.openDirectory({ id: 5, name: 'Dir' })
        expect(store.selectedFile).toBeNull()
    })

    it('accepts fileName property (from FileItem)', async () => {
        vi.mocked(getFiles).mockResolvedValue([])
        const store = useFileStore()
        await store.openDirectory({ id: 7, fileName: 'Reports' })
        expect(store.currentPath[1].name).toBe('Reports')
    })

    it('falls back to "目录 {id}" when no name given', async () => {
        vi.mocked(getFiles).mockResolvedValue([])
        const store = useFileStore()
        await store.openDirectory({ id: 8 })
        expect(store.currentPath[1].name).toBe('目录 8')
    })
})

// ── openFileDirectory ─────────────────────────────────────────────────────────

describe('fileStore — openFileDirectory()', () => {
    it('navigates when given a directory FileItem', async () => {
        vi.mocked(getFiles).mockResolvedValue([])
        const store = useFileStore()
        const dir = makeDir(3, 'Contracts')
        await store.openFileDirectory(dir)
        expect(store.currentParentId).toBe(3)
    })

    it('does nothing when given a non-directory FileItem', async () => {
        vi.mocked(getFiles).mockResolvedValue([])
        const store = useFileStore()
        const file = makeFile(99, 'readme.txt')
        await store.openFileDirectory(file)
        expect(store.currentPath).toHaveLength(1) // stays at root
    })
})

// ── resetToRoot ───────────────────────────────────────────────────────────────

describe('fileStore — resetToRoot()', () => {
    it('resets path to [Root] and clears selection', async () => {
        vi.mocked(getFiles).mockResolvedValue([])
        const store = useFileStore()
        await store.openDirectory({ id: 5, name: 'X' })
        store.selectFile(makeFile(1, 'x.txt'))
        await store.resetToRoot()
        expect(store.currentPath).toEqual([{ id: 0, name: 'Root' }])
        expect(store.selectedFile).toBeNull()
        expect(store.currentParentId).toBe(0)
    })
})

// ── selectFile ────────────────────────────────────────────────────────────────

describe('fileStore — selectFile()', () => {
    it('sets selectedFile', () => {
        const store = useFileStore()
        const f = makeFile(10, 'doc.txt')
        store.selectFile(f)
        expect(store.selectedFile).toEqual(f)
    })

    it('clears selectedFile when passed null', () => {
        const store = useFileStore()
        store.selectFile(makeFile(1, 'x'))
        store.selectFile(null)
        expect(store.selectedFile).toBeNull()
    })
})

import { computed, ref } from 'vue'
import { defineStore } from 'pinia'
import { getFiles, type FileItem } from '@/api/file'

export const useFileStore = defineStore('file', () => {
    const currentPath = ref<{ id: number; name: string }[]>([{ id: 0, name: 'Root' }])
    const files = ref<FileItem[]>([])
    const selectedFile = ref<FileItem | null>(null)
    const loading = ref(false)

    const currentParentId = computed(() => currentPath.value[currentPath.value.length - 1]?.id ?? 0)

    async function loadFiles(parentId: number = currentParentId.value) {
        loading.value = true
        try {
            files.value = await getFiles(parentId)
            if (selectedFile.value) {
                selectedFile.value = files.value.find((item) => item.id === selectedFile.value?.id) || null
            }
        } finally {
            loading.value = false
        }
    }

    async function openDirectory(target: { id: number; fileName?: string; name?: string }) {
        const index = currentPath.value.findIndex((item) => item.id === target.id)
        if (index >= 0) {
            currentPath.value = currentPath.value.slice(0, index + 1)
        } else {
            currentPath.value.push({
                id: target.id,
                name: target.fileName || target.name || `目录 ${target.id}`,
            })
        }
        selectedFile.value = null
        await loadFiles(target.id)
    }

    async function openFileDirectory(file: FileItem) {
        if (!file.isDirectory) return
        await openDirectory({ id: file.id, fileName: file.fileName })
    }

    async function resetToRoot() {
        currentPath.value = [{ id: 0, name: 'Root' }]
        selectedFile.value = null
        await loadFiles(0)
    }

    function selectFile(file: FileItem | null) {
        selectedFile.value = file
    }

    return {
        currentPath,
        currentParentId,
        files,
        selectedFile,
        loading,
        loadFiles,
        openDirectory,
        openFileDirectory,
        resetToRoot,
        selectFile,
    }
})

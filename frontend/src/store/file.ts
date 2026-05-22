import { defineStore } from 'pinia'
import { ref } from 'vue'
import { getFiles, type FileItem } from '@/api/file'

export const useFileStore = defineStore('file', () => {
    const currentPath = ref<{ id: number; name: string }[]>([{ id: 0, name: 'Root' }])
    const files = ref<FileItem[]>([])
    const selectedFile = ref<FileItem | null>(null)
    const loading = ref(false)

    async function loadFiles(parentId: number = 0) {
        loading.value = true
        try {
            const res: any = await getFiles(parentId)
            files.value = res.data
        } finally {
            loading.value = false
        }
    }

    function navigateToDir(file: FileItem) {
        if (file.isDirectory) {
            currentPath.value.push({ id: file.id, name: file.fileName })
            loadFiles(file.id)
        }
    }

    function navigateUp() {
        if (currentPath.value.length > 1) {
            currentPath.value.pop()
            const parentId = currentPath.value[currentPath.value.length - 1].id
            loadFiles(parentId)
        }
    }

    function selectFile(file: FileItem | null) {
        selectedFile.value = file
    }

    return { currentPath, files, selectedFile, loading, loadFiles, navigateToDir, navigateUp, selectFile }
})

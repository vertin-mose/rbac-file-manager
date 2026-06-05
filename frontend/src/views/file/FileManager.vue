<template>
  <div class="file-page">
    <div v-if="!userStore.hasPermission('doc:read')" class="empty-wrap">
      <el-empty description="您没有查看文件的权限" />
    </div>

    <template v-else>
      <section class="page-hero">
        <div>
          <p class="eyebrow">Workspace</p>
          <h1>文件管理</h1>
          <p class="hero-copy">集中查看目录结构、上传文档，并按权限执行协作操作。</p>
        </div>
        <div class="hero-actions">
          <el-button
            v-if="userStore.hasPermission('doc:create')"
            type="primary"
            @click="openCreateDialog()"
          >
            新建目录
          </el-button>
          <el-button
            v-if="userStore.hasPermission('doc:create')"
            type="success"
            @click="triggerFileUpload"
          >
            上传文件
          </el-button>
          <input
            ref="fileInputRef"
            type="file"
            style="display: none"
            @change="handleFileInputChange"
          />
          <input
            ref="updateInputRef"
            type="file"
            style="display: none"
            @change="handleUpdateInputChange"
          />
          <el-button :loading="fileStore.loading" @click="refreshAll">刷新</el-button>
        </div>
      </section>

      <div class="content-grid">
        <el-card class="sidebar-card" shadow="never">
          <FileTree
            ref="fileTreeRef"
            :can-create="userStore.hasPermission('doc:create')"
            :can-update="userStore.hasPermission('doc:update')"
            :can-delete="userStore.hasPermission('doc:delete')"
            @select="handleTreeSelect"
            @create-root="openRootCreateDialog"
            @create-child="openCreateDialog"
            @rename="openRenameDialog"
            @delete="confirmDeleteTreeNode"
          />
        </el-card>

        <div class="main-column">
          <el-card class="breadcrumb-card" shadow="never">
            <div class="breadcrumb-bar">
              <el-breadcrumb separator="/">
                <el-breadcrumb-item
                  v-for="segment in fileStore.currentPath"
                  :key="segment.id"
                >
                  <a href="#" @click.prevent="fileStore.openDirectory(segment)">{{ segment.name }}</a>
                </el-breadcrumb-item>
              </el-breadcrumb>
              <el-tag type="info" effect="plain">{{ fileStore.files.length }} 项内容</el-tag>
            </div>
          </el-card>

          <el-card class="table-card" shadow="never">
            <template #header>
              <div class="table-header">
                <div>
                  <h2>目录内容</h2>
                  <p>双击目录进入，单击选中项目后执行操作。</p>
                </div>
                <div class="ability-summary">
                  <el-tag
                    v-if="userStore.hasPermission('file:permission:manage')"
                    type="warning"
                    effect="plain"
                    size="small"
                  >管理员权限模式</el-tag>
                  <el-tag v-else effect="plain" size="small">文件权限控制模式</el-tag>
                </div>
              </div>
            </template>

            <el-table
              :data="fileStore.files"
              v-loading="fileStore.loading"
              row-key="id"
              highlight-current-row
              @row-click="handleRowClick"
              @row-dblclick="handleRowDoubleClick"
            >
              <el-table-column label="名称" min-width="260">
                <template #default="{ row }">
                  <div class="name-cell"
                    @click.stop="handleViewFile(row)"
                    @dblclick.stop="handleRowDoubleClick(row)">
                    <el-icon :color="row.isDirectory ? '#c78d2a' : '#4f6b88'">
                      <Folder v-if="row.isDirectory" />
                      <Document v-else />
                    </el-icon>
                    <span class="file-name-text">{{ row.fileName }}</span>
                  </div>
                </template>
              </el-table-column>

              <el-table-column label="类型" min-width="120">
                <template #default="{ row }">
                  <el-tag :type="row.isDirectory ? 'warning' : 'info'" effect="plain" size="small">
                    {{ row.isDirectory ? '目录' : fileTypeLabel(row.mimeType) }}
                  </el-tag>
                </template>
              </el-table-column>

              <el-table-column label="大小" width="120">
                <template #default="{ row }">
                  {{ row.isDirectory ? '--' : formatBytes(row.size) }}
                </template>
              </el-table-column>

              <el-table-column label="更新时间" min-width="180">
                <template #default="{ row }">
                  {{ formatDateTime(row.updatedAt || row.createdAt) }}
                </template>
              </el-table-column>

              <el-table-column label="操作" min-width="340" fixed="right">
                <template #default="{ row }">
                  <div class="table-actions">
                    <el-button
                      v-if="row.isDirectory"
                      link
                      type="primary"
                      @click.stop="fileStore.openFileDirectory(row)"
                    >
                      打开
                    </el-button>
                    <el-button
                      v-if="!row.isDirectory"
                      link
                      type="primary"
                      @click.stop="handleViewFile(row)"
                    >
                      查看
                    </el-button>
                    <el-button
                      v-if="!row.isDirectory && isTextFile(row) && userStore.hasPermission('doc:edit')"
                      link
                      type="primary"
                      @click.stop="handleEditFile(row)"
                    >
                      编辑
                    </el-button>
                    <el-button
                      v-if="!row.isDirectory"
                      link
                      type="primary"
                      @click.stop="handleDownloadFile(row)"
                    >
                      下载
                    </el-button>
                    <el-button
                      v-if="!row.isDirectory && userStore.hasPermission('doc:update')"
                      link
                      type="primary"
                      @click.stop="handleUpdateFile(row)"
                    >
                      更新
                    </el-button>
                    <el-button
                      v-if="userStore.hasPermission('doc:update')"
                      link
                      @click.stop="openRenameDialog({ id: row.id, label: row.fileName })"
                    >
                      重命名
                    </el-button>
                    <el-button
                      v-if="userStore.hasPermission('doc:share')"
                      link
                      @click.stop="openShareDialog(row)"
                    >
                      共享
                    </el-button>
                    <el-button
                      v-if="userStore.hasPermission('doc:review')"
                      link
                      @click.stop="openActionDialog('review', row)"
                    >
                      审阅
                    </el-button>
                    <el-button
                      v-if="userStore.hasPermission('doc:approve')"
                      link
                      @click.stop="openActionDialog('approve', row)"
                    >
                      审批
                    </el-button>
                    <el-button
                      v-if="userStore.hasPermission('doc:comment')"
                      link
                      @click.stop="openActionDialog('comment', row)"
                    >
                      评论
                    </el-button>
                    <el-button
                      v-if="userStore.hasPermission('doc:delete')"
                      link
                      type="danger"
                      @click.stop="confirmDelete(row)"
                    >
                      删除
                    </el-button>
                    <el-button
                      v-if="userStore.hasPermission('file:permission:manage')"
                      link
                      type="warning"
                      @click.stop="openPermissionDialog(row)"
                    >
                      权限
                    </el-button>
                  </div>
                </template>
              </el-table-column>
            </el-table>

            <el-empty
              v-if="!fileStore.loading && fileStore.files.length === 0"
              description="当前目录暂无内容"
            />
          </el-card>
        </div>
      </div>
    </template>

    <el-dialog
      v-model="dialogs.create.visible"
      :title="dialogs.create.parentId === 0 ? '新建根目录' : '新建子目录'"
      width="420px"
    >
      <el-form label-position="top" @submit.prevent>
        <el-form-item label="目录名称">
          <el-input
            v-model="dialogs.create.name"
            maxlength="120"
            placeholder="请输入目录名称"
            @keyup.enter="submitCreateDirectory"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogs.create.visible = false">取消</el-button>
        <el-button type="primary" @click="submitCreateDirectory">确定</el-button>
      </template>
    </el-dialog>

    <el-dialog
      v-model="dialogs.rename.visible"
      title="重命名"
      width="420px"
    >
      <el-form label-position="top" @submit.prevent>
        <el-form-item label="名称">
          <el-input
            v-model="dialogs.rename.name"
            maxlength="120"
            placeholder="请输入新的名称"
            @keyup.enter="submitRename"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogs.rename.visible = false">取消</el-button>
        <el-button type="primary" @click="submitRename">保存</el-button>
      </template>
    </el-dialog>

    <FilePermissionDialog
      :visible="dialogs.permission.visible"
      :file-id="dialogs.permission.fileId"
      :file-name="dialogs.permission.fileName"
      @close="dialogs.permission.visible = false"
      @updated="refreshAll"
    />

    <ShareDialog
      :visible="dialogs.share.visible"
      :file-id="dialogs.share.fileId"
      :file-name="dialogs.share.fileName"
      @close="dialogs.share.visible = false"
      @updated="refreshAll"
    />

    <FileActivityDialog
      :visible="dialogs.activity.visible"
      :file-id="dialogs.activity.fileId"
      :file-name="dialogs.activity.fileName"
      :mode="dialogs.activity.mode"
      @close="dialogs.activity.visible = false"
      @updated="refreshAll"
    />

    <el-dialog
      v-model="dialogs.edit.visible"
      title="编辑文件"
      width="820px"
      :close-on-click-modal="false"
      @closed="dialogs.edit.content = ''"
    >
      <template #header>
        <div class="edit-dialog-header">
          <span>编辑文件</span>
          <span class="edit-file-name">{{ dialogs.edit.fileName }}</span>
        </div>
      </template>
      <div v-loading="dialogs.edit.loading" class="edit-textarea-wrap">
        <el-input
          v-model="dialogs.edit.content"
          type="textarea"
          :autosize="{ minRows: 18, maxRows: 30 }"
          :disabled="dialogs.edit.saving"
          class="edit-textarea"
        />
      </div>
      <template #footer>
        <el-button @click="dialogs.edit.visible = false" :disabled="dialogs.edit.saving">取消</el-button>
        <el-button type="primary" @click="submitEdit" :loading="dialogs.edit.saving">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Document, Folder } from '@element-plus/icons-vue'
import FileActivityDialog from '@/components/FileActivityDialog.vue'
import FileTree from '@/components/FileTree.vue'
import FilePermissionDialog from '@/components/FilePermissionDialog.vue'
import ShareDialog from '@/components/ShareDialog.vue'
import {
  createDirectory,
  deleteFile,
  downloadFile,
  getFileTextContent,
  renameFile,
  shareFile,
  updateFile,
  updateFileTextContent,
  uploadFile,
  type FileItem,
} from '@/api/file'
import { useFileStore } from '@/store/file'
import { useUserStore } from '@/store/user'
import { formatBytes, formatDateTime } from '@/utils/format'

const fileStore = useFileStore()
const userStore = useUserStore()
const fileTreeRef = ref<InstanceType<typeof FileTree> | null>(null)
const fileInputRef = ref<HTMLInputElement | null>(null)
const updateInputRef = ref<HTMLInputElement | null>(null)

const dialogs = reactive({
  create: {
    visible: false,
    parentId: 0,
    name: '',
    jumpToRootAfterSubmit: false,
  },
  rename: {
    visible: false,
    fileId: 0,
    name: '',
  },
  activity: {
    visible: false,
    fileId: 0,
    fileName: '',
    mode: 'review' as 'review' | 'approve' | 'comment',
  },
  edit: {
    visible: false,
    fileId: 0,
    fileName: '',
    content: '',
    loading: false,
    saving: false,
  },
  permission: {
    visible: false,
    fileId: 0,
    fileName: '',
  },
  share: {
    visible: false,
    fileId: 0,
    fileName: '',
  },
})

async function refreshAll() {
  await fileStore.loadFiles()
  await fileTreeRef.value?.reload()
}

function openCreateDialog(payload?: { id?: number; parentId?: number }) {
  dialogs.create.parentId = payload?.id ?? payload?.parentId ?? fileStore.currentParentId
  dialogs.create.name = ''
  dialogs.create.jumpToRootAfterSubmit = false
  dialogs.create.visible = true
}

function openRootCreateDialog() {
  dialogs.create.parentId = 0
  dialogs.create.name = ''
  dialogs.create.jumpToRootAfterSubmit = true
  dialogs.create.visible = true
}

async function submitCreateDirectory() {
  const name = dialogs.create.name.trim()
  if (!name) {
    ElMessage.warning('目录名称不能为空')
    return
  }

  try {
    await createDirectory(name, dialogs.create.parentId)
    dialogs.create.visible = false
    dialogs.create.name = ''
    ElMessage.success('目录已创建')
  } catch {
    ElMessage.error('创建目录失败')
    return
  }

  if (dialogs.create.jumpToRootAfterSubmit) {
    await fileStore.resetToRoot()
  }

  await refreshAll()
}

function openRenameDialog(payload: { id: number; label: string }) {
  dialogs.rename.fileId = payload.id
  dialogs.rename.name = payload.label
  dialogs.rename.visible = true
}

async function submitRename() {
  const name = dialogs.rename.name.trim()
  if (!name) {
    ElMessage.warning('名称不能为空')
    return
  }

  await renameFile(dialogs.rename.fileId, name)
  dialogs.rename.visible = false
  dialogs.rename.name = ''
  ElMessage.success('已重命名')
  await refreshAll()
}

function openActionDialog(mode: 'review' | 'approve' | 'comment', file: FileItem) {
  dialogs.activity.visible = true
  dialogs.activity.mode = mode
  dialogs.activity.fileId = file.id
  dialogs.activity.fileName = file.fileName
}

function handleUpdateFile(file: FileItem) {
  if (file.isDirectory) return
  dialogs.activity.visible = false
  dialogs.share.visible = false
  dialogs.permission.visible = false
  // Store current file and trigger file picker
  updateTargetFile.value = file
  updateInputRef.value?.click()
}

const updateTargetFile = ref<FileItem | null>(null)

async function handleUpdateInputChange(e: Event) {
  const input = e.target as HTMLInputElement
  const file = input.files?.[0]
  if (!file || !updateTargetFile.value) return

  try {
    await updateFile(updateTargetFile.value.id, file)
    ElMessage.success('文件已更新')
    await refreshAll()
  } catch {
    ElMessage.error('更新失败')
  } finally {
    input.value = ''
    updateTargetFile.value = null
  }
}

function openPermissionDialog(file: FileItem) {
  dialogs.permission.fileId = file.id
  dialogs.permission.fileName = file.fileName
  dialogs.permission.visible = true
}

function openShareDialog(file: FileItem) {
  dialogs.share.fileId = file.id
  dialogs.share.fileName = file.fileName
  dialogs.share.visible = true
}

function fileTypeLabel(mimeType: string): string {
  if (!mimeType) return '文件'
  if (mimeType.includes('pdf')) return 'PDF'
  if (mimeType.includes('word') || mimeType.includes('document')) return 'Word'
  if (mimeType.includes('sheet') || mimeType.includes('excel')) return '表格'
  if (mimeType.includes('presentation') || mimeType.includes('powerpoint')) return '演示文稿'
  if (mimeType.startsWith('image/')) return '图片'
  if (mimeType.startsWith('text/')) return '文本'
  if (mimeType.includes('zip') || mimeType.includes('compressed')) return '压缩包'
  return mimeType.split('/').pop()?.toUpperCase() || '文件'
}

const EDITABLE_TEXT_EXTENSIONS = new Set([
  'txt', 'sql', 'md', 'json', 'xml', 'csv', 'yaml', 'yml',
  'py', 'java', 'js', 'ts', 'html', 'css', 'scss', 'vue', 'jsx', 'tsx',
  'c', 'cpp', 'h', 'hpp', 'rs', 'go', 'sh', 'bat', 'ini', 'cfg', 'toml',
  'log', 'env', 'gitignore', 'dockerfile', 'makefile',
])

function isTextFile(row: { mimeType: string; fileName: string }): boolean {
  const mime = (row.mimeType || '').toLowerCase()
  if (mime.startsWith('text/')) return true
  if (mime === 'application/json' || mime === 'application/xml' || mime === 'application/javascript') return true
  if (mime.includes('sql')) return true
  const ext = (row.fileName || '').split('.').pop()?.toLowerCase() || ''
  return EDITABLE_TEXT_EXTENSIONS.has(ext)
}

function isImageFile(mimeType: string): boolean {
  return (mimeType || '').toLowerCase().startsWith('image/')
}

async function confirmDelete(file: FileItem) {
  try {
    await ElMessageBox.confirm(`确认删除 ${file.fileName} 吗？`, '删除确认', {
      type: 'warning',
    })
    await deleteFile(file.id)
    if (fileStore.selectedFile?.id === file.id) {
      fileStore.selectFile(null)
    }
    ElMessage.success('已删除')
    await refreshAll()
  } catch {
    return
  }
}

async function confirmDeleteTreeNode(node: { id: number; label: string }) {
  try {
    await ElMessageBox.confirm(`确认删除目录 ${node.label} 吗？`, '删除确认', {
      type: 'warning',
    })
    await deleteFile(node.id)
    ElMessage.success('目录已删除')
    await refreshAll()
  } catch {
    return
  }
}

function handleRowClick(row: FileItem) {
  fileStore.selectFile(row)
}

async function handleRowDoubleClick(row: FileItem) {
  if (row.isDirectory) {
    await fileStore.openFileDirectory(row)
  } else {
    handleViewFile(row)
  }
}

async function handleTreeSelect(payload: { id: number; name: string }) {
  await fileStore.openDirectory(payload)
}

async function handleViewFile(row: FileItem) {
  if (row.isDirectory) {
    await fileStore.openFileDirectory(row)
  } else {
    try {
      const blob = await downloadFile(row.id)
      const mime = (blob.type || '').toLowerCase()
      let url: string

      if (isTextFile(row)) {
        // Text files: fix charset and open in new tab for inline viewing
        const text = await blob.text()
        const fixedBlob = new Blob([text], { type: `${mime.split(';')[0] || 'text/plain'};charset=utf-8` })
        url = window.URL.createObjectURL(fixedBlob)
        window.open(url, '_blank')
      } else if (isImageFile(mime)) {
        // Images: open as blob (browser will render inline)
        url = window.URL.createObjectURL(blob)
        window.open(url, '_blank')
      } else {
        // Binary or unknown: download instead of viewing
        const a = document.createElement('a')
        a.href = window.URL.createObjectURL(blob)
        a.download = row.fileName
        document.body.appendChild(a)
        a.click()
        document.body.removeChild(a)
        ElMessage.info('非文本/图片文件，已触发下载')
        return
      }
    } catch (e: any) {
      const detail = e?.response?.data?.message || e?.response?.data?.detail || ''
      ElMessage.error(detail || '文件无法查看')
    }
  }
}

async function handleDownloadFile(row: FileItem) {
  if (row.isDirectory) return
  try {
    const blob = await downloadFile(row.id)
    const url = window.URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = row.fileName
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    window.URL.revokeObjectURL(url)
  } catch (e: any) {
    const detail = e?.response?.data?.message || e?.response?.data?.detail || ''
    ElMessage.error(detail || '文件下载失败')
  }
}

async function handleEditFile(row: FileItem) {
  if (row.isDirectory) return
  if (!isTextFile(row)) {
    ElMessage.warning('该文件类型不支持在线编辑，请下载后使用本地编辑器')
    return
  }
  dialogs.edit.fileId = row.id
  dialogs.edit.fileName = row.fileName
  dialogs.edit.content = ''
  dialogs.edit.loading = true
  dialogs.edit.visible = true
  try {
    dialogs.edit.content = await getFileTextContent(row.id)
  } catch (e: any) {
    const detail = e?.response?.data?.message || e?.response?.data?.detail || e?.message || ''
    ElMessage.error(detail || '文件内容加载失败')
    dialogs.edit.visible = false
  } finally {
    dialogs.edit.loading = false
  }
}

async function submitEdit() {
  if (!dialogs.edit.content.trim() && dialogs.edit.content.length === 0) {
    ElMessage.warning('文件内容不能为空')
    return
  }
  dialogs.edit.saving = true
  try {
    await updateFileTextContent(dialogs.edit.fileId, dialogs.edit.content)
    dialogs.edit.visible = false
    ElMessage.success('文件已保存')
    await refreshAll()
  } catch {
    ElMessage.error('保存失败')
  } finally {
    dialogs.edit.saving = false
  }
}

function triggerFileUpload() {
  fileInputRef.value?.click()
}

async function handleFileInputChange(e: Event) {
  const input = e.target as HTMLInputElement
  const file = input.files?.[0]
  if (!file) return

  let newFile: any
  try {
    const res: any = await uploadFile(file, fileStore.currentParentId)
    newFile = res.data || res
    ElMessage.success('文件上传成功')
  } catch {
    ElMessage.error('上传失败')
    input.value = ''
    await refreshAll()
    return
  }

  // Reset input so the same file can be re-uploaded
  input.value = ''
  await refreshAll()

  // Open permission dialog for the newly uploaded file
  if (newFile && newFile.id) {
    dialogs.permission.fileId = newFile.id
    dialogs.permission.fileName = newFile.fileName || newFile.file_name
    dialogs.permission.visible = true
  }
}

onMounted(async () => {
  await fileStore.resetToRoot()
})
</script>

<style scoped>
.file-page {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.empty-wrap {
  min-height: 360px;
  display: grid;
  place-items: center;
}

.page-hero {
  display: flex;
  justify-content: space-between;
  gap: 24px;
  padding: 28px 32px;
  border-radius: 24px;
  background:
    radial-gradient(circle at top right, rgba(197, 145, 56, 0.16), transparent 28%),
    linear-gradient(135deg, #12324b 0%, #204e68 52%, #2f6e86 100%);
  color: #f5f7fa;
}

.eyebrow {
  margin: 0 0 8px;
  font-size: 12px;
  letter-spacing: 0.14em;
  text-transform: uppercase;
  color: rgba(255, 222, 173, 0.84);
}

.page-hero h1 {
  margin: 0;
  font-size: 34px;
}

.hero-copy {
  margin: 10px 0 0;
  max-width: 560px;
  line-height: 1.7;
  color: rgba(245, 247, 250, 0.8);
}

.hero-actions {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  flex-wrap: wrap;
}

.content-grid {
  display: grid;
  grid-template-columns: minmax(260px, 300px) minmax(0, 1fr);
  gap: 20px;
}

.sidebar-card,
.breadcrumb-card,
.table-card {
  border-radius: 20px;
}

.main-column {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.breadcrumb-bar,
.table-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 16px;
}

.table-header h2 {
  margin: 0;
  font-size: 18px;
}

.table-header p {
  margin: 6px 0 0;
  color: #7c8b99;
}

.action-tags,
.table-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.name-cell {
  display: inline-flex;
  align-items: center;
  gap: 10px;
  cursor: pointer;
}

.file-name-text {
  text-decoration: none;
  transition: text-decoration 0.15s;
}

.name-cell:hover .file-name-text {
  text-decoration: underline;
}

.edit-dialog-header {
  display: flex;
  align-items: center;
  gap: 12px;
}
.edit-file-name {
  font-size: 14px;
  font-weight: 400;
  color: #7c8b99;
}
.edit-textarea-wrap {
  min-height: 360px;
}
.edit-textarea :deep(textarea) {
  font-family: 'Cascadia Code', 'Fira Code', 'JetBrains Mono', 'Consolas', monospace;
  font-size: 13px;
  line-height: 1.6;
  tab-size: 2;
}

@media (max-width: 1080px) {
  .page-hero,
  .breadcrumb-bar,
  .table-header {
    flex-direction: column;
  }

  .content-grid {
    grid-template-columns: 1fr;
  }
}
</style>

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
              <el-tag type="info">当前目录 ID: {{ fileStore.currentParentId }}</el-tag>
            </div>
          </el-card>

          <el-card class="table-card" shadow="never">
            <template #header>
              <div class="table-header">
                <div>
                  <h2>目录内容</h2>
                  <p>双击目录进入，单击选中项目后执行操作。</p>
                </div>
                <div class="action-tags">
                  <el-tag v-if="userStore.hasPermission('doc:create')" effect="plain">创建</el-tag>
                  <el-tag v-if="userStore.hasPermission('doc:update')" effect="plain">编辑</el-tag>
                  <el-tag v-if="userStore.hasPermission('doc:delete')" effect="plain">删除</el-tag>
                  <el-tag v-if="userStore.hasPermission('doc:review')" effect="plain">审阅</el-tag>
                  <el-tag v-if="userStore.hasPermission('doc:approve')" effect="plain">审批</el-tag>
                  <el-tag v-if="userStore.hasPermission('doc:share')" effect="plain">共享</el-tag>
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

              <el-table-column label="类型" min-width="140">
                <template #default="{ row }">
                  {{ row.isDirectory ? '目录' : row.mimeType || '文件' }}
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
                      v-if="userStore.hasPermission('doc:update')"
                      link
                      @click.stop="openRenameDialog({ id: row.id, label: row.fileName })"
                    >
                      重命名
                    </el-button>
                    <el-button
                      v-if="userStore.hasPermission('doc:share')"
                      link
                      @click.stop="openActionDialog('share', row)"
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

    <el-dialog v-model="dialogs.action.visible" :title="actionDialogTitle" width="500px">
      <template v-if="dialogs.action.mode === 'share'">
        <el-form label-position="top">
          <el-form-item label="用户 ID 列表">
            <el-input v-model="dialogs.action.userIdsText" placeholder="例如：1,2,3" />
          </el-form-item>
          <el-form-item label="角色 ID 列表">
            <el-input v-model="dialogs.action.roleIdsText" placeholder="例如：4,5" />
          </el-form-item>
        </el-form>
      </template>
      <template v-else>
        <el-form label-position="top">
          <el-form-item label="说明">
            <el-input
              v-model="dialogs.action.content"
              type="textarea"
              :rows="4"
              :placeholder="dialogs.action.mode === 'comment' ? '请输入评论内容' : '请输入处理说明'"
            />
          </el-form-item>
        </el-form>
      </template>
      <template #footer>
        <el-button @click="dialogs.action.visible = false">取消</el-button>
        <el-button type="primary" @click="submitAction">提交</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Document, Folder } from '@element-plus/icons-vue'
import FileTree from '@/components/FileTree.vue'
import {
  approveFile,
  commentFile,
  createDirectory,
  deleteFile,
  downloadFile,
  renameFile,
  reviewFile,
  shareFile,
  uploadFile,
  type FileItem,
} from '@/api/file'
import { useFileStore } from '@/store/file'
import { useUserStore } from '@/store/user'
import { formatBytes, formatDateTime } from '@/utils/format'

type ActionMode = 'share' | 'review' | 'approve' | 'comment'

const fileStore = useFileStore()
const userStore = useUserStore()
const fileTreeRef = ref<InstanceType<typeof FileTree> | null>(null)
const fileInputRef = ref<HTMLInputElement | null>(null)

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
  action: {
    visible: false,
    mode: 'share' as ActionMode,
    file: null as FileItem | null,
    content: '',
    userIdsText: '',
    roleIdsText: '',
  },
})

const actionDialogTitle = computed(() => {
  switch (dialogs.action.mode) {
    case 'share':
      return '共享文件'
    case 'review':
      return '提交审阅'
    case 'approve':
      return '审批文件'
    case 'comment':
      return '添加评论'
  }
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

  await createDirectory(name, dialogs.create.parentId)
  dialogs.create.visible = false
  dialogs.create.name = ''
  ElMessage.success('目录已创建')

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

function openActionDialog(mode: ActionMode, file: FileItem) {
  dialogs.action.visible = true
  dialogs.action.mode = mode
  dialogs.action.file = file
  dialogs.action.content = ''
  dialogs.action.userIdsText = ''
  dialogs.action.roleIdsText = ''
}

function parseNumberList(text: string): number[] {
  return text
    .split(',')
    .map((item) => Number(item.trim()))
    .filter((item) => Number.isInteger(item) && item > 0)
}

async function submitAction() {
  if (!dialogs.action.file) return

  if (dialogs.action.mode === 'share') {
    await shareFile(dialogs.action.file.id, {
      userIds: parseNumberList(dialogs.action.userIdsText),
      roleIds: parseNumberList(dialogs.action.roleIdsText),
    })
  } else if (dialogs.action.mode === 'review') {
    await reviewFile(dialogs.action.file.id, dialogs.action.content)
  } else if (dialogs.action.mode === 'approve') {
    await approveFile(dialogs.action.file.id, dialogs.action.content)
  } else {
    await commentFile(dialogs.action.file.id, dialogs.action.content)
  }

  dialogs.action.visible = false
  ElMessage.success('操作已提交')
  await refreshAll()
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
      let url: string
      // Fix charset for text files to prevent garbled Chinese
      const mime = blob.type || ''
      if (/^text\//.test(mime)) {
        const text = await blob.text()
        const fixedBlob = new Blob([text], { type: `${mime.split(';')[0]};charset=utf-8` })
        url = window.URL.createObjectURL(fixedBlob)
      } else {
        url = window.URL.createObjectURL(blob)
      }
      window.open(url, '_blank')
    } catch (e: any) {
      const detail = e?.response?.data?.message || e?.response?.data?.detail || ''
      ElMessage.error(detail || '文件无法查看')
    }
  }
}

function triggerFileUpload() {
  fileInputRef.value?.click()
}

async function handleFileInputChange(e: Event) {
  const input = e.target as HTMLInputElement
  const file = input.files?.[0]
  if (!file) return

  try {
    await uploadFile(file, fileStore.currentParentId)
    ElMessage.success('文件上传成功')
  } catch {
    ElMessage.error('上传失败')
  }

  // Reset input so the same file can be re-uploaded
  input.value = ''

  await refreshAll()
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

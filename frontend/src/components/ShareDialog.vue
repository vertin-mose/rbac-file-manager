<template>
  <el-dialog
    :model-value="visible"
    :title="`共享设置 — ${fileName}`"
    width="500px"
    @close="$emit('close')"
  >
    <!-- Current user's own permissions -->
    <div class="share-section">
      <h4>我的权限</h4>
      <p class="my-perms">
        你对此文件拥有：
        <el-tag v-for="p in myPermissions" :key="p" size="small" effect="plain">
          {{ permLabel(p) }}
        </el-tag>
        <span v-if="myPermissions.length === 0">暂无权限</span>
      </p>
    </div>

    <el-divider />

    <!-- Users who already have access -->
    <div class="share-section">
      <h4>已共享用户</h4>
      <div v-if="sharedUsers.length > 0" class="shared-user-list">
        <el-tag
          v-for="u in sharedUsers"
          :key="u.userId"
          closable
          :disable-transitions="true"
          @close="handleRemoveUser(u)"
        >
          {{ u.username }}
        </el-tag>
      </div>
      <el-empty v-else description="暂无已共享的用户" :image-size="36" />
    </div>

    <el-divider />

    <!-- Share form -->
    <div class="share-section">
      <h4>添加共享</h4>
      <el-form label-position="top" @submit.prevent>
        <el-form-item label="选择用户">
          <el-select v-model="form.userIds" multiple filterable style="width: 100%" placeholder="请选择用户">
            <el-option v-for="u in availableUsers" :key="u.id" :label="u.username" :value="u.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="权限类型">
          <el-select v-model="form.permissionType" style="width: 100%">
            <el-option label="查看" value="read" />
            <el-option label="编辑" value="write" />
            <el-option label="删除" value="delete" />
          </el-select>
        </el-form-item>
        <el-button type="primary" @click="handleShare" :disabled="form.userIds.length === 0" :loading="sharing">
          共享
        </el-button>
      </el-form>
    </div>

    <template #footer>
      <el-button @click="$emit('close')">关闭</el-button>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { computed, reactive, ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { getFilePermissions, shareFile, type FilePermissionItem } from '@/api/file'
import { listUsers, type UserBasic } from '@/api/role'
import { useUserStore } from '@/store/user'

const userStore = useUserStore()

const props = defineProps<{
  visible: boolean
  fileId: number
  fileName: string
}>()

const emit = defineEmits<{
  (e: 'close'): void
  (e: 'updated'): void
}>()

const sharing = ref(false)
const permissions = ref<FilePermissionItem[]>([])
const allUsers = ref<UserBasic[]>([])

const form = reactive({
  userIds: [] as number[],
  permissionType: 'read',
})

function permLabel(type: string): string {
  const map: Record<string, string> = { read: '查看', write: '编辑', delete: '删除' }
  return map[type] || type
}

/** Current user's own permissions on this file */
const myPermissions = computed(() => {
  return permissions.value
    .filter((p) => p.userId === userStore.userId && p.username === userStore.username)
    .map((p) => p.permissionType)
})

/** Users who already have been shared access (deduplicated) */
const sharedUsers = computed(() => {
  const seen = new Set<number>()
  return permissions.value
    .filter((p) => p.userId != null && p.userId !== userStore.userId)
    .filter((p) => {
      if (seen.has(p.userId!)) return false
      seen.add(p.userId!)
      return true
    })
    .map((p) => ({ userId: p.userId!, username: p.username || '未知' }))
})

/** Users not yet shared */
const availableUsers = computed(() => {
  const sharedIds = new Set(sharedUsers.value.map((u) => u.userId))
  sharedIds.add(userStore.userId)
  return allUsers.value.filter((u) => !sharedIds.has(u.id))
})

async function loadPermissions() {
  try {
    permissions.value = await getFilePermissions(props.fileId)
  } catch {
    // ignore
  }
}

async function loadUsers() {
  try {
    allUsers.value = await listUsers()
  } catch {
    // ignore
  }
}

async function handleShare() {
  if (form.userIds.length === 0) return
  sharing.value = true
  try {
    const res: any = await shareFile(props.fileId, {
      userIds: form.userIds,
      permissionType: form.permissionType,
    })
    const data = res.data || res
    const granted = data?.granted || []
    const skipped = data?.skipped || []

    if (granted.length > 0) {
      ElMessage.success('共享成功')
      emit('updated')
    }
    if (skipped.length > 0) {
      const names = skipped
        .map((id: number) => allUsers.value.find((u) => u.id === id)?.username || `ID:${id}`)
        .join('、')
      ElMessage.warning(`该用户已拥有该权限：${names}`)
    }

    form.userIds = []
    form.permissionType = 'read'
    await loadPermissions()
  } catch {
    ElMessage.error('共享失败')
  } finally {
    sharing.value = false
  }
}

async function handleRemoveUser(user: { userId: number; username: string }) {
  // Find all permission records for this user on this file
  const userPerms = permissions.value.filter((p) => p.userId === user.userId)
  for (const perm of userPerms) {
    try {
      const { deleteFilePermission } = await import('@/api/file')
      await deleteFilePermission(props.fileId, perm.id)
    } catch {
      // ignore
    }
  }
  ElMessage.success(`已取消 ${user.username} 的共享`)
  await loadPermissions()
  emit('updated')
}

watch(
  () => props.visible,
  (val) => {
    if (val) {
      loadPermissions()
      loadUsers()
      form.userIds = []
      form.permissionType = 'read'
    }
  },
)
</script>

<style scoped>
.share-section h4 {
  margin: 0 0 10px;
  font-size: 14px;
  color: #303133;
}

.my-perms {
  margin: 0;
  font-size: 13px;
  color: #606266;
  display: flex;
  align-items: center;
  gap: 6px;
  flex-wrap: wrap;
}

.shared-user-list {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}
</style>

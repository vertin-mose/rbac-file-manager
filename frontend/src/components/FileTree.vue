<template>
  <div class="tree-panel">
    <div class="tree-panel__header">
      <div>
        <h3>目录树</h3>
        <p>点击目录快速跳转</p>
      </div>
      <el-button v-if="canCreate" link type="primary" @click="$emit('create-root')">
        新建根目录
      </el-button>
    </div>

    <div class="tree-root" @click="selectRoot">
      <el-icon><FolderOpened /></el-icon>
      <span>全部文件</span>
    </div>

    <el-tree
      :data="treeData"
      node-key="id"
      empty-text="暂无目录"
      :expand-on-click-node="false"
      default-expand-all
      @node-click="handleNodeClick"
    >
      <template #default="{ data }">
        <div class="tree-node">
          <span class="tree-node__label">
            <el-icon><Folder /></el-icon>
            {{ data.label }}
          </span>
          <span class="tree-node__actions">
            <el-button v-if="canCreate" link size="small" @click.stop="$emit('create-child', data)">
              新建
            </el-button>
            <el-button v-if="canUpdate" link size="small" @click.stop="$emit('rename', data)">
              重命名
            </el-button>
            <el-button v-if="canDelete" link size="small" type="danger" @click.stop="$emit('delete', data)">
              删除
            </el-button>
          </span>
        </div>
      </template>
    </el-tree>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { Folder, FolderOpened } from '@element-plus/icons-vue'
import { getFiles, type FileItem } from '@/api/file'

interface TreeNode {
  id: number
  label: string
  parentId: number
  children?: TreeNode[]
}

const props = defineProps<{
  canCreate: boolean
  canUpdate: boolean
  canDelete: boolean
}>()

const emit = defineEmits<{
  (event: 'select', payload: { id: number; name: string; path?: { id: number; name: string }[] }): void
  (event: 'create-root'): void
  (event: 'create-child', payload: { id: number; label: string; parentId: number }): void
  (event: 'rename', payload: { id: number; label: string; parentId: number }): void
  (event: 'delete', payload: { id: number; label: string; parentId: number }): void
}>()

const directories = ref<FileItem[]>([])

const treeData = computed(() => buildTree(directories.value))

async function loadTree() {
  const allDirectories: FileItem[] = []

  async function collect(parentId: number) {
    const files = await getFiles(parentId)
    const dirs = files.filter((item) => item.isDirectory)
    allDirectories.push(...dirs)
    for (const dir of dirs) {
      await collect(dir.id)
    }
  }

  await collect(0)
  directories.value = allDirectories
}

function buildTree(items: FileItem[]): TreeNode[] {
  const map = new Map<number, TreeNode>()
  const roots: TreeNode[] = []

  items.forEach((item) => {
    map.set(item.id, {
      id: item.id,
      label: item.fileName,
      parentId: item.parentId ?? 0,
      children: [],
    })
  })

  map.forEach((node) => {
    if (node.parentId === 0) {
      roots.push(node)
      return
    }
    const parent = map.get(node.parentId)
    if (parent) {
      parent.children = parent.children || []
      parent.children.push(node)
    } else {
      roots.push(node)
    }
  })

  return roots
}

function buildAncestorPath(nodeId: number): { id: number; name: string }[] {
  const path: { id: number; name: string }[] = []
  let current = nodeId
  while (current !== 0) {
    const dir = directories.value.find(d => d.id === current)
    if (!dir) break
    path.unshift({ id: dir.id, name: dir.fileName })
    current = dir.parentId ?? 0
  }
  return [{ id: 0, name: 'Root' }, ...path]
}

function handleNodeClick(node: TreeNode) {
  const path = buildAncestorPath(node.id)
  emit('select', { id: node.id, name: node.label, path })
}

function selectRoot() {
  emit('select', { id: 0, name: '全部文件', path: [{ id: 0, name: 'Root' }] })
}

defineExpose({ reload: loadTree })

onMounted(loadTree)
</script>

<style scoped>
.tree-panel {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.tree-panel__header {
  display: flex;
  justify-content: space-between;
  gap: 12px;
}

.tree-panel__header h3 {
  margin: 0;
  font-size: 16px;
  color: #213547;
}

.tree-panel__header p {
  margin: 4px 0 0;
  color: #7c8b99;
  font-size: 13px;
}

.tree-root {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 12px;
  border-radius: 8px;
  background: #f6f9fb;
  cursor: pointer;
  color: #28445c;
}

.tree-node {
  width: 100%;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.tree-node__label {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  min-width: 0;
}

.tree-node__actions {
  display: inline-flex;
  align-items: center;
  gap: 4px;
}
</style>

# 文件级用户权限管理功能

## 概述

本次改动为 RBAC 文档管理系统新增了**文件级用户权限管理**功能，实现了「管理员为具体用户配置具体文件的 read/write/delete 权限」的能力。

### 核心设计

- **两层权限模型**：全局角色权限（角色管理页）+ 文件级用户权限（文件权限页）
- **文件权限优先**：文件级权限可以覆盖全局角色权限。例如 VIEWER 角色全局只有 `doc:read`，但管理员可以给某个 VIEWER 用户单独授予某文件的 write/delete 权限
- **目录权限继承**：给目录设置权限后，其所有子文件和子目录自动继承该权限
- **权限只管用户**：文件权限仅按用户维度配置，角色维度的权限管理保留在角色管理页面

---

## 改动文件清单

| 文件 | 操作 | 说明 |
|------|------|------|
| `database/seed.sql` | 修改 | 新增 `file:permission:manage` 权限，分配给 ADMIN 角色 |
| `backend/services.py` | 修改 | 新增文件权限检查、目录继承、权限 CRUD 函数；文件操作接口加入权限校验 |
| `backend/main.py` | 修改 | 新增 3 个文件权限 API；文件操作路由改为文件级权限控制 |
| `frontend/src/components/FilePermissionDialog.vue` | **新建** | 文件权限管理对话框组件 |
| `frontend/src/api/file.ts` | 修改 | 新增文件权限相关 API 函数和类型定义 |
| `frontend/src/api/role.ts` | 修改 | 新增 `listUsers()` 用户列表 API |
| `frontend/src/constants/permissions.ts` | 修改 | 新增 `file:permission:manage` 权限常量 |
| `frontend/src/views/file/FileManager.vue` | 修改 | 集成权限管理按钮；移除全局权限对文件操作的限制 |
| `frontend/tsconfig.json` | 修改 | 修复 TypeScript 废弃警告 |

---

## 架构设计

### 权限控制流程

```
用户请求文件操作
       │
       ▼
  是否 ADMIN/SUPER_ADMIN？ ──是──▶ 放行
       │否
       ▼
  是否文件所有者？ ──是──▶ 放行
       │否
       ▼
  file_permissions 表中是否有
  该用户对该文件（或父目录）的
  对应权限？ ──是──▶ 放行
       │否
       ▼
    返回 403
```

### 目录继承机制

```
目录 A （用户 X 有 read 权限）
├── 文件 A1  ← 用户 X 可见（继承自目录 A）
├── 文件 A2  ← 用户 X 可见（继承自目录 A）
└── 子目录 B ← 用户 X 可见（继承自目录 A）
    └── 文件 B1  ← 用户 X 可见（继承自目录 A）
```

权限检查沿目录树向上查找：文件 → 父目录 → 祖父目录 → ...，直到找到匹配的权限记录或到达根目录。

### 两层权限关系

| 层级 | 管理位置 | 作用 | 示例 |
|------|---------|------|------|
| 全局角色权限 | 角色管理页面 | 控制用户能做哪些类型的操作 | VIEWER 有 `doc:read`，能调用文件列表 API |
| 文件级用户权限 | 文件权限按钮 | 控制用户能操作哪些具体文件 | 管理员给用户 X 授予文件 Y 的 write 权限 |

**文件级权限可以超越全局权限**：即使 VIEWER 全局没有 `doc:update`，管理员给某 VIEWER 用户授予某文件的 write 权限后，该用户可以重命名该文件。

---

## 新增 API

### 1. 获取文件权限列表

```
GET /api/files/{file_id}/permissions
```

**权限要求**：`doc:read`

**响应示例**：
```json
{
  "code": 200,
  "data": [
    {
      "id": 1,
      "file_id": 5,
      "role_id": null,
      "role_name": null,
      "user_id": 3,
      "username": "user111",
      "permission_type": "read",
      "granted_at": "2026-06-01T12:00:00"
    }
  ]
}
```

### 2. 批量设置文件权限

```
PUT /api/files/{file_id}/permissions
```

**权限要求**：`file:permission:manage`

**请求体**：
```json
{
  "permissions": [
    { "user_id": 3, "permission_type": "read" },
    { "user_id": 3, "permission_type": "write" },
    { "user_id": 3, "permission_type": "delete" }
  ]
}
```

**说明**：此接口会替换该文件的所有现有权限，调用时需传入完整的权限列表。

### 3. 删除单条权限

```
DELETE /api/files/{file_id}/permissions/{perm_id}
```

**权限要求**：`file:permission:manage`

### 4. 用户列表

```
GET /api/users
```

**权限要求**：`user:read`

**响应示例**：
```json
{
  "code": 200,
  "data": [
    { "id": 1, "username": "admin", "display_name": "System Administrator", "email": "admin@example.com" },
    { "id": 3, "username": "user111", "display_name": null, "email": null }
  ]
}
```

---

## 修改的 API 行为

以下 API 的权限检查逻辑已从「全局角色权限」改为「文件级用户权限」：

| API | 原逻辑 | 新逻辑 |
|-----|--------|--------|
| `GET /api/files/{id}` | 需要全局 `doc:read` | 检查用户是否有该文件的 read 权限 |
| `GET /api/files/{id}/download` | 需要全局 `doc:read` | 检查用户是否有该文件的 read 权限 |
| `PUT /api/files/{id}` (重命名) | 需要全局 `doc:update` | 检查用户是否有该文件的 write 权限 |
| `DELETE /api/files/{id}` | 需要全局 `doc:delete` | 检查用户是否有该文件的 delete 权限 |
| `POST /api/files` (上传) | 需要全局 `doc:create` | 检查用户是否有父目录的 write 权限 |
| `POST /api/files/directory` | 需要全局 `doc:create` | 检查用户是否有父目录的 write 权限 |
| `GET /api/files` (列表) | 需要全局 `doc:read` | 只显示用户拥有 read 权限的文件（ADMIN 除外） |

---

## 前端组件

### FilePermissionDialog

路径：`frontend/src/components/FilePermissionDialog.vue`

功能：
- 显示当前文件已配置的用户权限列表（用户名 + 权限类型 + 授予时间）
- 支持按用户添加权限（下拉选择用户，勾选 read/write/delete）
- 支持删除已有权限
- 所有登录用户可见共享按钮，ADMIN 及以上可见权限管理按钮

### FileManager 改动

- 文件操作按钮（查看/重命名/删除/审阅/审批/评论）对所有登录用户显示，不再受全局权限控制
- 「共享」按钮直接打开权限管理对话框
- 「权限」按钮仅对有 `file:permission:manage` 权限的用户显示（ADMIN 及以上）

---

## 数据库

### 权限表新增记录

```sql
INSERT INTO permissions (name, description, category) VALUES
('file:permission:manage', 'Manage file role permissions', 'file');
```

### ADMIN 角色权限映射

```sql
INSERT INTO role_permissions (role_id, permission_id)
SELECT r.id, p.id FROM roles r, permissions p
WHERE r.name = 'ADMIN' AND p.name = 'file:permission:manage';
```

由于 SUPER_ADMIN 继承 ADMIN，此权限对 SUPER_ADMIN 同样生效。

### file_permissions 表结构（已有，无需修改）

| 字段 | 类型 | 说明 |
|------|------|------|
| id | BIGINT | 主键 |
| file_id | BIGINT | 关联文件 ID |
| user_id | BIGINT | 关联用户 ID（本次仅使用此字段） |
| role_id | BIGINT | 关联角色 ID（保留，本次不使用） |
| permission_type | VARCHAR(20) | 权限类型：read / write / delete |
| granted_at | DATETIME | 授予时间 |

---

## 使用说明

### 管理员操作流程

1. 使用 admin 账号登录
2. 进入「文件管理」页面
3. 点击某个文件/目录操作列中的「权限」按钮
4. 在弹窗中选择用户，勾选权限类型（查看/编辑/删除），点击「添加」
5. 已有权限可在列表中删除

### 测试场景

| 场景 | 操作 | 预期结果 |
|------|------|---------|
| VIEWER 无权限 | VIEWER 登录查看文件列表 | 看不到任何文件（除非被授权） |
| 管理员授权 read | admin 给 VIEWER 授予文件 A 的 read | VIEWER 能看到文件 A，能下载 |
| 管理员授权 write | admin 给 VIEWER 授予文件 A 的 write | VIEWER 能重命名文件 A |
| 管理员授权 delete | admin 给 VIEWER 授予文件 A 的 delete | VIEWER 能删除文件 A |
| 目录继承 | admin 给 VIEWER 授予目录 D 的 read | VIEWER 能看到目录 D 下所有文件 |
| 文件所有者 | 用户自己上传的文件 | 始终可见，无需额外授权 |
| ADMIN 不受限 | ADMIN 登录 | 始终能看到所有文件 |

### Docker 重建

修改代码后需要重建 Docker 容器：

```bash
sudo docker-compose up --build -d
```

如果是已有数据库（非首次启动），需要手动插入新权限：

```bash
sudo docker exec -i rbac-mysql mysql -urbac_user -prbac_pass rbac_file_manager -e "
INSERT INTO permissions (name, description, category) VALUES ('file:permission:manage', 'Manage file role permissions', 'file');
INSERT INTO role_permissions (role_id, permission_id) SELECT r.id, p.id FROM roles r, permissions p WHERE r.name = 'ADMIN' AND p.name = 'file:permission:manage';
"
```

或者完全重置数据库（会清空数据）：

```bash
sudo docker-compose down -v
sudo docker-compose up --build -d
```

# 审计日志功能优化记录

## 后端改动

### 补充审计覆盖
- 新增 `REGISTER`、`CREATE_ROLE`、`UPDATE_ROLE` 操作的审计记录

### 详情中文化
所有操作详情改为中文，如 `用户admin已登录`、`删除了文件report.docx`、`为角色MANAGER分配了权限: audit:read, doc:read`

### 名称替代 ID
| 操作 | 优化后示例 |
|---|---|
| DELETE_ROLE | 删除了角色 ADMIN |
| ASSIGN_PERMISSIONS | 为角色 MANAGER 分配了权限: audit:read |
| ASSIGN_USER_ROLES | 为用户 zhangsan 分配了角色: EDITOR |
| RENAME_FILE | 重命名文件 report.docx 为 report_v2.docx |
| DELETE_FILE | 删除了目录 项目文档 |
| SHARE / REVIEW / APPROVE / COMMENT | 共享/审阅/批准/评论了文件 report.docx |

### 筛选增强
- 用户筛选改为按用户名模糊匹配
- 日期范围筛选移至后端 SQL 层，修复分页不准问题
- 导出接口支持按当前筛选条件导出

### 删除功能
- `DELETE /api/audit-logs/{log_id}` — 单条软删除
- `DELETE /api/audit-logs` — 批量软删除（接收 `{"ids": [...]}`）

## 前端改动

| 功能 | 说明 |
|---|---|
| 详情直接显示 | 移除点击"查看详情"按钮和 popover，内容直接展示 |
| 序号列 | ID 列改为连续序号 `(页码-1)×每页条数+行号+1` |
| 操作类型中文化 | 下拉筛选和表格列均显示中文（登录、上传文件、删除角色等） |
| 批量删除 | 表格支持多选，选中后出现红色提示条和批量删除按钮，带二次确认 |
| 导出筛选 | 导出 CSV 时自动应用当前筛选条件 |

## 涉及文件

| 文件 | 改动 |
|---|---|
| `backend/main.py` | 新增/修改 API 路由与 audit record 调用 |
| `backend/services.py` | 审计查询、导出、删除函数优化 |
| `frontend/src/views/audit/AuditLogView.vue` | 页面完整重构 |
| `frontend/src/api/audit.ts` | 新增批量删除、导出参数支持 |

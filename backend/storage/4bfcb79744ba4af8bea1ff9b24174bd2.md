# 前端更新说明

## 概述

当前结果：

- README 中标记为未完成的前端页面已经补齐
- 前端请求参数与后端返回字段已经完成对齐
- 前端构建校验已通过

---

## 本次新增或补齐的功能

### 1. 认证相关

- 重做了登录页的界面和交互流程
- 新增注册页，路径为 `/register`
- 新增路由控制，未登录用户可访问登录/注册页
- 保留并兼容原有基于 Token 的登录状态管理

涉及文件：

- `frontend/src/views/login/LoginView.vue`
- `frontend/src/views/login/RegisterView.vue`
- `frontend/src/router/index.ts`
- `frontend/src/api/auth.ts`

### 2. 文件管理

- 实现了可用的文件管理页面
- 新增目录树浏览
- 新增面包屑导航
- 新增文件列表展示
- 新增创建目录流程
- 新增文件上传流程
- 新增重命名流程
- 新增删除流程
- 新增基于权限的按钮显示控制
- 新增共享、审阅、审批、评论等操作弹窗

涉及文件：

- `frontend/src/views/file/FileManager.vue`
- `frontend/src/components/FileTree.vue`
- `frontend/src/store/file.ts`
- `frontend/src/api/file.ts`

### 3. 角色管理

- 实现了角色列表展示
- 新增角色创建/编辑界面
- 新增权限矩阵选择界面
- 新增权限分配流程
- 新增角色层级关系展示
- 新增按用户 ID 分配角色的功能

涉及文件：

- `frontend/src/views/role/RoleManagement.vue`
- `frontend/src/api/role.ts`
- `frontend/src/constants/permissions.ts`

### 4. 审计日志

- 实现了审计日志表格
- 新增分页功能
- 新增操作类型筛选
- 新增用户 ID 筛选
- 新增 CSV 导出
- 新增前端本地日期范围筛选

涉及文件：

- `frontend/src/views/audit/AuditLogView.vue`
- `frontend/src/api/audit.ts`

### 5. 布局与仪表盘

- 重做了主应用布局
- 清理了原有乱码界面文案
- 优化了头部角色标签展示
- 将仪表盘改造成可用的总览页面
- 新增权限与角色摘要展示

涉及文件：

- `frontend/src/components/AppLayout.vue`
- `frontend/src/views/dashboard/DashboardView.vue`
- `frontend/src/store/user.ts`

### 6. 前端公共能力

- 新增统一的日期格式化工具
- 新增统一的文件大小格式化工具
- 改进了请求错误处理逻辑
- 统一了前后端字段映射方式

涉及文件：

- `frontend/src/utils/format.ts`
- `frontend/src/api/request.ts`

---

## 一并包含的后端兼容修复

为了让补齐后的前端流程能够真实可用，本次也包含了一项后端兼容修复：

- 修正了多个文件相关接口中的异步认证/权限校验调用方式

涉及后端文件：

- `backend/main.py`

如果没有这项修复，前端中的创建目录、重命名、删除、共享、审阅、审批、评论等文件操作在运行时可能失败。

---

## 验证方式

前端已通过以下命令验证：

```bash
cd frontend
npm install
npm run build
```

验证结果：

- 生产构建通过

---

## 当前仍存在的限制

以下限制仍然存在，原因是当前后端能力或接口设计尚未覆盖：

- 审计日志的日期范围筛选目前只在前端本地生效
  - 当前后端审计接口只支持 `action` 和 `userId`，不支持日期范围参数
- 用户角色分配目前需要手动输入用户 ID
  - 当前后端没有提供可直接供前端使用的用户列表接口

---

## 对 README 状态描述的建议更新

如果后续要更新主 README，那么旧的状态描述：

> 前端仅登录页可用

建议改为能够反映当前实现状态的描述。*** End Patch

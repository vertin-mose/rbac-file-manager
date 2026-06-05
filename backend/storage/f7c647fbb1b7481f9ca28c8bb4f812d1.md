# RBAC Document Management System

基于 **RBAC** 模型的企业文档管理与协同办公系统，支持文档的创建、编辑、评审、审批全流程，实现精细化的角色权限控制和操作审计。

---

## 目录

- [项目概述](#项目概述)
- [需求分析](#需求分析)
- [系统架构](#系统架构)
- [技术栈](#技术栈)
- [文件组织](#文件组织)
- [RBAC 角色设计](#rbac-角色设计)
- [角色层级关系](#角色层级关系)
- [权限矩阵](#权限矩阵)
- [快速开始](#快速开始)
- [实现状态](#实现状态)
- [API 文档](#api-文档)
- [开发指南](#开发指南)

---

## 项目概述

本系统是软件安全课程的实践项目，定位为**文档管理与协同办公系统**，核心功能包括：

- **文档全生命周期管理**：创建、编辑、更新、评审、审批、归档
- **RBAC 角色权限模型**：6 角色层级化权限控制，支持角色继承
- **协同办公**：文档评论、审阅建议、审批流程
- **文件版本管理**：文件更新覆盖功能，保留历史审阅/审批/评论记录
- **用户管理**：管理员创建用户、启用/禁用、删除账号
- **安全审计**：记录所有用户操作，支持审计日志查询和导出
- **容器化部署**：使用 Docker Compose 一键启动全套服务

> ⚠️ **当前项目状态：后端全部完成、前端全部页面已实现、数据库就绪、集成测试就绪**
> 详细进展按「后端 / 前端 / 数据库 / 测试」四部分组织在下方 [实现状态](#实现状态) 中。

---

## 需求分析

### 1. 系统总体目标

构建一个安全、可扩展的企业级文档管理与协同办公平台，实现以下目标：

- **文档集中化管理**：提供统一的文档存储、组织和检索平台
- **精细化权限控制**：基于 RBAC-1 模型，实现角色继承和细粒度权限管理
- **协同工作流**：支持文档评审、审批等协作流程
- **完整审计追踪**：记录所有用户操作，满足合规审计需求
- **多环境部署**：同时支持本地开发模式和 Docker 容器化部署

### 2. 功能需求

#### 2.1 用户认证模块

| 功能 | 描述 | 优先级 |
|------|------|--------|
| 用户登录 | 用户名 + 密码登录，返回 JWT Token | 必须 |
| 用户注册 | 新用户自助注册，默认分配基础角色 | 必须 |
| Token 刷新 | JWT 无状态认证，24 小时过期 | 必须 |
| 登出记录 | 记录登出操作至审计日志 | 建议 |

#### 2.2 文档管理模块

| 功能 | 描述 | 优先级 |
|------|------|--------|
| 目录浏览 | 树形目录结构，支持无限层级嵌套 | 必须 |
| 文件上传/下载 | 支持大文件上传，MinIO 对象存储 | 必须 |
| 文件操作 | 重命名、移动、删除（含批量） | 必须 |
| 文件共享 | 按用户或角色共享文档访问权限 | 建议 |
| 文档审阅 | 提交审阅、添加审阅意见、批准/驳回 | 建议 |
| 文档评论 | 在文档上添加评论和批注 | 建议 |
| 全文检索 | 按文件名、类型、上传者搜索文档 | 建议 |
| 文件导出 | 导出文档为 PDF 或其他格式 | 建议 |

#### 2.3 角色权限模块

| 功能 | 描述 | 优先级 |
|------|------|--------|
| 角色 CRUD | 创建、查看、编辑、删除角色 | 必须 |
| 权限分配 | 为角色分配/撤销权限 | 必须 |
| 角色层级 | 配置角色继承关系（上级角色继承下级权限） | 必须 |
| 用户-角色分配 | 为用户分配一个或多个角色 | 必须 |
| 角色可视化 | 树形展示角色层级继承关系 | 建议 |

#### 2.4 审计日志模块

| 功能 | 描述 | 优先级 |
|------|------|--------|
| 日志记录 | 自动记录用户操作（登录、文件操作、权限变更等） | 必须 |
| 日志查询 | 分页查询，支持按操作类型、用户、时间范围筛选 | 必须 |
| 日志导出 | 导出审计日志为 CSV 格式 | 必须 |

### 3. 非功能需求

| 类别 | 要求 | 说明 |
|------|------|------|
| **安全性** | 密码加密 | 使用 BCrypt 哈希存储密码 |
| | 无状态认证 | JWT Token，不依赖服务端 Session |
| | 权限检查 | 每个 API 端点均需进行 RBAC 权限验证 |
| | CORS 防护 | 配置跨域白名单 |
| | SQL 注入防护 | 使用 ORM 参数化查询 |
| **性能** | 并发支持 | 后端应支持 >100 并发请求 |
| | 分页查询 | 所有列表接口支持分页 |
| **可用性** | 前端响应式 | 适配桌面端主流分辨率 |
| | 错误处理 | 统一错误响应格式（ApiResponse） |
| **可维护性** | 代码规范 | Python PEP8 + Vue 3 Composition API |
| | 文档完备 | API 文档自动生成（OpenAPI/Swagger） |
| **部署** | 容器化 | Docker Compose 编排全部服务 |
| | 环境分离 | `.env.local` / `.env.docker` 环境隔离 |

### 4. 角色需求

系统需要满足 6 种角色的权责分离要求，覆盖从系统运维到外部访客的完整权限层次：

| 角色 | 需求描述 |
|------|---------|
| 超级管理员 | 最高权限，管理系统配置、安全策略和系统备份 |
| 系统管理员 | 负责用户管理、角色分配、审计日志导出 |
| 部门经理 | 管理部门文档审批，查看团队审计日志 |
| 文档编辑员 | 创建、编辑、共享文档，参与讨论 |
| 文档审核员 | 审阅文档、添加批注，与编辑员形成职责分离 |
| 外部访客 | 仅可浏览和检索已授权的文档 |

### 5. 技术需求

| 类别 | 技术选型 | 说明 |
|------|----------|------|
| 后端框架 | Python FastAPI | 高性能异步 Web 框架 |
| 数据库 | MySQL 8.0 | 关系型数据持久化 |
| 缓存 | Redis 7 | 可选，用于性能优化 |
| 对象存储 | MinIO | S3 兼容的文件存储 |
| 前端框架 | Vue 3 + TypeScript | 现代 SPA 应用 |
| UI 库 | Element Plus | 企业级 UI 组件库 |
| 部署 | Docker Compose | 一键容器化部署 |

---

## 系统架构

```
┌──────────────────────────────────────────────────────┐
│                    Frontend (Vue 3)                    │
│         Element Plus UI + Pinia State + Router         │
└──────────────────┬───────────────────────────────────┘
                   │ HTTP / REST API
                   │ JWT Authentication
┌──────────────────▼───────────────────────────────────┐
│               Backend (Python FastAPI)                 │
│                                                        │
│  main.py — 全部路由（22 个 API 端点）                    │
│  auth.py — JWT + 密码 + 认证依赖                        │
│  services.py — 业务逻辑（RBAC、文件、审计）              │
│  models.py — 数据表映射 + 请求/响应模型                  │
│  config.py — 环境变量配置                               │
│  ┌──────────────────────────────────────────────┐     │
│  │           Data Layer (SQLAlchemy)             │     │
│  └────────────┬──────────────────┬───────────────┘     │
└─────────────────┼──────────────────┼────────────────────┘
                  │                  │
         ┌────────▼──────┐   ┌──────▼────────┐
         │   MySQL 8.0   │   │    Redis 7     │
         │               │   │   (不必须)     │
         └───────────────┘   └───────────────┘

         ┌─────────────────────────────────────┐
         │       MinIO (Object Storage)         │
         │     S3-compatible file storage       │
         └─────────────────────────────────────┘
```

### 架构组件说明

| 架构层次 | 组件 | 功能说明 |
|---------|------|---------|
| **前端架构** | Vue 3 SPA | 单页应用，前端路由由 Vue Router 管理，页面切换无刷新。所有组件使用 Composition API + `<script setup>` 语法，TypeScript 类型约束 |
| | Pinia 状态管理 | 集中管理用户认证状态（Token、角色、权限）、文件浏览状态。状态数据同步持久化到 localStorage |
| | Element Plus UI | 企业级组件库，提供表格、表单、菜单、弹窗、标签等开箱即用的 UI 组件 |
| | Axios HTTP 客户端 | 统一封装 HTTP 请求，自动附加 JWT Token，统一处理 401/403/500 等错误响应 |
| **后端架构** | FastAPI 路由层 | 处理 HTTP 请求路由，通过 Depends 依赖注入实现权限检查，自动生成 OpenAPI/Swagger 文档 |
| | Service 业务层 | 封装全部业务逻辑，包括认证（登录/注册）、角色 CRUD、文件操作、审计日志 |
| | SQLAlchemy ORM | 对象关系映射，将数据库表映射为 Python 对象。所有 SQL 通过 ORM 执行，天然防 SQL 注入 |
| | RBAC 权限引擎 | 核心在 `get_effective_permissions()` 函数中递归解析角色继承链，收集自身+继承所有权限的并集 |
| | JWT 认证中间件 | 使用 HS256 算法签名的 JSON Web Token，无状态认证，包含用户 ID、用户名、角色列表 |
| **存储架构** | MySQL 关系数据库 | 存储用户、角色、权限、文件记录、审计日志等结构化数据 |
| | MinIO 对象存储 | 文件内容以 S3 兼容方式存储，数据库仅存文件元数据和 MinIO 对象路径 |
| | Redis 缓存 | 可选组件，可用于缓存权限数据提升响应速度 |
| **部署架构** | Docker Compose | 编排 MySQL + Redis + MinIO + 后端 + 前端 共 5 个服务，通过 bridge 网络互联 |
| | Nginx 反向代理 | 前端容器内 Nginx 提供静态文件服务 + API 反向代理到后端 |

### 核心流程

1. **认证流程**：用户登录 → 后端验证凭据 → 返回 JWT Token（含角色和权限信息）→ 前端存储 Token 和权限列表
2. **授权流程**：请求携带 Token → 后端解析 → `require_perm()` 权限检查 → 角色层级递归解析 → 放行或 403
3. **文档操作流程**：用户操作文档 → RBAC 权限检查（含层级继承）→ MinIO 存储操作 → 记录审计日志
4. **数据流**：前端 <-> REST API <-> services.py <-> SQLAlchemy <-> MySQL

---

## 技术栈

### 后端

| 组件 | 技术 | 说明 |
|------|------|------|
| 框架 | FastAPI | 现代化高性能 Python Web 框架 |
| ORM | SQLAlchemy 2.0 | 数据库操作 |
| JWT | PyJWT | JSON Web Token |
| 密码 | bcrypt | 密码哈希 |
| 存储 | MinIO (boto3) | S3 兼容对象存储 |
| 运行 | Uvicorn | ASGI 服务器，支持热重载 |

### 前端

| 组件 | 技术 | 说明 |
|------|------|------|
| 框架 | Vue 3 | 渐进式前端框架 |
| 语言 | TypeScript | 类型安全 |
| UI 库 | Element Plus | 企业级组件库 |
| 状态管理 | Pinia | Vue 3 官方状态管理 |
| 路由 | Vue Router 4 | 前端路由 |
| HTTP | Axios | HTTP 客户端 |
| 构建 | Vite | 现代化构建工具 |
| 图标 | Element Plus Icons | SVG 图标库 |

### DevOps

| 组件 | 技术 | 说明 |
|------|------|------|
| 容器化 | Docker + Docker Compose | 多服务编排 |
| 数据库 | MySQL 8.0 | 关系型数据库 |
| 对象存储 | MinIO | S3 兼容文件存储 |
| 缓存 | Redis 7 | 缓存、可选 |
| 反向代理 | Nginx | 前端静态服务 + API 代理 |

---

## 文件组织

```
rbac-file-manager/
│
├── backend/                         # Python FastAPI 后端
│   ├── main.py                      # 应用入口：FastAPI 初始化、CORS、22 条 API 路由、权限检查依赖
│   ├── models.py                    # 数据模型：9 个 SQLAlchemy ORM 模型（User、Role、Permission 等）
│   │                                # + Pydantic 请求/响应数据模型（LoginRequest、RoleOut 等）
│   ├── auth.py                      # 认证模块：JWT Token 签发/验证、BCrypt 密码哈希、get_current_user 依赖
│   ├── services.py                  # 业务逻辑层：认证（login/register）、角色 CRUD、层级权限递归解析
│   │                                # （get_effective_permissions）、文件操作、审计日志记录/查询/导出
│   ├── config.py                    # 环境配置：从 .env 读取 DB/JWT/MinIO/Redis 配置参数
│   ├── requirements.txt             # Python 依赖清单
│   ├── Dockerfile                   # Python 容器镜像构建
│   ├── .env.local                   # 本地开发环境变量模板（DB_HOST=localhost）
│   └── .env.docker                  # Docker 部署环境变量模板（DB_HOST=mysql）
│
├── frontend/                        # Vue 3 + TypeScript 前端
│   ├── src/
│   │   ├── main.ts                  # 应用入口：注册 Element Plus + 图标库 + Pinia + Router
│   │   ├── App.vue                  # 根组件
│   │   ├── env.d.ts                 # TypeScript 类型声明
│   │   ├── api/                     # Axios API 封装层
│   │   │   ├── request.ts           # HTTP 客户端：JWT Token 自动附加、401/403 错误统一处理
│   │   │   ├── auth.ts              # 认证 API：login / register / logout 接口及类型定义
│   │   │   ├── role.ts              # 角色管理 API：角色 CRUD 及权限分配接口
│   │   │   ├── file.ts              # 文件管理 API：文件列表/上传/创建目录/重命名/删除接口
│   │   │   └── audit.ts             # 审计日志 API：日志查询（分页+筛选）及 CSV 导出接口
│   │   ├── store/                   # Pinia 状态管理
│   │   │   ├── user.ts              # 用户状态：Token、用户名、角色列表、权限列表、角色信息（含等级）
│   │   │   │                        # + hasRole/hasPermission/highestLevel 计算属性
│   │   │   └── file.ts              # 文件状态：当前目录、文件列表、面包屑
│   │   ├── router/
│   │   │   └── index.ts             # 路由配置：登录页 + 仪表盘/文件/角色/审计/系统配置 5 个子路由
│   │   │                            # + 导航守卫（未登录自动跳转登录页）
│   │   ├── components/
│   │   │   ├── AppLayout.vue        # 主布局：左侧角色菜单（按角色动态显示栏目）
│   │   │   │                        # + 顶部导航栏（显示用户名 + 角色身份标签）
│   │   │   ├── FileTree.vue         # 文件目录树组件（递归展开、点击跳转、内联操作）
│   │   │   ├── FilePermissionDialog.vue # 文件权限管理弹窗（角色优先+用户分配）
│   │   │   ├── ShareDialog.vue      # 文件共享弹窗（添加/查看共享用户）
│   │   │   └── FileActivityDialog.vue # 文件审阅/审批/评论弹窗（含历史记录+提交表单）
│   │   └── views/                   # 页面视图
│   │       ├── login/
│   │       │   └── LoginView.vue    # 登录页：用户名/密码表单 + 登录按钮 + 错误提示
│   │       ├── dashboard/
│   │       │   └── DashboardView.vue # 总体数据：文件总数、用户数、角色数、存储用量概览卡片
│   │       ├── file/
│   │       │   └── FileManager.vue  # 文件管理器：目录树 + 文件列表（含角色权限标签提示）
│   │       ├── role/
│   │       │   └── RoleManagement.vue # 角色管理：角色 CRUD 表格（占位）
│   │       ├── audit/
│   │       │   └── AuditLogView.vue # 审计日志：分页表格 + 筛选（占位）
│   │       └── system/
│   │           └── SystemConfigView.vue # 系统配置：系统信息/备份/安全策略（仅 SUPER_ADMIN 可见）
│   ├── nginx.conf                   # Nginx 配置：静态文件服务 + /api/ 反向代理到后端
│   ├── Dockerfile                   # 前端容器构建：Node 构建 → Nginx 运行（多阶段构建）
│   └── package.json                 # Node.js 依赖配置
│
├── database/                        # 数据库脚本
│   ├── init.sql                     # 建表语句：8 张核心表 + 1 张关联表 DDL
│   │                                # users、roles、permissions、user_roles、role_permissions
│   │                                # role_hierarchy、file_records、file_permissions、audit_logs
│   └── seed.sql                     # 种子数据：6 角色 + 角色层级关系 + 22 条权限 + 默认管理员
│                                    # + 角色-权限映射 + 根目录
│
├── docker-compose.yml               # 容器编排：5 个服务（MySQL + Redis + MinIO + Backend + Frontend）
├── .env                             # 当前环境变量（通过 cp 切换）
├── .gitignore                       # Git 忽略规则
└── README.md
```

---

## RBAC 角色设计

### 角色总览（6 角色）

系统采用 **企业文档管理与协同办公** 角色体系，6 个角色分为 5 个层级，实现权责分离：

| 级别 | 角色 | 中文名称 | 层级等级 | 定位 | 前端可见栏目 | 典型用户 |
|------|------|---------|---------|------|-------------|---------|
| **L1** | SUPER_ADMIN | 超级管理员 | 最高 | 系统运维人员，拥有全部权限，包括系统配置与安全策略管理 | 总体数据 + 文件管理 + 角色管理 + 审计日志 + **系统配置** | 系统管理员 |
| **L2** | ADMIN | 系统管理员 | 高 | 组织管理者，负责用户管理、角色分配、审计导出与系统备份 | 总体数据 + 文件管理 + 角色管理 + 审计日志 | IT 运维人员 |
| **L3** | MANAGER | 部门经理 | 中高 | 部门文档管理者，可审批/删除文档，查看审计日志 | 总体数据 + 文件管理 + 审计日志 | 部门负责人 |
| **L4** | EDITOR | 文档编辑员 | 中 | 文档内容创作者，创建、更新、共享文档，参与评论 | 总体数据 + 文件管理（新建/编辑按钮） | 普通员工 |
| **L4** | REVIEWER | 文档审核员 | 中 | 文档质量把控者，审阅文档、添加评论和批注 | 总体数据 + 文件管理（审核/评论按钮） | 质量/合规人员 |
| **L5** | VIEWER | 外部访客 | 基础 | 只读用户，查看和下载文档，无任何操作按钮 | 总体数据 + 文件管理（仅查看，无操作按钮） | 外部访客/实习生 |

> **职责分离原则**：EDITOR 和 REVIEWER 处于同一层级（L4），但权限互不重叠。EDITOR 拥有创建/更新/共享/评论权限，REVIEWER 拥有审阅/评论权限，EDITOR 不能自审，REVIEWER 不能编辑。MANAGER（L3）继承两者权限，可在必要时覆盖操作。

### 前端角色展示

用户在登录后，顶部导航栏右侧会以彩色标签形式显示其角色身份：

| 角色级别 | 标签颜色 | 显示内容 |
|---------|---------|---------|
| L1–L2（SUPER_ADMIN / ADMIN） | 红色 danger | "超级管理员" / "系统管理员" |
| L3（MANAGER） | 橙色 warning | "部门经理" |
| L4（EDITOR / REVIEWER） | 蓝色 primary | "文档编辑员" / "文档审核员" |
| L5（VIEWER） | 灰色 info | "外部访客" |

侧边栏菜单和页面内操作按钮根据用户 `hasPermission()` 状态动态显示/隐藏。

---

## 角色层级关系

本系统采用 **RBAC 层级模型（RBAC-1）**，即高级角色自动继承低级角色的所有权限。层级关系使用 `role_hierarchy` 表存储，在运行时由 `services.py` 的 `get_effective_permissions()` 递归解析。

```
                        ┌─────────────────┐
                        │   SUPER_ADMIN    │  ← 继承 ADMIN 的全部权限 + system:config
                        └────────┬────────┘
                                 │ inherits
                        ┌────────▼────────┐
                        │     ADMIN       │  ← 继承 MANAGER 的全部权限 + user/role 管理 + audit 导出 + system:backup
                        └────────┬────────┘
                                 │ inherits
                        ┌────────▼────────┐
                        │    MANAGER      │  ← 继承 EDITOR + REVIEWER 的全部权限 + doc:delete/approve
                        └──┬──────────┬──┘
                           │          │ inherits
              ┌────────────▼──┐    ┌──▼────────────┐
              │    EDITOR     │    │   REVIEWER     │
              │  (L4, 内容创建)│    │  (L4, 质量审核) │
              │               │    │                │
              │ 创建、编辑文档 │    │ 审阅、批注文档  │
              │ 共享、评论文档 │    │ 建议修改       │
              └───────┬───────┘    └───────┬────────┘
                      │                    │ inherits
                      └────────┬───────────┘
                               │
                      ┌────────▼────────┐
                      │     VIEWER      │  ← 基础权限：查看、搜索、下载
                      └─────────────────┘
```

> **关键设计**：EDITOR 和 REVIEWER 处于同一层级（L4），共同继承 VIEWER（L5）。这种设计确保编辑与审核职责分离——EDITOR 无法审核自己的文档，REVIEWER 无法编辑文档内容。MANAGER 作为 L3 角色同时继承两者，可在必要时执行完整的文档管理操作。

---

## 权限矩阵

| 权限 \\ 角色 | VIEWER | REVIEWER | EDITOR | MANAGER | ADMIN | SUPER_ADMIN |
|-------------|--------|----------|--------|---------|-------|-------------|
| **doc:read** | ✓ | ✓(inherit) | ✓(inherit) | ✓(inherit) | ✓(inherit) | ✓(inherit) |
| **doc:export** | ✓ | ✓(inherit) | ✓(inherit) | ✓(inherit) | ✓(inherit) | ✓(inherit) |
| **file:permission:manage** | | | | | ✓ | ✓(inherit) |
| **doc:review** | | ✓ | | ✓(inherit) | ✓(inherit) | ✓(inherit) |
| **doc:comment** | | ✓ | ✓ | ✓(inherit) | ✓(inherit) | ✓(inherit) |
| **doc:create** | | | ✓ | ✓(inherit) | ✓(inherit) | ✓(inherit) |
| **doc:update** | | | ✓ | ✓(inherit) | ✓(inherit) | ✓(inherit) |
| **doc:share** | | | ✓ | ✓(inherit) | ✓(inherit) | ✓(inherit) |
| **doc:delete** | | | | ✓ | ✓(inherit) | ✓(inherit) |
| **doc:approve** | | | | ✓ | ✓(inherit) | ✓(inherit) |
| **user:read** | | | | ✓ | ✓(inherit) | ✓(inherit) |
| **role:read** | | | | ✓ | ✓(inherit) | ✓(inherit) |
| **audit:read** | | | | ✓ | ✓(inherit) | ✓(inherit) |
| **user:create** | | | | | ✓ | ✓(inherit) |
| **user:update** | | | | | ✓ | ✓(inherit) |
| **user:delete** | | | | | ✓ | ✓(inherit) |
| **role:create** | | | | | ✓ | ✓(inherit) |
| **role:update** | | | | | ✓ | ✓(inherit) |
| **role:delete** | | | | | ✓ | ✓(inherit) |
| **role:assign** | | | | | ✓ | ✓(inherit) |
| **audit:export** | | | | | ✓ | ✓(inherit) |
| **system:backup** | | | | | ✓ | ✓(inherit) |
| **system:config** | | | | | | ✓ |

> **EDITOR 与 REVIEWER 区别**：EDITOR 拥有 `doc:create/update/share/comment`（不含 `doc:review`），REVIEWER 拥有 `doc:review/comment`（不含编辑权限）。这是企业文档管理中编辑与审核分离的典型要求。
>
> **显示名称说明**：前端显示的权限中文名称与实际功能对应——"更新文档"对应重命名和更新内容、"启用用户"对应启用/禁用账号、"下载文档"对应文件下载。`system:config`（配置系统）和 `system:backup`（备份系统）为预留权限，后端暂未实现对应 API。

---

## 快速开始

> ⚠️ **如果你是从零开始配置**，建议按 **方式一（本地开发）** 先调试代码，再转 **方式二（Docker 部署）**。
> 如果你是 Windows 用户，所有命令可在 **Git Bash**、**VS Code 终端** 或 **PyCharm 终端** 中执行。

---

### 下载代码

#### 方式 A：从 GitHub 克隆

```bash
# 克隆仓库
git clone https://github.com/YOUR_USERNAME/rbac-file-manager.git

# 进入项目目录
cd rbac-file-manager
```

#### 方式 B：从 Docker 下载镜像

```bash
# 1. 从 Docker Hub 拉取镜像（假设已发布）
docker pull yourusername/rbac-file-manager:latest

# 2. 创建项目目录和配置文件
mkdir rbac-file-manager
cd rbac-file-manager

# 3. 下载 docker-compose.yml 和数据库脚本
# （从项目仓库或文档中获取以下文件）
# - docker-compose.yml
# - database/init.sql
# - database/seed.sql
# - backend/.env.docker
```

> 实际部署时推荐使用方式 A（Git 克隆），以便获取完整的项目代码和文档。

---

### 方式一：本地开发模式

先在本机运行后端和前端，修改代码即时生效，适合日常开发调试。

#### 第一步：安装必需软件

```bash
# 检查 Python（需要 3.12+）
python --version

# 检查 Node.js（需要 20+）
node --version
npm --version

# 检查 Git
git --version
```

- Python 下载：https://www.python.org/downloads/（安装时勾选 **Add Python to PATH**）
- Node.js 下载：https://nodejs.org/（选择 LTS 版本）
- Git 下载：https://git-scm.com/download/win

#### 第二步：配置 MySQL 数据库

确保本机 MySQL 已运行（端口 3306），然后创建数据库和导入表结构：

```bash
# 登录 MySQL（-p 后会提示输入你的 MySQL root 密码）
mysql -u root -p

# 在 MySQL 中执行以下命令
CREATE DATABASE IF NOT EXISTS rbac_file_manager DEFAULT CHARACTER SET utf8mb4;
CREATE USER IF NOT EXISTS 'rbac_user'@'localhost' IDENTIFIED BY 'rbac_pass';
GRANT ALL PRIVILEGES ON rbac_file_manager.* TO 'rbac_user'@'localhost';
FLUSH PRIVILEGES;
USE rbac_file_manager;
SOURCE database/init.sql;
SOURCE database/seed.sql;
exit
```

#### 第三步：安装后端 Python 依赖

```bash
# 进入后端目录
cd backend

# 创建虚拟环境
python -m venv venv

# 激活虚拟环境
# Windows（Git Bash）:
source venv/Scripts/activate
# Windows（CMD/PowerShell）:
# venv\Scripts\activate

# 安装依赖
pip install -r requirements.txt
```

#### 第四步：配置环境变量

本地开发和 Docker 部署使用不同的 `.env` 文件，通过复制切换：

```bash
# 本地开发 → 复制 .env.local
cp backend/.env.local .env

# Docker 部署 → 复制 .env.docker（见方式二）
# cp backend/.env.docker .env
```

`.env.local` 内容说明：

```
DB_HOST=localhost            # 本地 MySQL
DB_USERNAME=rbac_user
DB_PASSWORD=rbac_pass
DB_NAME=rbac_file_manager
JWT_SECRET=...               # JWT 密钥
# MinIO 可选，不配不影响登录/角色/审计
```

#### 第五步：启动后端

```bash
# 确保在 backend 目录，且虚拟环境已激活
source venv/Scripts/activate

# 启动后端（热重载模式，修改代码自动重启）
python main.py

# 看到以下输出即成功:
# Uvicorn running on http://0.0.0.0:8080
```

#### 第六步：新开终端，启动前端

```bash
cd frontend
npm install
npm run dev

# 看到以下输出即成功:
# Local: http://localhost:5173
```

#### 验证

| 检查项 | 地址 | 预期结果 |
|--------|------|---------|
| 后端 API | http://localhost:8080 | 返回 `{"status":"ok"}` |
| API 文档 | http://localhost:8080/docs | Swagger 页面 |
| 前端界面 | http://localhost:5173 | 登录页面 |

**默认管理员账号：** `admin` / `admin123`

> 本模式下 MinIO 可选。如需文件上传功能，单独启动 MinIO 容器：
> ```bash
> docker run -d -p 9000:9000 -p 9001:9001 --name rbac-minio-lite minio/minio server /data --console-address ":9001"
> ```

---

### 方式二：Docker 部署模式

代码在本地调试通过后，用 Docker 一键部署所有服务（MySQL + Redis + MinIO + 后端 + 前端）。

#### 第一步：安装 Docker Desktop

```bash
# 检查是否已安装
docker --version
docker compose version
```

如果未安装：

1. 访问 https://www.docker.com/products/docker-desktop/ 下载 Docker Desktop
2. 选择 **Windows** 版本下载
3. 运行安装程序，**务必勾选 "Use WSL 2 instead of Hyper-V"**（推荐）
4. 安装完成后**重启电脑**
5. 启动 Docker Desktop，等待右下角图标变为绿色（Running）

> ⚠️ **常见问题**：
> - Windows 需要开启 **WSL 2**，安装时按提示操作即可
> - 提示 "WSL 2 installation is incomplete" → 管理员 PowerShell 运行 `wsl --update`
> - Docker 一直卡在 "starting" → 重启电脑
> - 如果提示 "Hardware assisted virtualization and data execution protection must be enabled" → 进入 BIOS 开启 Intel VT-x / AMD-V

#### 第二步：从 Docker Hub 拉取镜像（如已发布）

```bash
# 拉取所有服务镜像
docker compose pull

# 或单独拉取
docker pull mysql:8.0
docker pull redis:7-alpine
docker pull minio/minio
```

#### 第三步：切换环境变量并启动

```bash
# 1. 切换到 Docker 环境变量
cp backend/.env.docker .env

# 2. 停止本机 MySQL（释放 3306 端口/可能需要管理员身份）
net stop MySQL

# 3. 启动全部服务（首次启动会自动拉取镜像，约 5-15 分钟）
docker compose up -d --build

# 4. 查看启动状态
docker compose ps
```

所有服务状态为 `healthy` 即部署成功。

#### 验证

| 服务 | 地址 | 说明 |
|------|------|------|
| 前端界面 | http://localhost | Nginx 反向代理 |
| 后端 API | http://localhost:8080 | 返回 `{"status":"ok"}` |
| API 文档 | http://localhost:8080/docs | Swagger 页面 |
| MinIO 管理 | http://localhost:9001 | 凭据 `minioadmin` / `minioadmin` |

---

### 上传到 Git（GitHub）

```bash
# 1. 初始化仓库（如尚未初始化）
cd rbac-file-manager
git init

# 2. 添加所有文件并提交
git add .
git commit -m "init: RBAC Document Management System"

# 3. 在 https://github.com/new 创建新仓库（不勾选 README/.gitignore）

# 4. 关联远程仓库（替换 YOUR_USERNAME）
git remote add origin https://github.com/YOUR_USERNAME/rbac-file-manager.git

# 5. 推送到 GitHub
git push -u origin main
```

> 如果默认分支是 `master`：`git branch -M main && git push -u origin main`

---

### 发布到 GitHub Container Registry (ghcr.io)

GitHub Container Registry 与 GitHub 账号绑定，无需 Docker Hub 登录，团队成员可直接拉取使用。

#### 第一步：创建 GitHub Personal Access Token

1. 登录 GitHub → Settings → Developer settings → Personal access tokens → Fine-grained tokens（或 Tokens (classic)）
2. 点击 **Generate new token**
3. Token 权限（classic）：勾选 `write:packages`、`read:packages`、`delete:packages`
4. 生成后复制保存（只显示一次）

```bash
# 将 token 和用户名写入 .env 文件（该文件已在 .gitignore 中，不会提交）
echo 'GITHUB_USERNAME=你的GitHub用户名' >> .env
echo 'GITHUB_TOKEN=ghp_xxxxxxxxxxxxxxxxxxxx' >> .env
```

> ⚠️ 也可以写在 `backend/.env.docker` 中（已内置 `GITHUB_USERNAME` 和 `GITHUB_TOKEN` 字段），但注意不要将 token 提交到 Git。

#### 第二步：登录 ghcr.io 并推送镜像

```bash
# 1. 登录 GitHub Container Registry
echo $GITHUB_TOKEN | docker login ghcr.io -u $GITHUB_USERNAME --password-stdin

# 2. 构建镜像
docker compose build

# 3. 给镜像打标签（ghcr.io 格式）
docker tag rbac-file-manager-backend ghcr.io/${GITHUB_USERNAME}/rbac-file-manager-backend:latest
docker tag rbac-file-manager-frontend ghcr.io/${GITHUB_USERNAME}/rbac-file-manager-frontend:latest

# 4. 推送到 ghcr.io
docker push ghcr.io/${GITHUB_USERNAME}/rbac-file-manager-backend:latest
docker push ghcr.io/${GITHUB_USERNAME}/rbac-file-manager-frontend:latest
```

#### 第三步：将 GitHub Package 设为公开（首次需要）

推送成功后，默认权限为 **Private**，团队成员无法拉取。需手动设为 Public：

1. 打开 `https://github.com/YOUR_USERNAME?tab=packages`
2. 点击 `rbac-file-manager-backend` → Package settings → Danger Zone → Change visibility → **Public**
3. 对 `rbac-file-manager-frontend` 同样操作

> 设为 Public 后，任何人无需认证即可拉取（`docker pull` 不需要 token）。

#### 第四步：其他成员拉取运行

```bash
# 1. 克隆代码
git clone https://github.com/YOUR_USERNAME/rbac-file-manager.git
cd rbac-file-manager

# 2. 配置环境变量（不需要 GITHUB_TOKEN 即可拉取公开镜像）
cp backend/.env.docker .env
# 编辑 .env，修改 GITHUB_USERNAME 为发布者的 GitHub 用户名

# 3. 拉取镜像并启动
docker compose -f docker-compose.yml -f docker-compose.prod.yml pull
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d

# 4. 验证服务
docker compose ps
```

#### 镜像更新流程

```bash
# 1. 重新构建镜像
docker compose build

# 2. 登录 ghcr.io（如已登录可跳过）
echo $GITHUB_TOKEN | docker login ghcr.io -u $GITHUB_USERNAME --password-stdin

# 3. 推送更新
docker tag rbac-file-manager-backend ghcr.io/${GITHUB_USERNAME}/rbac-file-manager-backend:latest
docker tag rbac-file-manager-frontend ghcr.io/${GITHUB_USERNAME}/rbac-file-manager-frontend:latest
docker push ghcr.io/${GITHUB_USERNAME}/rbac-file-manager-backend:latest
docker push ghcr.io/${GITHUB_USERNAME}/rbac-file-manager-frontend:latest

# 4. 团队成员拉取更新
# docker compose -f docker-compose.yml -f docker-compose.prod.yml pull
# docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d
```

> **版本标签建议**：除了 `latest`，建议同时推送版本号标签（如 `v1.0.0`），方便回滚：
> ```bash
> docker tag rbac-file-manager-backend ghcr.io/${GITHUB_USERNAME}/rbac-file-manager-backend:v1.0.0
> docker push ghcr.io/${GITHUB_USERNAME}/rbac-file-manager-backend:v1.0.0
> ```
> 其他成员修改 `.env` 中 `IMAGE_TAG=v1.0.0` 即可拉取指定版本。

---

### 常用命令速查

```bash
# === 本地开发 ===
cd backend && source venv/Scripts/activate && python main.py   # 启动后端
cd frontend && npm run dev                                      # 启动前端

# === Docker ===
docker compose up -d --build          # 构建并启动所有服务
docker compose down                   # 停止并删除所有容器
docker compose logs -f backend        # 查看后端实时日志
docker compose ps                     # 查看所有服务状态
docker compose pull                   # 拉取最新镜像

# === Git ===
git clone https://github.com/YOUR_USERNAME/rbac-file-manager.git  # 克隆仓库
git pull origin master                                             # 拉取远程 master 分支更新
git add . && git commit -m "..." && git push origin master         # 提交并推送

# === GitHub Container Registry ===
echo $GITHUB_TOKEN | docker login ghcr.io -u $GITHUB_USERNAME --password-stdin  # 登录 ghcr.io
docker tag rbac-file-manager-backend ghcr.io/${GITHUB_USERNAME}/rbac-file-manager-backend:latest
docker push ghcr.io/${GITHUB_USERNAME}/rbac-file-manager-backend:latest    # 推送后端
docker push ghcr.io/${GITHUB_USERNAME}/rbac-file-manager-frontend:latest   # 推送前端
docker compose -f docker-compose.yml -f docker-compose.prod.yml pull       # 拉取远程镜像
```

---

## 实现状态

> 项目状态：后端 API 全部完成，前端全部页面已实现，数据库就绪，集成测试脚本可用。

---

### 后端 (Backend)

#### 已完成

所有 API 端点已在 `backend/main.py` 中实现，含完整 RBAC 权限检查：

| 模块 | API 端点 | 文件位置 |
|------|----------|----------|
| **认证** | 登录 / 注册 / 登出 / 当前身份 | `backend/main.py` → `services.py` (auth_service) |
| **角色管理** | 角色 CRUD、层级查询、权限分配、用户角色分配 | `backend/main.py` → `services.py` (role_service) |
| **文档管理** | 文档列表/详情/下载、上传、目录创建、重命名、删除、共享、审阅、审批、评论、文件内容更新（覆盖原文件+保留历史活动） | `backend/main.py` → `services.py` (file_service) |
| **审计日志** | 日志查询（分页+筛选）、CSV 导出 | `backend/main.py` → `services.py` (audit_service) |
| **用户信息** | 用户信息查询（按 ID）、用户列表、管理员创建用户、启用/禁用、删除 | `backend/main.py` → `services.py` (role_service) |

其他已完成的组件：
- RBAC 权限核心：`backend/services.py` — `get_effective_permissions()` 递归解析角色层级继承
- JWT 认证：`backend/auth.py` — Token 签发/验证 + BCrypt 密码哈希
- 数据库 ORM 模型：`backend/models.py` — 9 个 SQLAlchemy 模型 + Pydantic 数据模型
- 环境配置：`backend/config.py` — DB/JWT/MinIO/Redis 配置
- 注册默认分配 VIEWER 角色：`services.py` 中 `register()` 函数在创建用户后自动查找并分配 VIEWER
- 文件下载代理：`services.py` 中 `get_file_content()` 从 MinIO 读取文件内容并通过 API 代理返回

#### 待完成

- （无）后端已全部实现，所有接口可直接调用。

---

### 前端 (Frontend)

#### 已完成

| 页面/组件 | 文件位置 | 状态详情 |
|-----------|---------|----------|
| 登录页 | `frontend/src/views/login/LoginView.vue` | 完整实现，支持用户名/密码登录，登录后跳转总体数据；左右分区双栏居中布局 |
| 注册页 | `frontend/src/views/login/RegisterView.vue` | 新用户自助注册，默认分配 VIEWER 角色；左右分区双栏居中布局 |
| 路由守卫 | `frontend/src/router/index.ts` | 已配置路由守卫，未登录自动跳转登录页，含角色级别路由保护 |
| API 请求封装 | `frontend/src/api/request.ts` | Axios 封装，含 JWT Token 自动附加、401/403/500 统一错误处理 |
| 布局组件 | `frontend/src/components/AppLayout.vue` | 侧边栏菜单（按角色动态显示）+ 顶部导航栏（含角色身份标签）；挂载时自动调用 `/api/auth/me` 刷新权限，解决角色变更后权限缓存过期问题 |
| 用户状态管理 | `frontend/src/store/user.ts` | 存储 Token/用户名/角色/权限/角色信息，支持 `hasPermission()` 细粒度权限检查；新增 `refreshPermissions()` 方法从后端实时获取最新权限 |
| 总体数据页 | `frontend/src/views/dashboard/DashboardView.vue` | 四个统计卡片（权限数、角色数、访问层级、文档操作能力）+ 权限概览 + 角色信息（含角色 ID/级别） |
| 系统配置页 | `frontend/src/views/system/SystemConfigView.vue` | 仅 SUPER_ADMIN 可见，展示系统信息/备份/安全策略 |
| **文件管理器** | `frontend/src/views/file/FileManager.vue` | 目录树 + 面包屑导航 + 文件列表 + 文件上传 + 创建目录 + 重命名 + 删除 + 共享/审阅/审批/评论弹窗 + 操作按钮均通过 `hasPermission()` 动态控制显示、文件更新覆盖 + 下载按钮 |
| **目录树组件** | `frontend/src/components/FileTree.vue` | 递归展开全部目录、点击节点跳转、内联新建/重命名/删除操作 |
| **文件权限弹窗** | `frontend/src/components/FilePermissionDialog.vue` | 角色优先选择→用户分配、全部用户角色级权限、上传后自动弹出、仅管理员可二次修改 |
| **共享弹窗** | `frontend/src/components/ShareDialog.vue` | 独立于权限管理、已共享用户标签、添加共享选用户+权限类型 |
| **审阅/审批/评论弹窗** | `frontend/src/components/FileActivityDialog.vue` | 支持三种模式、显示当前版本和历史版本活动记录、审批含通过/驳回单选 |
| **角色管理** | `frontend/src/views/role/RoleManagement.vue` | 角色 CRUD 表格 + 权限矩阵勾选（含继承权限展示）+ L1-L5 层级树形展示 |
| **审计日志查看器** | `frontend/src/views/audit/AuditLogView.vue` | 分页表格 + 操作类型筛选 + 用户 ID 筛选 + 前端日期范围过滤 + CSV 导出 |
| **用户管理** | `frontend/src/views/users/UserManagement.vue` | 用户列表（含角色标签、状态标签）+ 用户名搜索 + 角色筛选 + 创建用户弹窗（含角色选择）+ 启用/禁用切换 + 删除用户 + 保留分配角色功能 |
| 前端公共工具 | `frontend/src/utils/format.ts` | 日期格式化 + 文件大小格式化 |
| 权限常量 | `frontend/src/constants/permissions.ts` | 权限分组定义 |
| 文件查看下载 | `frontend/src/views/file/FileManager.vue` | "查看"按钮（位于重名前）、双击文件直接打开、文件名 hover 下划线效果；通过 JWT 认证的 blob 下载，避免无 token 的 401 错误 |

#### 已知限制

| 问题 | 说明 |
|------|------|
| 审计日志日期范围仅前端过滤 | 后端审计接口仅支持 `action` 和 `userId` 参数，不支持日期范围 |
| 文件查看依赖 MinIO | 文件下载查看功能需要 MinIO 服务可用，否则返回错误 |

### 文件级权限说明

系统有两层权限模型：

1. **RBAC 角色权限** — 控制用户能否执行某种操作（如 `doc:read` 控制能否查看文件）
2. **文件级权限（文件授权）** — 在 RBAC 基础上对特定文件做额外限制

默认情况下（文件未被授权时），用户的 RBAC 权限决定访问权。当管理员通过"文件授权"功能为某个文件设置了权限后，该文件仅对指定用户/角色可见，即使其他用户的角色拥有 `doc:read` 也无法访问。

---

### 数据库 (Database)

#### 已完成

| 文件 | 内容 | 说明 |
|------|------|------|
| `database/init.sql` | 9 张表 DDL | User、Role、Permission、UserRole、RolePermission、RoleHierarchy、FileRecord、FilePermission、AuditLog |
| `database/seed.sql` | 种子数据 | 6 角色（SUPER_ADMIN → VIEWER）、角色层级关系、默认管理员（admin/admin123）、全部 22 条权限记录 |

数据库表结构：

| 表名 | 用途 |
|------|------|
| `users` | 用户表（用户名、密码哈希、显示名、角色关联） |
| `roles` | 角色表（角色名称、描述） |
| `permissions` | 权限表（权限名称、所属分类、描述） |
| `user_roles` | 用户-角色多对多关联 |
| `role_permissions` | 角色-权限多对多关联 |
| `role_hierarchy` | 角色层级继承关系（父角色 → 子角色） |
| `file_records` | 文件记录表（文件名、类型、大小、父目录、上传者、MinIO 路径、审阅状态） |
| `file_permissions` | 文件级权限控制（支持用户级和角色级） |
| `file_activities` | 文件审阅/审批/评论历史记录（按版本区分） |
| `audit_logs` | 审计日志表（操作用户、操作类型、IP、详情、时间） |

#### 待完成

- （无）数据库 DDL 和种子数据已全部就绪，Docker 启动时自动初始化。

---

### 测试 (Testing)

#### 已完成

| 文件 | 内容 | 运行方式 |
|------|------|---------|
| `test_verify.py` | 全流程集成测试脚本 | `python test_verify.py`（需先启动后端） |

测试覆盖范围（6 大模块、20+ 测试点）：
1. **健康检查** — 后端 `/api/health` 端点
2. **认证测试** — 管理员登录、错误密码返回 401、注册新用户、重复注册返回 409
3. **角色测试** — 角色列表（6 个）、角色详情、角色层级、无 Token 访问被拒
4. **文件测试** — 列表、创建目录、重命名、删除、不存在的文件返回 404
5. **审计日志测试** — 分页查询、操作类型验证、CSV 导出
6. **RBAC 继承测试** — 无角色用户访问受限

#### 待完成

- **单元测试**：为 `backend/services.py` 中各 service 函数添加 pytest 单元测试（文件位置：建议新建 `backend/tests/` 目录）
- **API 测试**：使用 FastAPI TestClient 的自动化测试
- **前端测试**：Vue 组件单元测试（Vitest）和 E2E 测试（如适用）

---

## API 文档

所有路由定义在 `backend/main.py` 中，启动后可访问 `http://localhost:8080/docs` 查看交互式 Swagger 文档。

### 认证接口

| 方法 | 路径 | 说明 | 权限 |
|------|------|------|------|
| POST | `/api/auth/login` | 用户登录（返回 Token + 角色信息 + 权限列表） | 公开 |
| POST | `/api/auth/register` | 用户注册 | 公开 |
| POST | `/api/auth/logout` | 登出 | 需认证 |
| GET | `/api/auth/me` | 获取当前用户身份与有效权限（实时查库，不依赖缓存） | 需认证 |

### 角色管理接口

| 方法 | 路径 | 说明 | 最低权限 |
|------|------|------|---------|
| GET | `/api/roles` | 角色列表（含继承权限） | role:read |
| GET | `/api/roles/{id}` | 角色详情 | role:read |
| GET | `/api/roles/hierarchy` | 角色层级关系 | role:read |
| POST | `/api/roles` | 创建角色 | role:create |
| PUT | `/api/roles/{id}` | 更新角色 | role:update |
| DELETE | `/api/roles/{id}` | 删除角色 | role:delete |
| PUT | `/api/roles/{id}/permissions` | 分配权限 | role:update |
| PUT | `/api/users/{id}/roles` | 分配用户角色 | role:assign |

### 文档管理接口

| 方法 | 路径 | 说明 | 最低权限 |
|------|------|------|---------|
| GET | `/api/files?parentId=0` | 文档列表（目录浏览） | doc:read |
| GET | `/api/files/{id}` | 文档详情 | doc:read |
| POST | `/api/files` | 上传文档（multipart） | doc:create |
| POST | `/api/files/directory` | 创建目录 | doc:create |
| PUT | `/api/files/{id}` | 重命名 | doc:update |
| DELETE | `/api/files/{id}` | 删除文档 | doc:delete |
| POST | `/api/files/{id}/share` | 共享文档 | doc:share |
| POST | `/api/files/{id}/review` | 提交审阅 | doc:review |
| POST | `/api/files/{id}/approve` | 审批文档（通过/驳回） | doc:approve |
| POST | `/api/files/{id}/comment` | 添加评论 | doc:comment |
| PUT | `/api/files/{id}/content` | 更新文件内容（覆盖原文件，保留历史活动） | doc:update |
| GET | `/api/files/{id}/activities` | 获取文件审阅/审批/评论活动记录 | doc:read |

### 用户管理接口

| 方法 | 路径 | 说明 | 最低权限 |
|------|------|------|---------|
| GET | `/api/users` | 用户列表 | user:read |
| GET | `/api/users/{id}` | 用户详情（含角色、启用状态） | role:read |
| POST | `/api/users` | 管理员创建用户（含角色选择） | user:create |
| PUT | `/api/users/{id}/roles` | 分配用户角色 | role:assign |
| PUT | `/api/users/{id}/status` | 启用/禁用用户 | user:update |
| DELETE | `/api/users/{id}` | 删除用户（软删除） | user:delete |

### 审计日志接口

| 方法 | 路径 | 说明 | 最低权限 |
|------|------|------|---------|
| GET | `/api/audit-logs` | 日志列表（分页+筛选） | audit:read |
| GET | `/api/audit-logs/export` | 导出 CSV | audit:export |

---

## 开发指南

### 编码规范

- **后端**：Python 3.12+, FastAPI, SQLAlchemy 2.0
- **前端**：Vue 3 Composition API + TypeScript
- **数据库**：表名小写+下划线，字段名小写+下划线
- **API**：RESTful 风格，统一返回 `ApiResponse` 格式（`{code, message, data, timestamp}`）

### 后端权限控制方式

权限检查通过 `require_perm()` 依赖工厂实现：

```python
# main.py 中的例子
@app.get("/api/roles")
def api_list_roles(req, db: Session = Depends(get_db),
                   _=Depends(require_perm("role:read"))):
    return ApiResponse.success(list_roles(db))
```

`require_perm("role:read")` 内部调用 `get_effective_permissions()` 递归解析角色层级，返回该角色及其所有继承角色的权限并集。

### 前端权限控制方式

前端使用 Pinia store 中的 `hasPermission()` 方法进行细粒度权限检查：

```typescript
// 按钮级权限控制
<el-button v-if="userStore.hasPermission('doc:create')">新建目录</el-button>
<el-button v-if="userStore.hasPermission('doc:review')">审核文档</el-button>
```

侧边栏菜单通过 `userStore.highestLevel` 计算属性控制栏目可见性：

```typescript
// 角色管理仅 L1-L2 可见
v-if="userStore.highestLevel <= 2"

// 审计日志仅 L1-L3 可见
v-if="userStore.highestLevel <= 3"

// 系统配置仅 SUPER_ADMIN 可见
v-if="userStore.hasRole('SUPER_ADMIN')"
```

### 本地测试

```bash
# 安装依赖
pip install -r requirements.txt

# 启动（开发模式，热重载）
python main.py

# 访问 API 文档
open http://localhost:8080/docs
```

### Docker 构建

```bash
# 构建并启动所有服务
docker compose up -d --build

# 查看后端日志
docker compose logs -f backend

# 仅重启后端
docker compose restart backend
```

---

## 安全特性

| 特性 | 实现方式 |
|------|----------|
| 密码加密 | BCrypt |
| 认证 | JWT Token（无状态） |
| 授权 | 权限依赖注入 + 角色层级递归解析 |
| CORS 防护 | FastAPI CORSMiddleware 白名单 |
| 审计日志 | services.py 中 record_audit() 函数 |
| XSS 防护 | Element Plus 自动转义 |
| SQL 注入防护 | SQLAlchemy 参数绑定 |
| 角色职责分离 | EDITOR 与 REVIEWER 权限分离，不可相互操作 |

---

## 默认账户

| 用户名 | 密码 | 角色 | 前端可见角色名称 |
|--------|------|------|-----------------|
| admin | admin123 | SUPER_ADMIN | 超级管理员 |

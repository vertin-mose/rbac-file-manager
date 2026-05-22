# RBAC Document Management System — Python FastAPI

## 项目定位
基于 RBAC 模型的企业文档管理与协同办公系统，软件安全课程实践项目。

## 后端技术栈（已从 Java Spring Boot 迁移到 Python FastAPI）
- Python 3.12 + FastAPI + SQLAlchemy 2.0 + PyMySQL
- JWT 认证 (PyJWT) + BCrypt 密码 (passlib)
- MinIO 文件存储 (S3-compatible) / Redis（可选）
- Docker Compose 部署

## 后端文件结构（平铺，无嵌套）
```
backend/
├── main.py          # FastAPI 入口 + 全部 22 条 API 路由
├── models.py        # SQLAlchemy 模型 + Pydantic 请求/响应模型
├── auth.py          # JWT 签发验证 + 密码哈希 + 认证依赖
├── services.py      # 全部业务逻辑（认证、RBAC、文件、审计）
├── config.py        # 环境变量配置
├── requirements.txt
└── Dockerfile
```

## 角色设计（6 角色，层级继承）
SUPER_ADMIN > ADMIN > MANAGER > EDITOR + REVIEWER > VIEWER

- 权限在 `services.py` 的 `get_effective_permissions()` 中递归解析
- 角色层级存储在 `role_hierarchy` 表，继承链在运行时递归收集

## 权限分类
document: create/read/update/delete/review/approve/comment/share/export
user: read/create/update/delete
role: read/create/update/delete/assign
audit: read/export
system: config/backup

## 状态
- **后端**: 全部 22 个 API 端点已实现，含 RBAC 权限检查
- **前端**: Vue 3 框架，所有视图和 API 对接完成
- **数据库**: 建表脚本和种子数据就绪（MySQL，与 Java 版本相同）
- **Docker**: docker-compose.yml 已更新为 Python 后端

## API 文档
启动后端后访问 http://localhost:8080/docs （FastAPI 自动生成 Swagger UI）

## 关键文件位置
- 数据库: `database/init.sql` + `database/seed.sql`
- 后端: `backend/main.py`
- RBAC 核心: `backend/services.py` (get_effective_permissions 递归解析)
- 认证: `backend/auth.py`
- 容器编排: `docker-compose.yml`
- 默认管理员: admin / admin123

## 项目路径
C:\Users\华硕\Desktop\实验\rbac-file-manager\

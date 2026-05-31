-- ========================================
-- RBAC Document Management System - Seed Data
-- 6 Roles (Enterprise Document Management & Collaboration) + Role Hierarchy + Default Admin
-- ========================================

-- === Permissions (Document Management Focus) ===
INSERT INTO permissions (name, description, category) VALUES
-- Document permissions
('doc:create',  'Create new documents and directories',    'document'),
('doc:read',    'View, search and download documents',     'document'),
('doc:update',  'Edit and modify document content',        'document'),
('doc:delete',  'Delete documents and directories',        'document'),
('doc:review',  'Review documents and suggest changes',    'document'),
('doc:approve', 'Approve/reject document reviews',         'document'),
('doc:comment', 'Add comments and annotations',            'document'),
('doc:share',   'Share documents with users or roles',     'document'),
('doc:export',  'Export documents to PDF/other formats',   'document'),
-- User management permissions
('user:read',   'View user list and profiles',             'user'),
('user:create', 'Create new user accounts',                'user'),
('user:update', 'Modify user details and status',          'user'),
('user:delete', 'Delete user accounts',                    'user'),
-- Role management permissions
('role:read',   'View role list and details',              'role'),
('role:create', 'Create new roles',                        'role'),
('role:update', 'Modify existing roles',                   'role'),
('role:delete', 'Delete roles',                            'role'),
('role:assign', 'Assign roles to users',                   'role'),
-- Audit permissions
('audit:read',  'View audit logs',                         'audit'),
('audit:export','Export audit logs',                       'audit'),
-- System permissions
('system:config', 'Modify system configuration',           'system'),
('system:backup', 'Perform system backup and restore',     'system'),
('file:permission:manage', 'Manage file role permissions', 'file');


-- === Roles (6 roles for Enterprise Document Management & Collaboration) ===
-- Hierarchy (high → low):
--   SUPER_ADMIN (L1) > ADMIN (L2) > MANAGER (L3) > EDITOR (L4)  > VIEWER (L5)
--                                                    > REVIEWER (L4) >
INSERT INTO roles (name, description) VALUES
('SUPER_ADMIN', '超级管理员 - 系统最高权限，全部功能模块可见，可管理系统配置与安全策略'),
('ADMIN',       '系统管理员 - 负责用户管理、角色分配、审计日志导出与系统备份维护'),
('MANAGER',     '部门经理 - 管理部门文档和团队成员，可审批、删除文档，查看审计日志'),
('EDITOR',      '文档编辑员 - 创建、编辑、共享文档，参与文档评论'),
('REVIEWER',    '文档审核员 - 审阅文档、添加评论和批注、建议修改'),
('VIEWER',      '外部访客 - 仅可浏览、搜索和下载文档');


-- === Role-Permission Mapping ===
-- Each role only gets its OWN unique permissions.
-- Inherited permissions (from junior roles via hierarchy) are resolved at runtime.

-- VIEWER: base level - only read and export
INSERT INTO role_permissions (role_id, permission_id)
SELECT r.id, p.id FROM roles r, permissions p
WHERE r.name = 'VIEWER' AND p.name IN (
    'doc:read', 'doc:export'
);

-- REVIEWER: read + review + comment (inherits VIEWER through hierarchy)
INSERT INTO role_permissions (role_id, permission_id)
SELECT r.id, p.id FROM roles r, permissions p
WHERE r.name = 'REVIEWER' AND p.name IN (
    'doc:review', 'doc:comment'
);

-- EDITOR: create + update + share + comment (inherits VIEWER through hierarchy)
-- NOTE: EDITOR deliberately lacks doc:review (separation of duties — editors should not review their own work)
INSERT INTO role_permissions (role_id, permission_id)
SELECT r.id, p.id FROM roles r, permissions p
WHERE r.name = 'EDITOR' AND p.name IN (
    'doc:create', 'doc:update', 'doc:share', 'doc:comment'
);

-- MANAGER: delete + approve + user:read + role:read (inherits EDITOR + REVIEWER through hierarchy)
INSERT INTO role_permissions (role_id, permission_id)
SELECT r.id, p.id FROM roles r, permissions p
WHERE r.name = 'MANAGER' AND p.name IN (
    'doc:delete', 'doc:approve',
    'user:read',
    'role:read',
    'audit:read'
);

-- ADMIN: user:crud + role:crud/assign + audit:export + system:backup (inherits MANAGER)
INSERT INTO role_permissions (role_id, permission_id)
SELECT r.id, p.id FROM roles r, permissions p
WHERE r.name = 'ADMIN' AND p.name IN (
    'user:create', 'user:update', 'user:delete',
    'role:create', 'role:update', 'role:delete', 'role:assign',
    'audit:export',
    'system:backup',
    'file:permission:manage'
);

-- SUPER_ADMIN: system:config (inherits ADMIN = all permissions)
INSERT INTO role_permissions (role_id, permission_id)
SELECT r.id, p.id FROM roles r, permissions p
WHERE r.name = 'SUPER_ADMIN' AND p.name IN (
    'system:config'
);


-- === Role Hierarchy Configuration (Enterprise Document Management) ===
-- The senior role inherits ALL permissions of the junior role.
-- Resolution: to get all permissions for a role, collect its own permissions
--             + all permissions of roles it inherits (recursively).
--
-- Hierarchy:
--   SUPER_ADMIN (L1) → ADMIN (L2) → MANAGER (L3) → EDITOR (L4) → VIEWER (L5)
--                                                     REVIEWER (L4) → VIEWER (L5)
-- EDITOR and REVIEWER are at the same level (L4), enforcing separation of duties:
--   - EDITOR creates/edits content but cannot review/approve
--   - REVIEWER reviews/approves content but cannot edit

-- SUPER_ADMIN inherits ADMIN
INSERT INTO role_hierarchy (role_id, inherited_role_id)
SELECT senior.id, junior.id FROM roles senior, roles junior
WHERE senior.name = 'SUPER_ADMIN' AND junior.name = 'ADMIN';

-- ADMIN inherits MANAGER
INSERT INTO role_hierarchy (role_id, inherited_role_id)
SELECT senior.id, junior.id FROM roles senior, roles junior
WHERE senior.name = 'ADMIN' AND junior.name = 'MANAGER';

-- MANAGER inherits EDITOR and REVIEWER (branching hierarchy)
INSERT INTO role_hierarchy (role_id, inherited_role_id)
SELECT senior.id, junior.id FROM roles senior, roles junior
WHERE senior.name = 'MANAGER' AND junior.name IN ('EDITOR', 'REVIEWER');

-- EDITOR inherits VIEWER
INSERT INTO role_hierarchy (role_id, inherited_role_id)
SELECT senior.id, junior.id FROM roles senior, roles junior
WHERE senior.name = 'EDITOR' AND junior.name = 'VIEWER';

-- REVIEWER inherits VIEWER
INSERT INTO role_hierarchy (role_id, inherited_role_id)
SELECT senior.id, junior.id FROM roles senior, roles junior
WHERE senior.name = 'REVIEWER' AND junior.name = 'VIEWER';


-- === Default Admin User ===
-- Password is BCrypt hash of 'admin123'
INSERT INTO users (username, password, display_name, email, enabled) VALUES
('admin', '$2b$12$RMVdQpb8tIGAkQqlT2JCSOSj97kLZeB6L6SQKFNiNSmGVj2.JhKXW', 'System Administrator', 'admin@example.com', TRUE);

-- Assign SUPER_ADMIN role to admin user
INSERT INTO user_roles (user_id, role_id)
SELECT u.id, r.id FROM users u, roles r
WHERE u.username = 'admin' AND r.name = 'SUPER_ADMIN';


-- === Default Root Directory ===
INSERT INTO file_records (file_name, is_directory, owner_id, parent_id)
SELECT 'Root', TRUE, u.id, NULL FROM users u WHERE u.username = 'admin';

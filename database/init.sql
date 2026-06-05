-- ========================================
-- RBAC File Manager - Database Schema
-- Supports: MySQL 8.0+ / PostgreSQL 16+
-- ========================================

-- Users table
CREATE TABLE IF NOT EXISTS users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(50) NOT NULL UNIQUE,
    password VARCHAR(255) NOT NULL,
    display_name VARCHAR(100),
    email VARCHAR(100),
    enabled BOOLEAN NOT NULL DEFAULT TRUE,
    failed_login_attempts INT NOT NULL DEFAULT 0,
    locked_until DATETIME,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    deleted BOOLEAN NOT NULL DEFAULT FALSE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Roles table
CREATE TABLE IF NOT EXISTS roles (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(50) NOT NULL UNIQUE,
    description VARCHAR(200),
    enabled BOOLEAN NOT NULL DEFAULT TRUE,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    deleted BOOLEAN NOT NULL DEFAULT FALSE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Permissions table
CREATE TABLE IF NOT EXISTS permissions (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL UNIQUE,
    description VARCHAR(200),
    category VARCHAR(50),
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    deleted BOOLEAN NOT NULL DEFAULT FALSE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- User-Role mapping (many-to-many)
CREATE TABLE IF NOT EXISTS user_roles (
    user_id INT NOT NULL,
    role_id INT NOT NULL,
    PRIMARY KEY (user_id, role_id),
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (role_id) REFERENCES roles(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Role-Permission mapping (many-to-many)
CREATE TABLE IF NOT EXISTS role_permissions (
    role_id INT NOT NULL,
    permission_id INT NOT NULL,
    PRIMARY KEY (role_id, permission_id),
    FOREIGN KEY (role_id) REFERENCES roles(id) ON DELETE CASCADE,
    FOREIGN KEY (permission_id) REFERENCES permissions(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Role Hierarchy: senior roles inherit permissions from junior roles
-- e.g. SUPER_ADMIN inherits ADMIN 鈫?SUPER_ADMIN gets all ADMIN's permissions
CREATE TABLE IF NOT EXISTS role_hierarchy (
    role_id INT NOT NULL,            -- the senior/higher role
    inherited_role_id INT NOT NULL,   -- the junior/lower role whose permissions are inherited
    PRIMARY KEY (role_id, inherited_role_id),
    FOREIGN KEY (role_id) REFERENCES roles(id) ON DELETE CASCADE,
    FOREIGN KEY (inherited_role_id) REFERENCES roles(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- File records (supports directory tree structure)
CREATE TABLE IF NOT EXISTS file_records (
    id INT AUTO_INCREMENT PRIMARY KEY,
    file_name VARCHAR(500) NOT NULL,
    file_path VARCHAR(1000),
    parent_id INT,
    is_directory BOOLEAN NOT NULL DEFAULT FALSE,
    size INT DEFAULT 0,
    mime_type VARCHAR(100),
    owner_id INT NOT NULL,
    storage_url VARCHAR(1000),
    status VARCHAR(20) NOT NULL DEFAULT 'draft' COMMENT 'draft, under_review, approved, rejected',
    review_comment VARCHAR(500),
    reviewed_by INT,
    reviewed_at DATETIME,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    deleted BOOLEAN NOT NULL DEFAULT FALSE,
    FOREIGN KEY (parent_id) REFERENCES file_records(id) ON DELETE SET NULL,
    FOREIGN KEY (owner_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (reviewed_by) REFERENCES users(id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- File-level permissions (optional fine-grained control)
CREATE TABLE IF NOT EXISTS file_permissions (
    id INT AUTO_INCREMENT PRIMARY KEY,
    file_id INT NOT NULL,
    user_id INT,
    role_id INT,
    permission_type VARCHAR(20) NOT NULL COMMENT 'read, write, update, delete',
    granted_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (file_id) REFERENCES file_records(id) ON DELETE CASCADE,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (role_id) REFERENCES roles(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Audit logs
CREATE TABLE IF NOT EXISTS audit_logs (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    username VARCHAR(50),
    action VARCHAR(50) NOT NULL COMMENT 'LOGIN, LOGOUT, CREATE_FILE, DELETE_FILE, UPDATE_FILE, READ_FILE, ASSIGN_ROLE, etc.',
    detail VARCHAR(500),
    ip_address VARCHAR(45),
    success BOOLEAN NOT NULL DEFAULT TRUE,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    deleted BOOLEAN NOT NULL DEFAULT FALSE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- File activities (review/approve/comment history per file version)
CREATE TABLE IF NOT EXISTS file_activities (
    id INT AUTO_INCREMENT PRIMARY KEY,
    file_id INT NOT NULL,
    user_id INT NOT NULL,
    activity_type VARCHAR(20) NOT NULL COMMENT 'review, approve, comment',
    content VARCHAR(500),
    approved BOOLEAN COMMENT 'only for approve type',
    is_history BOOLEAN NOT NULL DEFAULT FALSE COMMENT 'true if from a previous file version',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (file_id) REFERENCES file_records(id) ON DELETE CASCADE,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Indexes
CREATE INDEX idx_users_username ON users(username);
CREATE INDEX idx_roles_name ON roles(name);
CREATE INDEX idx_permissions_name ON permissions(name);
CREATE INDEX idx_permissions_category ON permissions(category);
CREATE INDEX idx_file_records_parent ON file_records(parent_id);
CREATE INDEX idx_file_records_owner ON file_records(owner_id);
CREATE INDEX idx_audit_logs_user ON audit_logs(user_id);
CREATE INDEX idx_audit_logs_action ON audit_logs(action);
CREATE INDEX idx_audit_logs_created ON audit_logs(created_at);
CREATE INDEX idx_file_activities_file ON file_activities(file_id);
CREATE INDEX idx_file_activities_type ON file_activities(activity_type);

-- ========================================
-- Migration: Review Workflow columns (v2)
-- Run these ALTER TABLE statements if upgrading from v1 schema
-- ========================================
-- ALTER TABLE file_records ADD COLUMN status VARCHAR(20) DEFAULT 'draft';
-- ALTER TABLE file_records ADD COLUMN review_comment VARCHAR(500);
-- ALTER TABLE file_records ADD COLUMN reviewed_by INT;
-- ALTER TABLE file_records ADD COLUMN reviewed_at DATETIME;
-- ALTER TABLE file_records ADD FOREIGN KEY (reviewed_by) REFERENCES users(id) ON DELETE SET NULL;

-- ========================================
-- Migration: Account Lockout columns (v3)
-- ========================================
-- ALTER TABLE users ADD COLUMN failed_login_attempts INT NOT NULL DEFAULT 0;
-- ALTER TABLE users ADD COLUMN locked_until DATETIME;


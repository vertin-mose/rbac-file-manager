"""Business logic: auth, roles, files, audit."""

import csv
import io
import os
import re
import uuid
from datetime import datetime, timedelta
from typing import Optional

from fastapi import HTTPException, UploadFile
from minio import Minio
from sqlalchemy import desc
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from auth import create_token, hash_password, verify_password
from config import settings
from models import (
    AuditLog, FileActivity, FilePermission, FileRecord, Permission, Role, RoleHierarchy, RolePermission, User, UserRole,
)

# ── Security Constants ──────────────────────────────────────────────────────

MAX_LOGIN_ATTEMPTS = 5
LOCKOUT_DURATION_MINUTES = 15
PASSWORD_MIN_LENGTH = 8


# ── Helpers ────────────────────────────────────────────────────────────────

def validate_password_strength(password: str) -> str | None:
    """Return error message if password is too weak, else None."""
    if len(password) < PASSWORD_MIN_LENGTH:
        return f"密码长度不能少于{PASSWORD_MIN_LENGTH}位"
    if not re.search(r"[A-Z]", password):
        return "密码必须包含至少一个大写字母"
    if not re.search(r"[a-z]", password):
        return "密码必须包含至少一个小写字母"
    if not re.search(r"[0-9]", password):
        return "密码必须包含至少一个数字"


# Global MinIO client instance (lazy singleton — checked only once)
_minio_client: Optional[Minio] = None
_minio_checked = False


def get_minio_client() -> Optional[Minio]:
    global _minio_client, _minio_checked
    if _minio_checked:
        return _minio_client
    _minio_checked = True
    try:
        url = settings.MINIO_ENDPOINT.replace("http://", "").replace("https://", "")
        client = Minio(url, access_key=settings.MINIO_ACCESS_KEY,
                       secret_key=settings.MINIO_SECRET_KEY, secure=False)
        if not client.bucket_exists(settings.MINIO_BUCKET):
            client.make_bucket(settings.MINIO_BUCKET)
        _minio_client = client
    except Exception:
        _minio_client = None
    return _minio_client


def record_audit(db: Session, user_id: int, username: str, action: str,
                 detail: str = "", ip: str = "", success: bool = True):
    log = AuditLog(user_id=user_id, username=username, action=action,
                   detail=detail, ip_address=ip, success=success)
    db.add(log)
    db.commit()


def get_effective_permissions(role_id: int, db: Session) -> set[str]:
    """Recursively collect own + inherited permission names for a role."""
    visited = set()
    result = set()

    def collect(rid: int):
        if rid in visited:
            return
        visited.add(rid)
        role = db.get(Role, rid)
        if not role:
            return
        # Deleted roles: skip their own permissions but still traverse inherited
        # roles so the chain isn't broken (e.g. ADMIN → deleted_custom → MANAGER
        # should still deliver MANAGER's permissions to ADMIN).
        if not role.deleted:
            for p in role.permissions:
                if not p.deleted:
                    result.add(p.name)
        for ir in role.inherited_roles:
            collect(ir.id)

    collect(role_id)
    return result


# ── Auth Service ───────────────────────────────────────────────────────────

ROLE_LEVEL = {
    'SUPER_ADMIN': 1,
    'ADMIN': 2,
    'MANAGER': 3,
    'EDITOR': 4,
    'REVIEWER': 4,
    'VIEWER': 5,
}

ROLE_DISPLAY = {
    'SUPER_ADMIN': '超级管理员',
    'ADMIN': '系统管理员',
    'MANAGER': '部门经理',
    'EDITOR': '文档编辑员',
    'REVIEWER': '文档审核员',
    'VIEWER': '访客',
}
ROLE_DESCRIPTION = {
    'SUPER_ADMIN': '系统最高权限，管理全部功能模块与系统配置。',
    'ADMIN': '负责用户、角色与审计日志导出等管理工作。',
    'MANAGER': '管理部门文档和成员，可审批、删除文档并查看审计日志。',
    'EDITOR': '负责创建、编辑、共享文档，并参与评论协作。',
    'REVIEWER': '负责审阅文档、添加评论与批注，并提出修改建议。',
    'VIEWER': '仅可浏览、检索和导出文档内容。',
}


def login(db: Session, username: str, password: str, ip: str = "") -> dict:
    user = db.query(User).filter(User.username == username, User.deleted == False).first()

    # ── Account lockout check ──
    if user and user.locked_until and user.locked_until > datetime.now():
        remaining = int((user.locked_until - datetime.now()).total_seconds() // 60) + 1
        record_audit(db, user.id, username, "LOGIN_FAILED",
                     detail=f"用户{username}登录失败（账户已锁定，剩余{remaining}分钟）", ip=ip, success=False)
        raise HTTPException(
            status_code=423,
            detail=f"账户已被锁定，请在{remaining}分钟后重试",
        )

    if not user or not verify_password(password, user.password):
        if user:
            user.failed_login_attempts = (user.failed_login_attempts or 0) + 1
            if user.failed_login_attempts >= MAX_LOGIN_ATTEMPTS:
                user.locked_until = datetime.now() + timedelta(minutes=LOCKOUT_DURATION_MINUTES)
                record_audit(db, user.id, username, "LOGIN_FAILED",
                             detail=f"用户{username}连续{MAX_LOGIN_ATTEMPTS}次登录失败，已锁定{LOCKOUT_DURATION_MINUTES}分钟",
                             ip=ip, success=False)
                raise HTTPException(
                    status_code=423,
                    detail=f"连续{MAX_LOGIN_ATTEMPTS}次登录失败，账户已锁定{LOCKOUT_DURATION_MINUTES}分钟",
                )
            db.commit()
        record_audit(db, user.id if user else 0, username, "LOGIN_FAILED",
                     detail=f"用户{username}登录失败（第{user.failed_login_attempts if user else 0}次尝试）",
                     ip=ip, success=False)
        raise HTTPException(status_code=401, detail="Invalid username or password")
    if not user.enabled:
        raise HTTPException(status_code=403, detail="Account disabled")

    # ── Reset lockout on successful login ──
    user.failed_login_attempts = 0
    user.locked_until = None
    db.commit()

    active_roles = [r for r in user.roles if not r.deleted]
    role_names = [r.name for r in active_roles]
    all_perms = set()
    for r in active_roles:
        all_perms |= get_effective_permissions(r.id, db)

    token = create_token(user.id, user.username, role_names)
    record_audit(db, user.id, user.username, "LOGIN", detail=f"用户{user.username}已登录", ip=ip)

    return {"token": token, "user_id": user.id, "username": user.username, "display_name": user.display_name,
            "roles": role_names,
            "role_info": [
                {"name": r, "display_name": ROLE_DISPLAY.get(r, r), "level": ROLE_LEVEL.get(r, 99)}
                for r in role_names
            ],
            "permissions": sorted(all_perms)}


def get_role_description(role: Role) -> str:
    return ROLE_DESCRIPTION.get(role.name, role.description or "")


def register(db: Session, username: str, password: str,
             display_name: Optional[str] = None, email: Optional[str] = None) -> dict:
    err = validate_password_strength(password)
    if err:
        raise HTTPException(status_code=400, detail=err)
    exists = db.query(User).filter(User.username == username, User.deleted == False).first()
    if exists:
        raise HTTPException(status_code=409, detail="Username already taken")

    user = User(username=username, password=hash_password(password),
                display_name=display_name, email=email)
    db.add(user)
    db.commit()
    db.refresh(user)

    # Assign the VIEWER role by default
    viewer_role = db.query(Role).filter(Role.name == "VIEWER", Role.deleted == False).first()
    if viewer_role:
        user.roles = [viewer_role]
        db.commit()

    return {"id": user.id, "username": user.username,
            "display_name": user.display_name, "email": user.email}


# ── Role Service ───────────────────────────────────────────────────────────

def list_roles(db: Session) -> list[dict]:
    roles = db.query(Role).filter(Role.deleted == False).all()
    result = []
    for r in roles:
        active_permissions = [p for p in r.permissions if not p.deleted]
        perms = [{"id": p.id, "name": p.name, "description": p.description,
                   "category": p.category} for p in active_permissions]
        inherited = get_effective_permissions(r.id, db) - {p.name for p in active_permissions}
        inherited_perms = db.query(Permission).filter(
            Permission.name.in_(inherited), Permission.deleted == False
        ).all() if inherited else []
        result.append({
            "id": r.id, "name": r.name, "description": get_role_description(r),
            "permissions": perms,
            "inherited_permissions": [{"id": p.id, "name": p.name, "description": p.description,
                                        "category": p.category} for p in inherited_perms],
        })
    return result


def get_role(db: Session, role_id: int) -> dict:
    role = db.get(Role, role_id)
    if not role or role.deleted:
        raise HTTPException(status_code=404, detail="Role not found")
    active_permissions = [p for p in role.permissions if not p.deleted]
    perms = [{"id": p.id, "name": p.name, "description": p.description, "category": p.category}
             for p in active_permissions]
    inherited_names = get_effective_permissions(role.id, db) - {p.name for p in active_permissions}
    inherited_perms = db.query(Permission).filter(
        Permission.name.in_(inherited_names), Permission.deleted == False
    ).all() if inherited_names else []
    return {
        "id": role.id, "name": role.name, "description": get_role_description(role),
        "permissions": perms,
        "inherited_permissions": [{"id": p.id, "name": p.name, "description": p.description,
                                    "category": p.category} for p in inherited_perms],
    }


def create_role(db: Session, name: str, description: str = "",
                permission_ids: list[int] = None,
                inherited_role_ids: list[int] = None,
                rewire_children: bool = False) -> dict:
    """Create a role with optional hierarchy position and initial permissions."""
    # Only check non-deleted roles — deleted role names can be reused
    exists = db.query(Role).filter(Role.name == name, Role.deleted == False).first()
    if exists:
        raise HTTPException(status_code=409, detail="角色名已存在")
    # If a deleted role has this name, rename it to free the name for reuse
    deleted = db.query(Role).filter(Role.name == name, Role.deleted == True).first()
    if deleted:
        deleted.name = f"{name}_deleted_{deleted.id}"
        db.commit()
    role = Role(name=name, description=description)
    if permission_ids:
        perms = db.query(Permission).filter(Permission.id.in_(permission_ids)).all()
        role.permissions = perms
    db.add(role)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="角色名冲突，请更换名称")
    db.refresh(role)

    if inherited_role_ids:
        for ir_id in inherited_role_ids:
            ir = db.get(Role, ir_id)
            if ir and not ir.deleted:
                hierarchy_entry = RoleHierarchy(role_id=role.id, inherited_role_id=ir_id)
                db.add(hierarchy_entry)
        db.commit()
        db.refresh(role)

    # Rewire: make all direct children of inherited roles point to the new role instead
    if rewire_children and inherited_role_ids:
        children = db.query(RoleHierarchy).filter(
            RoleHierarchy.inherited_role_id.in_(inherited_role_ids),
            RoleHierarchy.role_id != role.id,
        ).all()
        for child_entry in children:
            child_entry.inherited_role_id = role.id
        db.commit()

    return get_role(db, role.id)


def update_role(db: Session, role_id: int, name: Optional[str] = None,
                description: Optional[str] = None) -> dict:
    role = db.get(Role, role_id)
    if not role or role.deleted:
        raise HTTPException(status_code=404, detail="Role not found")
    if name:
        # Check all roles (including deleted) to avoid unique constraint violation
        existing = db.query(Role).filter(Role.name == name, Role.id != role_id).first()
        if existing:
            raise HTTPException(status_code=409, detail="角色名已存在")
        role.name = name
    if description is not None:
        role.description = description
    db.commit()
    db.refresh(role)
    return get_role(db, role.id)


def delete_role(db: Session, role_id: int):
    role = db.get(Role, role_id)
    if not role or role.deleted:
        raise HTTPException(status_code=404, detail="Role not found")

    # Reconnect children to this role's parents before deleting,
    # so the inheritance chain is not broken (e.g. ADMIN → a → MANAGER
    # becomes ADMIN → MANAGER when "a" is deleted).
    parents = [r.id for r in role.inherited_roles]
    children = db.query(RoleHierarchy).filter(
        RoleHierarchy.inherited_role_id == role_id
    ).all()
    if children and parents:
        for child in children:
            child.inherited_role_id = parents[0]
    elif children and not parents:
        # Orphan children — delete the link
        for child in children:
            db.delete(child)

    role.permissions = []
    role.inherited_roles = []
    db.query(UserRole).filter(UserRole.role_id == role_id).delete(synchronize_session=False)
    db.query(RolePermission).filter(RolePermission.role_id == role_id).delete(synchronize_session=False)
    role.deleted = True
    db.commit()


def assign_permissions(db: Session, role_id: int, permission_ids: list[int]):
    role = db.get(Role, role_id)
    if not role or role.deleted:
        raise HTTPException(status_code=404, detail="Role not found")
    perms = db.query(Permission).filter(Permission.id.in_(permission_ids)).all()
    role.permissions = perms
    db.commit()


def get_hierarchy(db: Session) -> list[dict]:
    rows = db.query(RoleHierarchy).all()
    result = []
    for row in rows:
        senior = db.get(Role, row.role_id)
        junior = db.get(Role, row.inherited_role_id)
        if senior and junior and not senior.deleted and not junior.deleted:
            result.append({"role_id": row.role_id, "role_name": senior.name,
                           "inherited_role_id": row.inherited_role_id,
                           "inherited_role_name": junior.name})
    return result


def get_hierarchy_structure(db: Session) -> list[dict]:
    """Return all active roles sorted by level with their inherited permissions."""
    roles = db.query(Role).filter(Role.deleted == False).all()
    role_map = {r.id: r for r in roles}

    # Build parent/child maps from RoleHierarchy directly (bypass ORM cache)
    from collections import defaultdict
    parent_map: dict[int, list[int]] = defaultdict(list)   # role_id → [inherited_role_ids]
    child_map: dict[int, list[int]] = defaultdict(list)    # inherited_role_id → [role_ids]
    for rh in db.query(RoleHierarchy).all():
        parent_map[rh.role_id].append(rh.inherited_role_id)
        child_map[rh.inherited_role_id].append(rh.role_id)

    def get_parent_ids(role_id: int) -> list[int]:
        return [pid for pid in parent_map.get(role_id, [])
                if pid in role_map and not role_map[pid].deleted]

    def get_parent_levels(role_id: int) -> list[int]:
        return [level_map.get(pid) for pid in get_parent_ids(role_id)
                if level_map.get(pid) is not None]

    level_map: dict[int, int] = {}

    # Pass 1: roles with hardcoded level or direct inheritance from known roles
    for role in roles:
        if role.name in ROLE_LEVEL:
            level_map[role.id] = ROLE_LEVEL[role.name]
        else:
            parent_ids = get_parent_ids(role.id)
            if parent_ids:
                known = [ROLE_LEVEL.get(role_map[pid].name) for pid in parent_ids
                         if role_map[pid].name in ROLE_LEVEL]
                level_map[role.id] = min(known) - 1 if known else None
            else:
                level_map[role.id] = 99

    # Pass 2: iterative resolution for chained custom roles (a → b → MANAGER)
    changed = True
    while changed:
        changed = False
        for role in roles:
            if level_map.get(role.id) is None:
                levels = get_parent_levels(role.id)
                if levels:
                    level_map[role.id] = min(levels) - 1
                    changed = True

    # Pass 3: remaining unresolvable → level 99
    for role in roles:
        if level_map.get(role.id) is None:
            level_map[role.id] = 99

    # Pass 4: detect and correct inserted roles.
    inserted_ids: set[int] = set()
    for role in roles:
        if role.name in ROLE_LEVEL:
            continue
        cur = level_map.get(role.id, 99)
        if cur == 99:
            continue
        children_ids = child_map.get(role.id)
        if not children_ids:
            continue
        if not get_parent_ids(role.id):
            continue
        # Check if any child is at same or lower level (child >= role).
        # In a normal hierarchy, children are always above (child_level < role_level).
        # If child_level >= role_level, the role was inserted between the child
        # and the child's former parent, squeezing them together.
        for child_id in children_ids:
            child_level = level_map.get(child_id)
            if child_level is not None and child_level >= cur:
                inserted_ids.add(role.id)
                break

    # Process inserted roles top-down (lowest L first), cascade each
    inserted_roles = sorted(
        [r for r in roles if r.id in inserted_ids],
        key=lambda r: level_map.get(r.id, 99),
    )
    for role in inserted_roles:
        parent_levels = get_parent_levels(role.id)
        if not parent_levels:
            continue
        new_level = min(parent_levels)
        level_map[role.id] = new_level
        # Cascade: everything at >= new_level shifts down by 1 (except this role)
        for r in roles:
            rl = level_map.get(r.id)
            if rl is not None and rl >= new_level and r.id != role.id:
                level_map[r.id] = rl + 1

    # Re-resolve non-foundation, non-inserted roles whose parent levels changed
    changed = True
    while changed:
        changed = False
        for role in roles:
            if role.name in ROLE_LEVEL or role.id in inserted_ids:
                continue
            levels = get_parent_levels(role.id)
            if not levels:
                continue
            expected = min(levels) - 1
            if level_map.get(role.id) != expected:
                level_map[role.id] = expected
                changed = True

    result = []
    for role in roles:
        level = level_map[role.id]
        effective_perms = get_effective_permissions(role.id, db)
        parent_ids = get_parent_ids(role.id)
        result.append({
            "id": role.id,
            "name": role.name,
            "level": level,
            "display_name": ROLE_DISPLAY.get(role.name, role.name),
            "description": get_role_description(role),
            "effective_permissions": sorted(effective_perms),
            "inherited_from": [
                {"id": pid, "name": role_map[pid].name,
                 "display_name": ROLE_DISPLAY.get(role_map[pid].name, role_map[pid].name)}
                for pid in parent_ids
            ],
        })
    result.sort(key=lambda r: (r["level"], r["name"]))
    return result


def list_users(db: Session) -> list[dict]:
    users = db.query(User).filter(User.deleted == False).all()
    return [
        {"id": u.id, "username": u.username, "display_name": u.display_name, "email": u.email,
         "roles": [{"id": r.id, "name": r.name} for r in u.roles if not r.deleted]}
        for u in users
    ]


def get_user_info(db: Session, user_id: int) -> dict:
    user = db.get(User, user_id)
    if not user or user.deleted:
        raise HTTPException(status_code=404, detail="User not found")
    return {
        "id": user.id,
        "username": user.username,
        "display_name": user.display_name,
        "email": user.email,
        "enabled": user.enabled,
        "roles": [{"id": r.id, "name": r.name, "description": r.description} for r in user.roles if not r.deleted],
    }


def assign_user_roles(db: Session, user_id: int, role_ids: list[int]):
    user = db.get(User, user_id)
    if not user or user.deleted:
        raise HTTPException(status_code=404, detail="User not found")
    roles = db.query(Role).filter(Role.id.in_(role_ids), Role.deleted == False).all()
    user.roles = roles
    db.commit()


def admin_create_user(db: Session, username: str, password: str,
                       display_name: str = None, email: str = None,
                       role_ids: list[int] = None) -> dict:
    """Create user with role selection — admin only."""
    err = validate_password_strength(password)
    if err:
        raise HTTPException(status_code=400, detail=err)
    exists = db.query(User).filter(User.username == username, User.deleted == False).first()
    if exists:
        raise HTTPException(status_code=409, detail="Username already taken")
    user = User(username=username, password=hash_password(password),
                display_name=display_name, email=email)
    db.add(user)
    db.commit()
    db.refresh(user)
    if role_ids:
        roles = db.query(Role).filter(Role.id.in_(role_ids), Role.deleted == False).all()
        user.roles = roles
        db.commit()
    return {
        "id": user.id, "username": user.username,
        "display_name": user.display_name, "email": user.email,
        "roles": [{"id": r.id, "name": r.name} for r in (user.roles or [])],
    }


def toggle_user_status(db: Session, user_id: int) -> dict:
    """Toggle user enabled/disabled."""
    user = db.get(User, user_id)
    if not user or user.deleted:
        raise HTTPException(status_code=404, detail="User not found")
    user.enabled = not user.enabled
    db.commit()
    db.refresh(user)
    return {"id": user.id, "username": user.username, "enabled": user.enabled}


def admin_delete_user(db: Session, user_id: int):
    """Soft delete a user."""
    user = db.get(User, user_id)
    if not user or user.deleted:
        raise HTTPException(status_code=404, detail="User not found")
    user.deleted = True
    user.roles = []
    db.commit()


def admin_update_user(db: Session, user_id: int, display_name: str = None,
                       email: str = None, reset_password: bool = False) -> dict:
    """Admin updates user info or resets password to 123456."""
    user = db.get(User, user_id)
    if not user or user.deleted:
        raise HTTPException(status_code=404, detail="User not found")
    if display_name is not None:
        user.display_name = display_name
    if email is not None:
        user.email = email
    if reset_password:
        user.password = hash_password("123456")
    db.commit()
    db.refresh(user)
    return {"id": user.id, "username": user.username,
            "display_name": user.display_name, "email": user.email,
            "reset_password": reset_password}


def update_own_profile(db: Session, user_id: int, display_name: str = None,
                        email: str = None, old_password: str = None,
                        new_password: str = None) -> dict:
    """Current user updates their own profile or changes password."""
    user = db.get(User, user_id)
    if not user or user.deleted:
        raise HTTPException(status_code=404, detail="User not found")
    if display_name is not None:
        user.display_name = display_name
    if email is not None:
        user.email = email
    if new_password:
        err = validate_password_strength(new_password)
        if err:
            raise HTTPException(status_code=400, detail=err)
        if not old_password or not verify_password(old_password, user.password):
            raise HTTPException(status_code=400, detail="旧密码不正确")
        user.password = hash_password(new_password)
    db.commit()
    db.refresh(user)
    return {"id": user.id, "username": user.username,
            "display_name": user.display_name, "email": user.email,
            "password_changed": bool(new_password)}


# ── File Service ───────────────────────────────────────────────────────────

def _is_privileged_role(roles: list[str]) -> bool:
    return bool(roles and set(roles) & {"SUPER_ADMIN", "ADMIN"})


def _check_file_permission(db: Session, file_id: int, user_id: int,
                           roles: list[str], permission_type: str) -> bool:
    """Pure additive file-level permission check.

    FilePermission records only GRANT additional access on top of RBAC.
    They never restrict users who already have the corresponding RBAC
    permission (checked at the route level via require_perm).
    """
    if _is_privileged_role(roles):
        return True
    f = db.get(FileRecord, file_id)
    if not f or f.deleted:
        return False
    if f.owner_id == user_id:
        return True

    # Resolve role names → IDs for role-level checks
    role_ids = [r.id for r in db.query(Role.id).filter(
        Role.name.in_(roles), Role.deleted == False).all()] if roles else []

    # Walk up the directory tree checking FilePermission records
    current = f
    while current is not None:
        # Check user-level permission
        if db.query(FilePermission).filter(
            FilePermission.file_id == current.id,
            FilePermission.user_id == user_id,
            FilePermission.permission_type == permission_type,
        ).first() is not None:
            return True
        # Check role-level permission
        if role_ids and db.query(FilePermission).filter(
            FilePermission.file_id == current.id,
            FilePermission.role_id.in_(role_ids),
            FilePermission.permission_type == permission_type,
        ).first() is not None:
            return True
        if current.parent_id:
            current = db.get(FileRecord, current.parent_id)
            if not current or current.deleted:
                break
        else:
            break

    # RBAC baseline: route-level require_perm already verified the user has
    # the corresponding RBAC permission (doc:read / doc:update / doc:delete).
    # FilePermission is purely additive — deny only if explicitly restricted.
    return True


def list_files(db: Session, parent_id: int = 0, user_id: int = None,
               roles: list[str] = None):
    if parent_id == 0:
        files = db.query(FileRecord).filter(
            FileRecord.parent_id.is_(None), FileRecord.deleted == False).all()
    else:
        files = db.query(FileRecord).filter(
            FileRecord.parent_id == parent_id, FileRecord.deleted == False).all()

    if user_id and roles and not _is_privileged_role(roles):
        # Check if the parent directory itself is accessible (directory inheritance)
        parent_accessible = False
        if parent_id:
            parent_accessible = _check_file_permission(
                db, parent_id, user_id, roles, "read")

        # Resolve role IDs for role-level access checks
        role_ids = [r.id for r in db.query(Role.id).filter(
            Role.name.in_(roles), Role.deleted == False).all()]

        def is_file_accessible(f: FileRecord) -> bool:
            if f.owner_id == user_id:
                return True
            # Direct user-level permission
            if db.query(FilePermission).filter(
                FilePermission.file_id == f.id,
                FilePermission.user_id == user_id,
                FilePermission.permission_type == "read",
            ).first():
                return True
            # Role-level permission
            if role_ids and db.query(FilePermission).filter(
                FilePermission.file_id == f.id,
                FilePermission.role_id.in_(role_ids),
                FilePermission.permission_type == "read",
            ).first():
                return True
            # Inherited from parent directory
            if parent_accessible:
                return True
            # RBAC baseline: anyone with doc:read (verified at route level) can see files
            return True

        files = [f for f in files if is_file_accessible(f)]

    return [_file_to_dict(f) for f in files]


def _file_to_dict(f: FileRecord) -> dict:
    return {
        "id": f.id, "file_name": f.file_name, "is_directory": f.is_directory,
        "size": f.size or 0, "mime_type": f.mime_type, "owner_id": f.owner_id,
        "parent_id": f.parent_id, "storage_url": f.storage_url or "",
        "status": getattr(f, "status", "draft") or "draft",
        "review_comment": getattr(f, "review_comment", None),
        "reviewed_by": getattr(f, "reviewed_by", None),
        "reviewed_at": f.reviewed_at.isoformat() if getattr(f, "reviewed_at", None) else None,
        "created_at": f.created_at.isoformat() if f.created_at else None,
        "updated_at": f.updated_at.isoformat() if f.updated_at else None,
    }


def get_file(db: Session, file_id: int, user_id: int = None,
             roles: list[str] = None) -> dict:
    f = db.get(FileRecord, file_id)
    if not f or f.deleted:
        raise HTTPException(status_code=404, detail="File not found")
    if user_id and roles and not _check_file_permission(db, file_id, user_id, roles, "read"):
        raise HTTPException(status_code=403, detail="No permission to access this file")
    return _file_to_dict(f)


async def upload_file(db: Session, file: UploadFile, parent_id: int, owner_id: int) -> dict:
    minio_client = get_minio_client()
    ext = file.filename.rsplit(".", 1)[-1] if "." in (file.filename or "") else ""
    storage_name = f"{uuid.uuid4().hex}.{ext}" if ext else uuid.uuid4().hex
    storage_url = ""
    content = await file.read()

    if minio_client:
        minio_client.put_object(settings.MINIO_BUCKET, storage_name,
                                io.BytesIO(content), len(content))
        storage_url = f"{settings.MINIO_ENDPOINT}/{settings.MINIO_BUCKET}/{storage_name}"
    else:
        # Local fallback when MinIO is not configured
        local_dir = os.path.join(os.path.dirname(__file__), "storage")
        os.makedirs(local_dir, exist_ok=True)
        local_path = os.path.join(local_dir, storage_name)
        with open(local_path, "wb") as f:
            f.write(content)
        storage_url = f"local://{storage_name}"

    f = FileRecord(
        file_name=file.filename or "unnamed",
        parent_id=parent_id if parent_id != 0 else None,
        is_directory=False, size=len(content),
        mime_type=file.content_type, owner_id=owner_id,
        storage_url=storage_url,
    )
    db.add(f)
    db.commit()
    db.refresh(f)
    return _file_to_dict(f)


def create_directory(db: Session, name: str, parent_id: int, owner_id: int) -> dict:
    f = FileRecord(
        file_name=name, parent_id=parent_id if parent_id != 0 else None,
        is_directory=True, owner_id=owner_id,
    )
    db.add(f)
    db.commit()
    db.refresh(f)
    return _file_to_dict(f)


def rename_file(db: Session, file_id: int, new_name: str,
                user_id: int = None, roles: list[str] = None) -> dict:
    f = db.get(FileRecord, file_id)
    if not f or f.deleted:
        raise HTTPException(status_code=404, detail="File not found")
    if user_id and roles and not _check_file_permission(db, file_id, user_id, roles, "write"):
        raise HTTPException(status_code=403, detail="No permission to rename this file")
    f.file_name = new_name
    db.commit()
    db.refresh(f)
    return _file_to_dict(f)


def get_file_content(db: Session, file_id: int, user_id: int = None,
                     roles: list[str] = None) -> tuple[bytes, str, str]:
    """Return (content_bytes, mime_type, file_name) for a file record."""
    if user_id and roles and not _check_file_permission(db, file_id, user_id, roles, "read"):
        raise HTTPException(status_code=403, detail="No permission to access this file")
    f = db.get(FileRecord, file_id)
    if not f or f.deleted:
        raise HTTPException(status_code=404, detail="File not found")
    if f.is_directory:
        raise HTTPException(status_code=400, detail="Cannot download a directory")

    if not f.storage_url:
        raise HTTPException(status_code=501, detail="文件内容不可用：上传时未连接 MinIO 存储服务，文件未实际保存")

    # Local file system fallback
    if f.storage_url.startswith("local://"):
        local_dir = os.path.join(os.path.dirname(__file__), "storage")
        local_path = os.path.join(local_dir, f.storage_url[len("local://"):])
        if not os.path.exists(local_path):
            raise HTTPException(status_code=501, detail="文件内容不可用：本地存储文件已被删除")
        with open(local_path, "rb") as fh:
            content = fh.read()
        return content, f.mime_type or "application/octet-stream", f.file_name

    # Try to read from MinIO
    minio_client = get_minio_client()
    if not minio_client:
        raise HTTPException(status_code=501, detail="文件内容不可用：MinIO 存储服务未启动，请联系管理员")

    try:
        path = f.storage_url.replace(settings.MINIO_ENDPOINT, "").strip("/")
        parts = path.split("/", 1)
        if len(parts) != 2:
            raise HTTPException(status_code=501, detail="文件存储路径异常")
        bucket, object_name = parts
        response = minio_client.get_object(bucket, object_name)
        content = response.read()
        response.close()
        response.release_conn()
        return content, f.mime_type or "application/octet-stream", f.file_name
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=501, detail="文件内容不可用：读取存储服务时出错")


def delete_file(db: Session, file_id: int, user_id: int = None,
                roles: list[str] = None):
    f = db.get(FileRecord, file_id)
    if not f or f.deleted:
        raise HTTPException(status_code=404, detail="File not found")
    if user_id and roles and not _check_file_permission(db, file_id, user_id, roles, "delete"):
        raise HTTPException(status_code=403, detail="No permission to delete this file")
    deleted_ids: list[int] = []

    def mark_deleted(node: FileRecord):
        deleted_ids.append(node.id)
        node.deleted = True
        for child in (node.children or []):
            mark_deleted(child)

    mark_deleted(f)
    db.query(FilePermission).filter(FilePermission.file_id.in_(deleted_ids)).delete(synchronize_session=False)
    db.commit()


def share_file(db: Session, file_id: int, user_ids: list[int],
               permission_type: str = "read") -> dict:
    f = db.get(FileRecord, file_id)
    if not f or f.deleted:
        raise HTTPException(status_code=404, detail="File not found")
    granted = []
    skipped = []
    for uid in user_ids:
        existing = db.query(FilePermission).filter(
            FilePermission.file_id == file_id,
            FilePermission.user_id == uid,
            FilePermission.permission_type == permission_type,
        ).first()
        if existing:
            skipped.append(uid)
        else:
            db.add(FilePermission(file_id=file_id, user_id=uid, permission_type=permission_type))
            granted.append(uid)
    if granted:
        db.commit()
    return {"granted": granted, "skipped": skipped}


# ── File Permission Service ────────────────────────────────────────────────

def review_file(db: Session, file_id: int, reviewer_id: int, comment: str = "") -> dict:
    """Submit a file for review — sets status to 'under_review'."""
    f = db.get(FileRecord, file_id)
    if not f or f.deleted:
        raise HTTPException(status_code=404, detail="File not found")
    if f.is_directory:
        raise HTTPException(status_code=400, detail="Directories cannot be reviewed")
    from datetime import datetime as dt
    f.status = "under_review"
    f.review_comment = comment or ""
    f.reviewed_by = reviewer_id
    f.reviewed_at = dt.now()
    db.commit()
    db.refresh(f)
    create_activity(db, file_id, reviewer_id, "review", comment)
    return _file_to_dict(f)


def approve_file(db: Session, file_id: int, approver_id: int,
                 approved: bool = True, comment: str = "") -> dict:
    """Approve or reject a file — sets status to 'approved' or 'rejected'.

    One-time only: raises 400 if file is already approved/rejected.
    After update_file_content (status reset to draft), approval can be submitted again.
    """
    f = db.get(FileRecord, file_id)
    if not f or f.deleted:
        raise HTTPException(status_code=404, detail="File not found")
    if f.is_directory:
        raise HTTPException(status_code=400, detail="Directories cannot be approved")
    if f.status in ("approved", "rejected"):
        raise HTTPException(status_code=400, detail="该文件已完成审批，更新文件后可再次提交审批")
    from datetime import datetime as dt
    f.status = "approved" if approved else "rejected"
    f.review_comment = comment or ""
    f.reviewed_by = approver_id
    f.reviewed_at = dt.now()
    db.commit()
    db.refresh(f)
    create_activity(db, file_id, approver_id, "approve", comment, approved)
    return _file_to_dict(f)

def comment_file(db: Session, file_id: int, user_id: int, content: str = "") -> dict:
    """Add a comment to a file."""
    f = db.get(FileRecord, file_id)
    if not f or f.deleted:
        raise HTTPException(status_code=404, detail="File not found")
    if f.is_directory:
        raise HTTPException(status_code=400, detail="Directories cannot be commented on")
    create_activity(db, file_id, user_id, "comment", content)
    return _file_to_dict(f)


def get_file_permissions(db: Session, file_id: int) -> list[dict]:
    f = db.get(FileRecord, file_id)
    if not f or f.deleted:
        raise HTTPException(status_code=404, detail="File not found")
    perms = db.query(FilePermission).filter(FilePermission.file_id == file_id).all()
    result = []
    for p in perms:
        role = db.get(Role, p.role_id) if p.role_id else None
        user = db.get(User, p.user_id) if p.user_id else None
        result.append({
            "id": p.id,
            "file_id": p.file_id,
            "role_id": p.role_id,
            "role_name": role.name if role and not role.deleted else None,
            "user_id": p.user_id,
            "username": user.username if user and not user.deleted else None,
            "permission_type": p.permission_type,
            "granted_at": p.granted_at.isoformat() if p.granted_at else None,
        })
    return result


def set_file_permissions(db: Session, file_id: int,
                         permissions: list[dict]) -> list[dict]:
    f = db.get(FileRecord, file_id)
    if not f or f.deleted:
        raise HTTPException(status_code=404, detail="File not found")
    db.query(FilePermission).filter(FilePermission.file_id == file_id).delete(
        synchronize_session=False)
    for perm in permissions:
        db.add(FilePermission(
            file_id=file_id,
            role_id=perm.get("role_id"),
            user_id=perm.get("user_id"),
            permission_type=perm["permission_type"],
        ))
    db.commit()
    return get_file_permissions(db, file_id)


def delete_file_permission(db: Session, perm_id: int):
    perm = db.get(FilePermission, perm_id)
    if not perm:
        raise HTTPException(status_code=404, detail="Permission not found")
    db.delete(perm)
    db.commit()


def can_manage_file_permissions(db: Session, file_id: int, user_id: int, roles: list[str]) -> bool:
    """Check if user can modify file permissions.
    - Admin/SUPER_ADMIN always can.
    - File owner can if no permissions have been set yet (initial setup).
    """
    if _is_privileged_role(roles):
        return True
    # Check if user has file:permission:manage via any role
    for role_name in roles:
        role = db.query(Role).filter(Role.name == role_name, Role.deleted == False).first()
        if role and "file:permission:manage" in get_effective_permissions(role.id, db):
            return True
    # Allow file owner for initial setup (no permissions exist yet)
    f = db.get(FileRecord, file_id)
    if f and not f.deleted and f.owner_id == user_id:
        existing = db.query(FilePermission).filter(FilePermission.file_id == file_id).count()
        if existing == 0:
            return True
    return False


# ── File Activity Service ───────────────────────────────────────────────

def create_activity(db: Session, file_id: int, user_id: int,
                    activity_type: str, content: str = "",
                    approved: bool = None):
    """Create a FileActivity record for the current version."""
    activity = FileActivity(
        file_id=file_id, user_id=user_id,
        activity_type=activity_type, content=content or "",
        approved=approved, is_history=False,
    )
    db.add(activity)
    db.commit()


def get_file_activities(db: Session, file_id: int) -> list[dict]:
    """Return all activities for a file, newest first."""
    f = db.get(FileRecord, file_id)
    if not f or f.deleted:
        raise HTTPException(status_code=404, detail="File not found")
    activities = db.query(FileActivity).filter(
        FileActivity.file_id == file_id
    ).order_by(desc(FileActivity.created_at)).all()
    result = []
    for act in activities:
        user = db.get(User, act.user_id)
        result.append({
            "id": act.id,
            "file_id": act.file_id,
            "user_id": act.user_id,
            "username": user.username if user and not user.deleted else "已删除用户",
            "activity_type": act.activity_type,
            "content": act.content,
            "approved": act.approved,
            "is_history": act.is_history,
            "created_at": act.created_at.isoformat() if act.created_at else None,
        })
    return result


def delete_activity(db: Session, activity_id: int, user_id: int, roles: list[str]):
    """Delete a review or comment activity.

    Only the author or SUPER_ADMIN/ADMIN may delete.
    Approve-type activities cannot be deleted (audit trail).
    """
    act = db.get(FileActivity, activity_id)
    if not act:
        raise HTTPException(status_code=404, detail="Activity not found")
    if act.activity_type == "approve":
        raise HTTPException(status_code=400, detail="审批记录不可删除")
    if act.user_id != user_id and not _is_privileged_role(roles):
        raise HTTPException(status_code=403, detail="无权删除此记录")
    db.delete(act)
    db.commit()


def update_file_content(db: Session, file_id: int, file: UploadFile,
                         user_id: int, roles: list[str]) -> dict:
    """Overwrite file content, reset status to draft, mark old activities as history."""
    f = db.get(FileRecord, file_id)
    if not f or f.deleted:
        raise HTTPException(status_code=404, detail="File not found")
    if f.is_directory:
        raise HTTPException(status_code=400, detail="Cannot update a directory")
    if not _check_file_permission(db, file_id, user_id, roles, "write"):
        raise HTTPException(status_code=403, detail="No permission to update this file")

    # Read new content
    content = file.file.read()
    ext = file.filename.rsplit(".", 1)[-1] if "." in (file.filename or "") else ""
    storage_name = f"{uuid.uuid4().hex}.{ext}" if ext else uuid.uuid4().hex

    # Replace storage
    minio_client = get_minio_client()
    if minio_client:
        minio_client.put_object(settings.MINIO_BUCKET, storage_name,
                                io.BytesIO(content), len(content))
        f.storage_url = f"{settings.MINIO_ENDPOINT}/{settings.MINIO_BUCKET}/{storage_name}"
    else:
        local_dir = os.path.join(os.path.dirname(__file__), "storage")
        os.makedirs(local_dir, exist_ok=True)
        local_path = os.path.join(local_dir, storage_name)
        with open(local_path, "wb") as fh:
            fh.write(content)
        f.storage_url = f"local://{storage_name}"

    # Update metadata
    f.size = len(content)
    f.mime_type = file.content_type
    f.file_name = file.filename or f.file_name

    # Reset status to draft
    f.status = "draft"
    f.review_comment = None
    f.reviewed_by = None
    f.reviewed_at = None

    # Mark all current activities as history
    db.query(FileActivity).filter(
        FileActivity.file_id == file_id,
        FileActivity.is_history == False,
    ).update({"is_history": True}, synchronize_session=False)

    db.commit()
    db.refresh(f)
    return _file_to_dict(f)


def update_file_text_content(db: Session, file_id: int, text_content: str,
                              user_id: int, roles: list[str]) -> dict:
    """Overwrite file content with raw text, reset status to draft."""
    f = db.get(FileRecord, file_id)
    if not f or f.deleted:
        raise HTTPException(status_code=404, detail="File not found")
    if f.is_directory:
        raise HTTPException(status_code=400, detail="Cannot update a directory")
    if not _check_file_permission(db, file_id, user_id, roles, "write"):
        raise HTTPException(status_code=403, detail="No permission to update this file")

    content = text_content.encode("utf-8")
    storage_name = f"{uuid.uuid4().hex}.txt"

    minio_client = get_minio_client()
    if minio_client:
        minio_client.put_object(settings.MINIO_BUCKET, storage_name,
                                io.BytesIO(content), len(content))
        f.storage_url = f"{settings.MINIO_ENDPOINT}/{settings.MINIO_BUCKET}/{storage_name}"
    else:
        local_dir = os.path.join(os.path.dirname(__file__), "storage")
        os.makedirs(local_dir, exist_ok=True)
        local_path = os.path.join(local_dir, storage_name)
        with open(local_path, "wb") as fh:
            fh.write(content)
        f.storage_url = f"local://{storage_name}"

    # Update metadata
    f.size = len(content)
    f.mime_type = "text/plain; charset=utf-8"

    # Reset status to draft
    f.status = "draft"
    f.review_comment = None
    f.reviewed_by = None
    f.reviewed_at = None

    # Mark all current activities as history
    db.query(FileActivity).filter(
        FileActivity.file_id == file_id,
        FileActivity.is_history == False,
    ).update({"is_history": True}, synchronize_session=False)

    db.commit()
    db.refresh(f)
    return _file_to_dict(f)


def ensure_missing_permissions(db: Session):
    """Ensure file:permission:manage and doc:edit exist and are properly assigned.
    Safe to call on every startup — skips if already seeded.
    """
    # ── file:permission:manage → ADMIN ──
    perm = db.query(Permission).filter(
        Permission.name == "file:permission:manage", Permission.deleted == False
    ).first()
    if not perm:
        perm = Permission(name="file:permission:manage",
                          description="Manage file role permissions",
                          category="file")
        db.add(perm)
        db.commit()
        db.refresh(perm)

    admin_role = db.query(Role).filter(Role.name == "ADMIN", Role.deleted == False).first()
    if admin_role and perm not in admin_role.permissions:
        admin_role.permissions.append(perm)
        db.commit()

    # ── doc:edit → EDITOR ──
    edit_perm = db.query(Permission).filter(
        Permission.name == "doc:edit", Permission.deleted == False
    ).first()
    if not edit_perm:
        edit_perm = Permission(name="doc:edit",
                               description="Inline edit file text content",
                               category="document")
        db.add(edit_perm)
        db.commit()
        db.refresh(edit_perm)

    editor_role = db.query(Role).filter(Role.name == "EDITOR", Role.deleted == False).first()
    if editor_role and edit_perm not in editor_role.permissions:
        editor_role.permissions.append(edit_perm)
        db.commit()

    _ensure_hierarchy_integrity(db)


def _ensure_hierarchy_integrity(db: Session):
    """Repair broken hierarchy chains caused by previous buggy delete_role code.

    The old delete_role used `RoleHierarchy.inherited_role_id == role_id` to delete
    hierarchy entries, which removed the ADMIN → {deleted_role} link instead of
    rewiring it. This left ADMIN with no valid inherited roles, breaking the entire
    permission inheritance chain. This function restores ADMIN → MANAGER when needed.
    """
    admin = db.query(Role).filter(Role.name == "ADMIN", Role.deleted == False).first()
    manager = db.query(Role).filter(Role.name == "MANAGER", Role.deleted == False).first()
    if not admin or not manager:
        return

    # Check if ADMIN has any non-deleted inherited role that eventually reaches MANAGER
    def _has_chain_to(source_id, target_id, seen=None):
        if seen is None:
            seen = set()
        if source_id == target_id:
            return True
        if source_id in seen:
            return False
        seen.add(source_id)
        role = db.get(Role, source_id)
        if not role or role.deleted:
            return False
        for ir in role.inherited_roles:
            if _has_chain_to(ir.id, target_id, seen):
                return True
        return False

    if _has_chain_to(admin.id, manager.id):
        return

    # Rewire ADMIN away from any deleted role to MANAGER
    for ir in list(admin.inherited_roles):
        if ir.deleted:
            hier = db.query(RoleHierarchy).filter(
                RoleHierarchy.role_id == admin.id,
                RoleHierarchy.inherited_role_id == ir.id,
            ).first()
            if hier:
                hier.inherited_role_id = manager.id
                db.commit()
                return

    # ADMIN has no inherited roles at all — add direct ADMIN → MANAGER
    existing = db.query(RoleHierarchy).filter(
        RoleHierarchy.role_id == admin.id,
        RoleHierarchy.inherited_role_id == manager.id,
    ).first()
    if not existing:
        db.add(RoleHierarchy(role_id=admin.id, inherited_role_id=manager.id))
        db.commit()


def ensure_missing_columns(db: Session):
    """Auto-add missing columns to existing DB tables (safe no-op if already present)."""
    from sqlalchemy import text, inspect
    inspector = inspect(db.bind)

    # file_records columns
    existing_cols = {c["name"] for c in inspector.get_columns("file_records")}
    migrations = [
        ("status", "VARCHAR(20) DEFAULT 'draft'"),
        ("review_comment", "VARCHAR(500)"),
        ("reviewed_by", "BIGINT"),
        ("reviewed_at", "DATETIME"),
    ]
    for col_name, col_def in migrations:
        if col_name not in existing_cols:
            db.execute(text(f"ALTER TABLE file_records ADD COLUMN {col_name} {col_def}"))

    # users columns — account lockout
    user_cols = {c["name"] for c in inspector.get_columns("users")}
    user_migrations = [
        ("failed_login_attempts", "INTEGER DEFAULT 0"),
        ("locked_until", "DATETIME"),
    ]
    for col_name, col_def in user_migrations:
        if col_name not in user_cols:
            db.execute(text(f"ALTER TABLE users ADD COLUMN {col_name} {col_def}"))

    db.commit()


# ── Audit Service ──────────────────────────────────────────────────────────

def query_audit_logs(db: Session, page: int = 1, size: int = 20,
                     action: str = None, username: str = None,
                     start_date: str = None, end_date: str = None) -> dict:
    q = db.query(AuditLog).filter(AuditLog.deleted == False)
    if action:
        q = q.filter(AuditLog.action == action)
    if username:
        q = q.filter(AuditLog.username.like(f"%{username}%"))
    if start_date:
        q = q.filter(AuditLog.created_at >= f"{start_date} 00:00:00")
    if end_date:
        q = q.filter(AuditLog.created_at <= f"{end_date} 23:59:59")
    total = q.count()
    q = q.order_by(desc(AuditLog.created_at)).offset((page - 1) * size).limit(size)
    items = []
    for log in q:
        items.append({
            "id": log.id, "user_id": log.user_id, "username": log.username,
            "action": log.action, "detail": log.detail, "ip_address": log.ip_address,
            "success": log.success,
            "created_at": log.created_at.isoformat() if log.created_at else None,
        })
    return {"items": items, "total": total, "page": page, "size": size}


def delete_audit_log(db: Session, log_id: int):
    log = db.get(AuditLog, log_id)
    if not log or log.deleted:
        raise HTTPException(status_code=404, detail="Audit log not found")
    log.deleted = True
    db.commit()


def batch_delete_audit_logs(db: Session, log_ids: list[int]):
    db.query(AuditLog).filter(
        AuditLog.id.in_(log_ids), AuditLog.deleted == False
    ).update({"deleted": True}, synchronize_session=False)
    db.commit()


def export_audit_logs(db: Session, action: str = None, username: str = None,
                      start_date: str = None, end_date: str = None) -> str:
    q = db.query(AuditLog).filter(AuditLog.deleted == False)
    if action:
        q = q.filter(AuditLog.action == action)
    if username:
        q = q.filter(AuditLog.username.like(f"%{username}%"))
    if start_date:
        q = q.filter(AuditLog.created_at >= f"{start_date} 00:00:00")
    if end_date:
        q = q.filter(AuditLog.created_at <= f"{end_date} 23:59:59")
    logs = q.order_by(desc(AuditLog.created_at)).all()
    output = io.StringIO()
    output.write('')  # UTF-8 BOM，确保 Excel 直接打开时中文不乱码
    writer = csv.writer(output)
    writer.writerow(["ID", "UserID", "Username", "Action", "Detail", "IP", "Success", "CreatedAt"])
    for log in logs:
        writer.writerow([log.id, log.user_id, log.username, log.action,
                         log.detail, log.ip_address, log.success,
                         log.created_at.isoformat() if log.created_at else ""])
    return output.getvalue()

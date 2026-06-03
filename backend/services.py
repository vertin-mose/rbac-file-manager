"""Business logic: auth, roles, files, audit."""

import csv
import io
import os
import uuid
from datetime import datetime
from typing import Optional

from fastapi import HTTPException, UploadFile
from minio import Minio
from sqlalchemy import desc
from sqlalchemy.orm import Session

from auth import create_token, hash_password, verify_password
from config import settings
from models import (
    AuditLog, FilePermission, FileRecord, Permission, Role, RoleHierarchy, RolePermission, User, UserRole,
)


# ── Helpers ────────────────────────────────────────────────────────────────

def get_minio_client() -> Optional[Minio]:
    try:
        url = settings.MINIO_ENDPOINT.replace("http://", "").replace("https://", "")
        client = Minio(url, access_key=settings.MINIO_ACCESS_KEY,
                       secret_key=settings.MINIO_SECRET_KEY, secure=False)
        if not client.bucket_exists(settings.MINIO_BUCKET):
            client.make_bucket(settings.MINIO_BUCKET)
        return client
    except Exception:
        return None


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
        if not role or role.deleted:
            return
        for p in role.permissions:
            if not p.deleted:
                result.add(p.name)
        for ir in role.inherited_roles:
            collect(ir.id)

    collect(role_id)
    return result


# ── Auth Service ───────────────────────────────────────────────────────────

# Role display names & levels (for enterprise document management)
ROLE_DISPLAY = {
    'SUPER_ADMIN': '超级管理员',
    'ADMIN': '系统管理员',
    'MANAGER': '部门经理',
    'EDITOR': '文档编辑员',
    'REVIEWER': '文档审核员',
    'VIEWER': '外部访客',
}
ROLE_LEVEL = {
    'SUPER_ADMIN': 1,
    'ADMIN': 2,
    'MANAGER': 3,
    'EDITOR': 4,
    'REVIEWER': 4,
    'VIEWER': 5,
}

# Override the garbled seed/display text with canonical role labels and descriptions.
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
    'ADMIN': '负责用户、角色、审计导出和系统备份等管理工作。',
    'MANAGER': '管理部门文档和成员，可审批、删除文档并查看审计日志。',
    'EDITOR': '负责创建、编辑、共享文档，并参与评论协作。',
    'REVIEWER': '负责审阅文档、添加评论与批注，并提出修改建议。',
    'VIEWER': '仅可浏览、检索和导出文档内容。',
}


def login(db: Session, username: str, password: str, ip: str = "") -> dict:
    user = db.query(User).filter(User.username == username, User.deleted == False).first()
    if not user or not verify_password(password, user.password):
        record_audit(db, user.id if user else 0, username, "LOGIN_FAILED",
                     detail=f"用户{username}登录失败", ip=ip, success=False)
        raise HTTPException(status_code=401, detail="Invalid username or password")
    if not user.enabled:
        raise HTTPException(status_code=403, detail="Account disabled")

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


def create_role(db: Session, name: str, description: str = "", permission_ids: list[int] = None) -> dict:
    exists = db.query(Role).filter(Role.name == name, Role.deleted == False).first()
    if exists:
        raise HTTPException(status_code=409, detail="Role name already exists")
    role = Role(name=name, description=description)
    if permission_ids:
        perms = db.query(Permission).filter(Permission.id.in_(permission_ids)).all()
        role.permissions = perms
    db.add(role)
    db.commit()
    db.refresh(role)
    return get_role(db, role.id)


def update_role(db: Session, role_id: int, name: Optional[str] = None,
                description: Optional[str] = None) -> dict:
    role = db.get(Role, role_id)
    if not role or role.deleted:
        raise HTTPException(status_code=404, detail="Role not found")
    if name:
        existing = db.query(Role).filter(Role.name == name, Role.id != role_id,
                                          Role.deleted == False).first()
        if existing:
            raise HTTPException(status_code=409, detail="Role name already exists")
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
    role.permissions = []
    role.inherited_roles = []
    db.query(UserRole).filter(UserRole.role_id == role_id).delete(synchronize_session=False)
    db.query(RolePermission).filter(RolePermission.role_id == role_id).delete(synchronize_session=False)
    db.query(RoleHierarchy).filter(
        RoleHierarchy.inherited_role_id == role_id
    ).delete(synchronize_session=False)
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


# ── File Service ───────────────────────────────────────────────────────────

def _is_privileged_role(roles: list[str]) -> bool:
    return bool(roles and set(roles) & {"SUPER_ADMIN", "ADMIN"})


def _check_file_permission(db: Session, file_id: int, user_id: int,
                           roles: list[str], permission_type: str) -> bool:
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

    # Walk up the directory tree to check user-level and role-level permissions
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
    return False


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
            return False

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
    return _file_to_dict(f)


def approve_file(db: Session, file_id: int, approver_id: int,
                 approved: bool = True, comment: str = "") -> dict:
    """Approve or reject a file — sets status to 'approved' or 'rejected'."""
    f = db.get(FileRecord, file_id)
    if not f or f.deleted:
        raise HTTPException(status_code=404, detail="File not found")
    if f.is_directory:
        raise HTTPException(status_code=400, detail="Directories cannot be approved")
    from datetime import datetime as dt
    f.status = "approved" if approved else "rejected"
    f.review_comment = comment or ""
    f.reviewed_by = approver_id
    f.reviewed_at = dt.now()
    db.commit()
    db.refresh(f)
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


def ensure_missing_permissions(db: Session):
    """Ensure file:permission:manage exists and is assigned to ADMIN role.
    Safe to call on every startup — skips if already seeded.
    """
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
    writer = csv.writer(output)
    writer.writerow(["ID", "UserID", "Username", "Action", "Detail", "IP", "Success", "CreatedAt"])
    for log in logs:
        writer.writerow([log.id, log.user_id, log.username, log.action,
                         log.detail, log.ip_address, log.success,
                         log.created_at.isoformat() if log.created_at else ""])
    return output.getvalue()

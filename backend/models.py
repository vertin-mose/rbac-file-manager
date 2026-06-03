"""SQLAlchemy ORM models + Pydantic request/response schemas."""

from datetime import datetime
from typing import Optional
from sqlalchemy import Column, Integer, String, Boolean, BigInteger, DateTime, Text, ForeignKey
from sqlalchemy.orm import backref, declarative_base, relationship
from pydantic import BaseModel

# ── SQLAlchemy ORM Models ──────────────────────────────────────────────────

Base = declarative_base()


class User(Base):
    __tablename__ = "users"
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    username = Column(String(50), unique=True, nullable=False)
    password = Column(String(255), nullable=False)
    display_name = Column(String(100))
    email = Column(String(100))
    enabled = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    deleted = Column(Boolean, default=False)

    roles = relationship("Role", secondary="user_roles", lazy="selectin")


class Role(Base):
    __tablename__ = "roles"
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    name = Column(String(50), unique=True, nullable=False)
    description = Column(String(200))
    enabled = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    deleted = Column(Boolean, default=False)

    permissions = relationship("Permission", secondary="role_permissions", lazy="selectin")
    inherited_roles = relationship(
        "Role", secondary="role_hierarchy",
        primaryjoin="Role.id == role_hierarchy.c.role_id",
        secondaryjoin="Role.id == role_hierarchy.c.inherited_role_id",
        lazy="selectin"
    )


class Permission(Base):
    __tablename__ = "permissions"
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    name = Column(String(100), unique=True, nullable=False)
    description = Column(String(200))
    category = Column(String(50))
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    deleted = Column(Boolean, default=False)


class FileRecord(Base):
    __tablename__ = "file_records"
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    file_name = Column(String(500), nullable=False)
    file_path = Column(String(1000))
    parent_id = Column(BigInteger, ForeignKey("file_records.id"))
    is_directory = Column(Boolean, default=False)
    size = Column(BigInteger, default=0)
    mime_type = Column(String(100))
    owner_id = Column(BigInteger, ForeignKey("users.id"), nullable=False)
    storage_url = Column(String(1000))
    # Status for review workflow: draft → under_review → approved / rejected
    status = Column(String(20), default="draft")
    review_comment = Column(String(500))
    reviewed_by = Column(BigInteger, ForeignKey("users.id"))
    reviewed_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    deleted = Column(Boolean, default=False)

    children = relationship(
        "FileRecord",
        backref=backref("parent", remote_side=[id]),
        lazy="selectin"
    )
    owner = relationship("User", lazy="selectin")


class FilePermission(Base):
    __tablename__ = "file_permissions"
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    file_id = Column(BigInteger, ForeignKey("file_records.id"), nullable=False)
    user_id = Column(BigInteger, ForeignKey("users.id"))
    role_id = Column(BigInteger, ForeignKey("roles.id"))
    permission_type = Column(String(20), nullable=False)
    granted_at = Column(DateTime, default=datetime.now)


class AuditLog(Base):
    __tablename__ = "audit_logs"
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    user_id = Column(BigInteger, ForeignKey("users.id"), nullable=False)
    username = Column(String(50))
    action = Column(String(50), nullable=False)
    detail = Column(String(500))
    ip_address = Column(String(45))
    success = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    deleted = Column(Boolean, default=False)


# Junction tables (SQLAlchemy needs them for secondary=)
class UserRole(Base):
    __tablename__ = "user_roles"
    user_id = Column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    role_id = Column(BigInteger, ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True)


class RolePermission(Base):
    __tablename__ = "role_permissions"
    role_id = Column(BigInteger, ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True)
    permission_id = Column(BigInteger, ForeignKey("permissions.id", ondelete="CASCADE"), primary_key=True)


class RoleHierarchy(Base):
    __tablename__ = "role_hierarchy"
    role_id = Column(BigInteger, ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True)
    inherited_role_id = Column(BigInteger, ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True)


# ── Pydantic Schemas ───────────────────────────────────────────────────────

class ApiResponse:
    """Unified JSON response helper. Returns dict for FastAPI to serialize."""
    @staticmethod
    def success(data=None, message="success"):
        return {"code": 200, "message": message, "data": data, "timestamp": datetime.now().isoformat()}

    @staticmethod
    def error(code: int, message: str):
        return {"code": code, "message": message, "data": None, "timestamp": datetime.now().isoformat()}


# Auth
class LoginRequest(BaseModel):
    username: str
    password: str


class RegisterRequest(BaseModel):
    username: str
    password: str
    display_name: Optional[str] = None
    email: Optional[str] = None


class LoginResponse(BaseModel):
    token: str
    username: str
    roles: list[str]
    permissions: list[str]


# Role
class PermissionOut(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    category: Optional[str] = None


class RoleCreate(BaseModel):
    name: str
    description: Optional[str] = None
    permission_ids: list[int] = []


class RoleUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None


class RoleOut(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    permissions: list[PermissionOut] = []
    inherited_permissions: list[PermissionOut] = []


class PermissionsAssign(BaseModel):
    permission_ids: list[int]


class UserRoleAssign(BaseModel):
    role_ids: list[int]


# File
class FileOut(BaseModel):
    id: int
    file_name: str
    is_directory: bool
    size: int
    mime_type: Optional[str] = None
    owner_id: int
    parent_id: Optional[int] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class FileRename(BaseModel):
    file_name: str


class DirectoryCreate(BaseModel):
    file_name: str
    parent_id: int = 0


class FileShare(BaseModel):
    user_ids: list[int] = []
    role_ids: list[int] = []


class CommentCreate(BaseModel):
    content: str


# Audit
class AuditLogOut(BaseModel):
    id: int
    user_id: int
    username: Optional[str] = None
    action: str
    detail: Optional[str] = None
    ip_address: Optional[str] = None
    success: bool
    created_at: Optional[str] = None

"""
Shared pytest fixtures for the feat/file-user-permissions branch.
Uses in-memory SQLite with the updated seed data (23 permissions incl.
file:permission:manage, assigned to ADMIN).
"""

import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from models import (
    Base, User, Role, Permission, UserRole, RolePermission, RoleHierarchy, FileRecord,
)
from auth import hash_password


@pytest.fixture(scope="session")
def engine():
    eng = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
    )

    @event.listens_for(eng, "connect")
    def set_fk(conn, _):
        conn.execute("PRAGMA foreign_keys=ON")

    Base.metadata.create_all(eng)
    return eng


@pytest.fixture(scope="session")
def SessionFactory(engine):
    return sessionmaker(bind=engine)


@pytest.fixture()
def db(SessionFactory):
    session = SessionFactory()
    yield session
    session.rollback()
    session.close()


# ── Seed data ─────────────────────────────────────────────────────────────────

def _seed_permissions(session) -> dict[str, Permission]:
    perm_defs = [
        ("doc:create", "document"), ("doc:read", "document"),
        ("doc:update", "document"), ("doc:delete", "document"),
        ("doc:review", "document"), ("doc:approve", "document"),
        ("doc:comment", "document"), ("doc:share", "document"),
        ("doc:export", "document"), ("doc:edit", "document"),
        ("user:read", "user"), ("user:create", "user"),
        ("user:update", "user"), ("user:delete", "user"),
        ("role:read", "role"), ("role:create", "role"),
        ("role:update", "role"), ("role:delete", "role"),
        ("role:assign", "role"),
        ("audit:read", "audit"), ("audit:export", "audit"),
        ("system:config", "system"), ("system:backup", "system"),
        # NEW in this branch
        ("file:permission:manage", "file"),
    ]
    perms = {}
    for name, cat in perm_defs:
        p = Permission(name=name, category=cat, description=name)
        session.add(p)
        perms[name] = p
    session.flush()
    return perms


def _seed_roles(session, perms: dict[str, Permission]) -> dict[str, Role]:
    role_perms = {
        "VIEWER":     ["doc:read", "doc:export"],
        "REVIEWER":   ["doc:review", "doc:comment"],
        "EDITOR":     ["doc:create", "doc:update", "doc:edit", "doc:share", "doc:comment"],
        "MANAGER":    ["doc:delete", "doc:approve", "user:read", "role:read", "audit:read"],
        # ADMIN now gets file:permission:manage
        "ADMIN":      ["user:create", "user:update", "user:delete",
                       "role:create", "role:update", "role:delete", "role:assign",
                       "audit:export", "system:backup", "file:permission:manage"],
        "SUPER_ADMIN": ["system:config"],
    }
    roles = {}
    for name, owned in role_perms.items():
        r = Role(name=name, description=name)
        r.permissions = [perms[p] for p in owned]
        session.add(r)
        roles[name] = r
    session.flush()
    return roles


def _seed_hierarchy(session, roles: dict[str, Role]):
    links = [
        ("SUPER_ADMIN", "ADMIN"), ("ADMIN", "MANAGER"),
        ("MANAGER", "EDITOR"), ("MANAGER", "REVIEWER"),
        ("EDITOR", "VIEWER"), ("REVIEWER", "VIEWER"),
    ]
    for senior, junior in links:
        session.add(RoleHierarchy(role_id=roles[senior].id,
                                  inherited_role_id=roles[junior].id))
    session.flush()
    for r in roles.values():
        session.refresh(r)


@pytest.fixture()
def seeded_db(db):
    """Session pre-loaded with full seed data including file:permission:manage."""
    # Clear any leftover data from previous tests
    for table in reversed(Base.metadata.sorted_tables):
        db.execute(table.delete())
    perms = _seed_permissions(db)
    roles = _seed_roles(db, perms)
    _seed_hierarchy(db, roles)

    admin = User(username="admin", password=hash_password("admin123"),
                 display_name="Admin", enabled=True)
    viewer_user = User(username="viewer1", password=hash_password("viewer123"),
                       display_name="Viewer One", enabled=True)
    editor_user = User(username="editor1", password=hash_password("editor123"),
                       display_name="Editor One", enabled=True)
    db.add_all([admin, viewer_user, editor_user])
    db.flush()
    admin.roles = [roles["SUPER_ADMIN"]]
    viewer_user.roles = [roles["VIEWER"]]
    editor_user.roles = [roles["EDITOR"]]
    db.commit()

    return db, roles, perms, admin, viewer_user, editor_user

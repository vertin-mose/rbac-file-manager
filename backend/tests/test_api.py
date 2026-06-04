"""
FastAPI TestClient tests for all API routes in main.py.
Uses the same in-memory SQLite DB as unit tests via dependency overrides.
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from models import Base, User, Role, Permission, RoleHierarchy, FileRecord
from auth import hash_password, create_token


# ── DB Setup (scoped to module so state persists across related tests) ─────────

@pytest.fixture(scope="module")
def test_engine():
    eng = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})

    @event.listens_for(eng, "connect")
    def set_fk(conn, _):
        conn.execute("PRAGMA foreign_keys=ON")

    Base.metadata.create_all(eng)
    return eng


@pytest.fixture(scope="module")
def test_session_factory(test_engine):
    return sessionmaker(bind=test_engine)


@pytest.fixture(scope="module")
def seeded_session(test_session_factory):
    """Module-scoped session with full seed data."""
    db = test_session_factory()

    perm_defs = [
        ("doc:create","document"), ("doc:read","document"), ("doc:update","document"),
        ("doc:delete","document"), ("doc:review","document"), ("doc:approve","document"),
        ("doc:comment","document"), ("doc:share","document"), ("doc:export","document"),
        ("doc:edit","document"),
        ("user:read","user"), ("user:create","user"), ("user:update","user"),
        ("user:delete","user"),
        ("role:read","role"), ("role:create","role"), ("role:update","role"),
        ("role:delete","role"), ("role:assign","role"),
        ("audit:read","audit"), ("audit:export","audit"),
        ("system:config","system"), ("system:backup","system"),
        ("file:permission:manage","file"),
    ]
    perms = {}
    for name, cat in perm_defs:
        p = Permission(name=name, category=cat, description=name)
        db.add(p)
        perms[name] = p
    db.flush()

    role_perms = {
        "VIEWER":     ["doc:read", "doc:export"],
        "REVIEWER":   ["doc:review", "doc:comment"],
        "EDITOR":     ["doc:create", "doc:update", "doc:edit", "doc:share", "doc:comment"],
        "MANAGER":    ["doc:delete", "doc:approve", "user:read", "role:read", "audit:read"],
        "ADMIN":      ["user:create", "user:update", "user:delete",
                       "role:create", "role:update", "role:delete", "role:assign",
                       "audit:export", "system:backup", "file:permission:manage"],
        "SUPER_ADMIN": ["system:config"],
    }
    roles = {}
    for name, owned in role_perms.items():
        r = Role(name=name, description=name)
        r.permissions = [perms[p] for p in owned]
        db.add(r)
        roles[name] = r
    db.flush()

    hierarchy = [
        ("SUPER_ADMIN","ADMIN"), ("ADMIN","MANAGER"),
        ("MANAGER","EDITOR"), ("MANAGER","REVIEWER"),
        ("EDITOR","VIEWER"), ("REVIEWER","VIEWER"),
    ]
    for senior, junior in hierarchy:
        db.add(RoleHierarchy(role_id=roles[senior].id, inherited_role_id=roles[junior].id))

    admin = User(username="testadmin", password=hash_password("admin123"),
                 display_name="Test Admin", enabled=True)
    viewer = User(username="testviewer", password=hash_password("viewer123"),
                  display_name="Test Viewer", enabled=True)
    db.add_all([admin, viewer])
    db.flush()
    admin.roles = [roles["SUPER_ADMIN"]]
    viewer.roles = [roles["VIEWER"]]
    db.commit()

    yield db, roles, perms, admin, viewer
    db.close()


@pytest.fixture(scope="module")
def client(test_session_factory, seeded_session):
    """TestClient with DB dependency overridden to use in-memory SQLite."""
    import main
    from main import get_db

    def override_get_db():
        db = test_session_factory()
        try:
            yield db
        finally:
            db.close()

    main.app.dependency_overrides[get_db] = override_get_db
    with TestClient(main.app, raise_server_exceptions=False) as c:
        yield c
    main.app.dependency_overrides.clear()


@pytest.fixture(scope="module")
def admin_token(seeded_session):
    _, roles, _, admin, _ = seeded_session
    return create_token(admin.id, admin.username, ["SUPER_ADMIN"])


@pytest.fixture(scope="module")
def viewer_token(seeded_session):
    _, roles, _, _, viewer = seeded_session
    return create_token(viewer.id, viewer.username, ["VIEWER"])


def auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


# ── Health ────────────────────────────────────────────────────────────────────

class TestHealthAPI:
    def test_health_ok(self, client):
        r = client.get("/api/health")
        assert r.status_code == 200
        assert r.json()["status"] == "ok"


# ── Auth API ──────────────────────────────────────────────────────────────────

class TestAuthAPI:
    def test_login_success(self, client):
        r = client.post("/api/auth/login",
                        json={"username": "testadmin", "password": "admin123"})
        assert r.status_code == 200
        d = r.json()["data"]
        assert "token" in d
        assert "SUPER_ADMIN" in d["roles"]

    def test_login_wrong_password(self, client):
        r = client.post("/api/auth/login",
                        json={"username": "testadmin", "password": "wrong"})
        assert r.status_code == 401

    def test_register_new_user(self, client):
        r = client.post("/api/auth/register",
                        json={"username": "api_test_user_new",
                              "password": "TestPass123!"})
        assert r.status_code == 200
        assert r.json()["data"]["username"] == "api_test_user_new"

    def test_register_duplicate(self, client):
        client.post("/api/auth/register",
                    json={"username": "dup_api_user", "password": "pass"})
        r = client.post("/api/auth/register",
                        json={"username": "dup_api_user", "password": "pass"})
        assert r.status_code == 409

    def test_logout_requires_auth(self, client):
        r = client.post("/api/auth/logout")
        assert r.status_code == 401

    def test_logout_success(self, client, admin_token):
        r = client.post("/api/auth/logout", headers=auth(admin_token))
        assert r.status_code == 200


# ── Role API ──────────────────────────────────────────────────────────────────

class TestRoleAPI:
    def test_list_roles_requires_auth(self, client):
        r = client.get("/api/roles")
        assert r.status_code == 401

    def test_list_roles_viewer_forbidden(self, client, viewer_token):
        r = client.get("/api/roles", headers=auth(viewer_token))
        assert r.status_code == 403

    def test_list_roles_admin(self, client, admin_token):
        r = client.get("/api/roles", headers=auth(admin_token))
        assert r.status_code == 200
        roles = r.json()["data"]
        names = {rr["name"] for rr in roles}
        assert names == {"SUPER_ADMIN", "ADMIN", "MANAGER", "EDITOR", "REVIEWER", "VIEWER"}

    def test_get_role_hierarchy(self, client, admin_token):
        r = client.get("/api/roles/hierarchy", headers=auth(admin_token))
        assert r.status_code == 200
        hier = r.json()["data"]
        assert any(h["role_name"] == "SUPER_ADMIN" and h["inherited_role_name"] == "ADMIN"
                   for h in hier)

    def test_create_update_delete_role(self, client, admin_token):
        # Create
        r = client.post("/api/roles",
                        json={"name": "API_TEST_ROLE", "description": "test",
                              "permission_ids": []},
                        headers=auth(admin_token))
        assert r.status_code == 200
        role_id = r.json()["data"]["id"]

        # Update
        r2 = client.put(f"/api/roles/{role_id}",
                         json={"description": "updated"},
                         headers=auth(admin_token))
        assert r2.status_code == 200

        # Assign permissions
        r3 = client.put(f"/api/roles/{role_id}/permissions",
                         json={"permission_ids": [1, 2]},
                         headers=auth(admin_token))
        assert r3.status_code == 200

        # Delete
        r4 = client.delete(f"/api/roles/{role_id}", headers=auth(admin_token))
        assert r4.status_code == 200

        # Confirm gone
        r5 = client.get(f"/api/roles/{role_id}", headers=auth(admin_token))
        assert r5.status_code == 404

    def test_viewer_cannot_create_role(self, client, viewer_token):
        r = client.post("/api/roles",
                        json={"name": "HACK", "description": ""},
                        headers=auth(viewer_token))
        assert r.status_code == 403


# ── File API ──────────────────────────────────────────────────────────────────

class TestFileAPI:
    def test_list_root_files(self, client, admin_token):
        r = client.get("/api/files", headers=auth(admin_token))
        assert r.status_code == 200
        assert isinstance(r.json()["data"], list)

    def test_list_files_requires_auth(self, client):
        r = client.get("/api/files")
        assert r.status_code == 401

    def test_create_rename_delete_directory(self, client, admin_token):
        # Create
        r = client.post("/api/files/directory",
                         json={"file_name": "API Test Dir", "parent_id": 0},
                         headers=auth(admin_token))
        assert r.status_code == 200
        d = r.json()["data"]
        assert d["is_directory"] is True
        dir_id = d["id"]

        # Rename
        r2 = client.put(f"/api/files/{dir_id}",
                         json={"file_name": "Renamed Dir"},
                         headers=auth(admin_token))
        assert r2.status_code == 200
        assert r2.json()["data"]["file_name"] == "Renamed Dir"

        # Get detail
        r3 = client.get(f"/api/files/{dir_id}", headers=auth(admin_token))
        assert r3.status_code == 200

        # Delete
        r4 = client.delete(f"/api/files/{dir_id}", headers=auth(admin_token))
        assert r4.status_code == 200

        # Confirm deleted
        r5 = client.get(f"/api/files/{dir_id}", headers=auth(admin_token))
        assert r5.status_code == 404

    def test_get_nonexistent_file(self, client, admin_token):
        r = client.get("/api/files/999999", headers=auth(admin_token))
        assert r.status_code == 404

    def test_viewer_cannot_create_directory(self, client, viewer_token):
        r = client.post("/api/files/directory",
                         json={"file_name": "hacked_dir", "parent_id": 0},
                         headers=auth(viewer_token))
        assert r.status_code == 403

    def test_viewer_can_list_files(self, client, viewer_token):
        r = client.get("/api/files", headers=auth(viewer_token))
        assert r.status_code == 200

    def test_share_file(self, client, admin_token):
        r = client.post("/api/files/directory",
                         json={"file_name": "ShareTest", "parent_id": 0},
                         headers=auth(admin_token))
        dir_id = r.json()["data"]["id"]
        r2 = client.post(f"/api/files/{dir_id}/share",
                          json={"user_ids": [], "role_ids": [1]},
                          headers=auth(admin_token))
        assert r2.status_code == 200
        # cleanup
        client.delete(f"/api/files/{dir_id}", headers=auth(admin_token))

    def test_review_comment_approve_by_admin(self, client, admin_token):
        r = client.post("/api/files/directory",
                         json={"file_name": "ReviewTarget", "parent_id": 0},
                         headers=auth(admin_token))
        fid = r.json()["data"]["id"]
        for action in ["review", "approve", "comment"]:
            ra = client.post(f"/api/files/{fid}/{action}",
                              json={"content": f"test {action}"},
                              headers=auth(admin_token))
            assert ra.status_code == 200, f"{action} failed: {ra.json()}"
        client.delete(f"/api/files/{fid}", headers=auth(admin_token))


# ── Audit Log API ─────────────────────────────────────────────────────────────

class TestAuditLogAPI:
    def test_list_audit_logs_requires_auth(self, client):
        r = client.get("/api/audit-logs")
        assert r.status_code == 401

    def test_viewer_cannot_access_audit_logs(self, client, viewer_token):
        r = client.get("/api/audit-logs", headers=auth(viewer_token))
        assert r.status_code == 403

    def test_admin_can_list_audit_logs(self, client, admin_token):
        r = client.get("/api/audit-logs", headers=auth(admin_token))
        assert r.status_code == 200
        d = r.json()["data"]
        assert "items" in d and "total" in d

    def test_filter_by_action(self, client, admin_token):
        r = client.get("/api/audit-logs?action=LOGIN", headers=auth(admin_token))
        assert r.status_code == 200
        items = r.json()["data"]["items"]
        assert all(i["action"] == "LOGIN" for i in items)

    def test_pagination(self, client, admin_token):
        r = client.get("/api/audit-logs?page=1&size=3", headers=auth(admin_token))
        assert r.status_code == 200
        assert len(r.json()["data"]["items"]) <= 3

    def test_export_csv_requires_export_perm(self, client, admin_token, viewer_token):
        # Admin (SUPER_ADMIN has audit:export) should succeed
        r = client.get("/api/audit-logs/export", headers=auth(admin_token))
        assert r.status_code == 200
        # Viewer lacks audit:export
        r2 = client.get("/api/audit-logs/export", headers=auth(viewer_token))
        assert r2.status_code == 403

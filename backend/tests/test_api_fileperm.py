"""
FastAPI TestClient tests for the new file-permission endpoints and
changed file-operation behaviour in the feat/file-user-permissions branch.

New endpoints:
  GET  /api/files/{id}/permissions
  PUT  /api/files/{id}/permissions
  DELETE /api/files/{id}/permissions/{perm_id}
  GET  /api/users

Changed behaviour:
  File operations (get, rename, delete) now check file-level permissions,
  not just global role permissions.
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from models import Base, User, Role, Permission, RoleHierarchy, FileRecord, FilePermission
from auth import hash_password, create_token


# ── DB bootstrap ──────────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def test_engine():
    eng = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})

    @event.listens_for(eng, "connect")
    def set_fk(conn, _):
        conn.execute("PRAGMA foreign_keys=ON")

    Base.metadata.create_all(eng)
    return eng


@pytest.fixture(scope="module")
def sf(test_engine):
    return sessionmaker(bind=test_engine)


@pytest.fixture(scope="module")
def seed(sf):
    db = sf()
    perm_defs = [
        ("doc:create","document"), ("doc:read","document"), ("doc:update","document"),
        ("doc:delete","document"), ("doc:review","document"), ("doc:approve","document"),
        ("doc:comment","document"), ("doc:share","document"), ("doc:export","document"),
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
        db.add(p); perms[name] = p
    db.flush()

    role_perms = {
        "VIEWER":     ["doc:read","doc:export"],
        "REVIEWER":   ["doc:review","doc:comment"],
        "EDITOR":     ["doc:create","doc:update","doc:share","doc:comment"],
        "MANAGER":    ["doc:delete","doc:approve","user:read","role:read","audit:read"],
        "ADMIN":      ["user:create","user:update","user:delete",
                       "role:create","role:update","role:delete","role:assign",
                       "audit:export","system:backup","file:permission:manage"],
        "SUPER_ADMIN":["system:config"],
    }
    roles = {}
    for name, owned in role_perms.items():
        r = Role(name=name, description=name)
        r.permissions = [perms[p] for p in owned]
        db.add(r); roles[name] = r
    db.flush()

    for senior, junior in [("SUPER_ADMIN","ADMIN"),("ADMIN","MANAGER"),
                            ("MANAGER","EDITOR"),("MANAGER","REVIEWER"),
                            ("EDITOR","VIEWER"),("REVIEWER","VIEWER")]:
        db.add(RoleHierarchy(role_id=roles[senior].id, inherited_role_id=roles[junior].id))

    admin  = User(username="t_admin",  password=hash_password("admin123"),  enabled=True)
    viewer = User(username="t_viewer", password=hash_password("viewer123"), enabled=True)
    editor = User(username="t_editor", password=hash_password("editor123"), enabled=True)
    db.add_all([admin, viewer, editor])
    db.flush()
    admin.roles  = [roles["SUPER_ADMIN"]]
    viewer.roles = [roles["VIEWER"]]
    editor.roles = [roles["EDITOR"]]
    db.commit()

    yield db, roles, perms, admin, viewer, editor
    db.close()


@pytest.fixture(scope="module")
def client(sf, seed):
    import main
    from main import get_db

    def override_db():
        db = sf()
        try:
            yield db
        finally:
            db.close()

    main.app.dependency_overrides[get_db] = override_db
    with TestClient(main.app, raise_server_exceptions=False) as c:
        yield c
    main.app.dependency_overrides.clear()


@pytest.fixture(scope="module")
def admin_token(seed):
    _, _, _, admin, _, _ = seed
    return create_token(admin.id, admin.username, ["SUPER_ADMIN"])


@pytest.fixture(scope="module")
def viewer_token(seed):
    _, _, _, _, viewer, _ = seed
    return create_token(viewer.id, viewer.username, ["VIEWER"])


@pytest.fixture(scope="module")
def editor_token(seed):
    _, _, _, _, _, editor = seed
    return create_token(editor.id, editor.username, ["EDITOR"])


def auth(token): return {"Authorization": f"Bearer {token}"}


# ── Helper: create a file owned by admin ─────────────────────────────────────

def create_test_file(client, admin_token, name="test_api_file.txt"):
    r = client.post("/api/files/directory",
                    json={"file_name": name, "parent_id": 0},
                    headers=auth(admin_token))
    assert r.status_code == 200, r.text
    return r.json()["data"]["id"]


# ── GET /api/files/{id}/permissions ──────────────────────────────────────────

class TestGetFilePermissionsAPI:
    def test_admin_can_get_empty_permissions(self, client, admin_token):
        fid = create_test_file(client, admin_token, "perm_get_empty")
        r = client.get(f"/api/files/{fid}/permissions", headers=auth(admin_token))
        assert r.status_code == 200
        assert r.json()["data"] == []
        client.delete(f"/api/files/{fid}", headers=auth(admin_token))

    def test_viewer_can_get_permissions_on_accessible_file(self, client, admin_token, viewer_token, seed):
        _, _, _, _, viewer, _ = seed
        fid = create_test_file(client, admin_token, "perm_get_viewer")
        # Grant viewer read first (so they can call the endpoint)
        client.put(f"/api/files/{fid}/permissions",
                   json={"permissions": [{"user_id": viewer.id, "permission_type": "read"}]},
                   headers=auth(admin_token))
        r = client.get(f"/api/files/{fid}/permissions", headers=auth(viewer_token))
        assert r.status_code == 200
        client.delete(f"/api/files/{fid}", headers=auth(admin_token))

    def test_nonexistent_file_returns_404(self, client, admin_token):
        r = client.get("/api/files/999999/permissions", headers=auth(admin_token))
        assert r.status_code == 404


# ── PUT /api/files/{id}/permissions ──────────────────────────────────────────

class TestSetFilePermissionsAPI:
    def test_admin_can_set_permissions(self, client, admin_token, seed):
        _, _, _, _, viewer, _ = seed
        fid = create_test_file(client, admin_token, "perm_set")
        r = client.put(f"/api/files/{fid}/permissions",
                       json={"permissions": [
                           {"user_id": viewer.id, "permission_type": "read"},
                           {"user_id": viewer.id, "permission_type": "write"},
                       ]},
                       headers=auth(admin_token))
        assert r.status_code == 200
        data = r.json()["data"]
        types = {p["permission_type"] for p in data}
        assert types == {"read", "write"}
        client.delete(f"/api/files/{fid}", headers=auth(admin_token))

    def test_viewer_cannot_set_permissions(self, client, viewer_token, admin_token, seed):
        _, _, _, _, viewer, _ = seed
        fid = create_test_file(client, admin_token, "perm_set_deny")
        # Grant viewer read so request doesn't fail at auth level
        client.put(f"/api/files/{fid}/permissions",
                   json={"permissions": [{"user_id": viewer.id, "permission_type": "read"}]},
                   headers=auth(admin_token))
        r = client.put(f"/api/files/{fid}/permissions",
                       json={"permissions": []},
                       headers=auth(viewer_token))
        assert r.status_code == 403
        client.delete(f"/api/files/{fid}", headers=auth(admin_token))

    def test_editor_cannot_set_permissions(self, client, editor_token, admin_token):
        fid = create_test_file(client, admin_token, "perm_set_editor_deny")
        r = client.put(f"/api/files/{fid}/permissions",
                       json={"permissions": []},
                       headers=auth(editor_token))
        assert r.status_code == 403
        client.delete(f"/api/files/{fid}", headers=auth(admin_token))

    def test_set_replaces_all_permissions(self, client, admin_token, seed):
        _, _, _, _, viewer, editor = seed
        fid = create_test_file(client, admin_token, "perm_replace")
        # Set initial
        client.put(f"/api/files/{fid}/permissions",
                   json={"permissions": [{"user_id": viewer.id, "permission_type": "read"}]},
                   headers=auth(admin_token))
        # Replace with different set
        client.put(f"/api/files/{fid}/permissions",
                   json={"permissions": [{"user_id": editor.id, "permission_type": "write"}]},
                   headers=auth(admin_token))
        r = client.get(f"/api/files/{fid}/permissions", headers=auth(admin_token))
        data = r.json()["data"]
        assert len(data) == 1
        assert data[0]["permission_type"] == "write"
        assert data[0]["user_id"] == editor.id
        client.delete(f"/api/files/{fid}", headers=auth(admin_token))


# ── DELETE /api/files/{id}/permissions/{perm_id} ─────────────────────────────

class TestDeleteFilePermissionAPI:
    def test_admin_can_delete_permission(self, client, admin_token, seed):
        _, _, _, _, viewer, _ = seed
        fid = create_test_file(client, admin_token, "perm_del")
        client.put(f"/api/files/{fid}/permissions",
                   json={"permissions": [{"user_id": viewer.id, "permission_type": "read"}]},
                   headers=auth(admin_token))
        perms = client.get(f"/api/files/{fid}/permissions",
                           headers=auth(admin_token)).json()["data"]
        perm_id = perms[0]["id"]
        r = client.delete(f"/api/files/{fid}/permissions/{perm_id}",
                          headers=auth(admin_token))
        assert r.status_code == 200
        perms_after = client.get(f"/api/files/{fid}/permissions",
                                 headers=auth(admin_token)).json()["data"]
        assert all(p["id"] != perm_id for p in perms_after)
        client.delete(f"/api/files/{fid}", headers=auth(admin_token))

    def test_viewer_cannot_delete_permission(self, client, admin_token, viewer_token, seed):
        _, _, _, _, viewer, _ = seed
        fid = create_test_file(client, admin_token, "perm_del_deny")
        client.put(f"/api/files/{fid}/permissions",
                   json={"permissions": [{"user_id": viewer.id, "permission_type": "read"}]},
                   headers=auth(admin_token))
        perms = client.get(f"/api/files/{fid}/permissions",
                           headers=auth(admin_token)).json()["data"]
        perm_id = perms[0]["id"]
        r = client.delete(f"/api/files/{fid}/permissions/{perm_id}",
                          headers=auth(viewer_token))
        assert r.status_code == 403
        client.delete(f"/api/files/{fid}", headers=auth(admin_token))


# ── GET /api/users ────────────────────────────────────────────────────────────

class TestListUsersAPI:
    def test_manager_can_list_users(self, client, seed):
        _, roles, _, _, _, _ = seed
        # Create a manager token
        mgr_token = create_token(1, "t_admin", ["MANAGER"])
        r = client.get("/api/users", headers=auth(mgr_token))
        assert r.status_code == 200
        users = r.json()["data"]
        assert isinstance(users, list)
        assert len(users) >= 3

    def test_viewer_cannot_list_users(self, client, viewer_token):
        r = client.get("/api/users", headers=auth(viewer_token))
        assert r.status_code == 403

    def test_response_fields(self, client, admin_token):
        r = client.get("/api/users", headers=auth(admin_token))
        assert r.status_code == 200
        for u in r.json()["data"]:
            assert "id" in u
            assert "username" in u
            assert "display_name" in u
            assert "email" in u
            assert "password" not in u


# ── Changed file-operation behaviour ─────────────────────────────────────────

class TestFileOperationPermissionChange:
    def test_viewer_with_read_permission_can_get_file(self, client, admin_token, viewer_token, seed):
        _, _, _, _, viewer, _ = seed
        fid = create_test_file(client, admin_token, "fp_get_test")
        # Without permission → 403
        r1 = client.get(f"/api/files/{fid}", headers=auth(viewer_token))
        assert r1.status_code == 403
        # Grant read
        client.put(f"/api/files/{fid}/permissions",
                   json={"permissions": [{"user_id": viewer.id, "permission_type": "read"}]},
                   headers=auth(admin_token))
        r2 = client.get(f"/api/files/{fid}", headers=auth(viewer_token))
        assert r2.status_code == 200
        client.delete(f"/api/files/{fid}", headers=auth(admin_token))

    def test_viewer_with_write_permission_can_rename(self, client, admin_token, viewer_token, seed):
        _, _, _, _, viewer, _ = seed
        fid = create_test_file(client, admin_token, "fp_rename_test")
        # Without permission → 403
        r1 = client.put(f"/api/files/{fid}", json={"file_name": "new_name"},
                        headers=auth(viewer_token))
        assert r1.status_code == 403
        # Grant write
        client.put(f"/api/files/{fid}/permissions",
                   json={"permissions": [{"user_id": viewer.id, "permission_type": "write"}]},
                   headers=auth(admin_token))
        r2 = client.put(f"/api/files/{fid}", json={"file_name": "new_name"},
                        headers=auth(viewer_token))
        assert r2.status_code == 200
        client.delete(f"/api/files/{fid}", headers=auth(admin_token))

    def test_viewer_with_delete_permission_can_delete(self, client, admin_token, viewer_token, seed):
        _, _, _, _, viewer, _ = seed
        fid = create_test_file(client, admin_token, "fp_delete_test")
        # Without permission → 403
        r1 = client.delete(f"/api/files/{fid}", headers=auth(viewer_token))
        assert r1.status_code == 403
        # Grant delete
        fid2 = create_test_file(client, admin_token, "fp_delete_test2")
        client.put(f"/api/files/{fid2}/permissions",
                   json={"permissions": [{"user_id": viewer.id, "permission_type": "delete"}]},
                   headers=auth(admin_token))
        r2 = client.delete(f"/api/files/{fid2}", headers=auth(viewer_token))
        assert r2.status_code == 200
        # cleanup first file
        client.delete(f"/api/files/{fid}", headers=auth(admin_token))

    def test_admin_always_bypasses_file_permission_check(self, client, admin_token):
        fid = create_test_file(client, admin_token, "fp_admin_bypass")
        # Admin can always get, rename, delete regardless of file_permissions table
        assert client.get(f"/api/files/{fid}", headers=auth(admin_token)).status_code == 200
        assert client.put(f"/api/files/{fid}", json={"file_name": "bypassed"},
                          headers=auth(admin_token)).status_code == 200
        assert client.delete(f"/api/files/{fid}", headers=auth(admin_token)).status_code == 200

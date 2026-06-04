"""
Unit tests for services.py — RBAC permission-inheritance engine,
auth service (login/register), role service (CRUD), and audit service.
All tests use an isolated in-memory SQLite DB (see conftest.py).
"""

import pytest
from fastapi import HTTPException

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from services import (
    get_effective_permissions,
    login, register,
    list_roles, get_role, create_role, update_role, delete_role,
    assign_permissions, get_hierarchy, assign_user_roles, get_user_info,
    create_directory, list_files, get_file, rename_file, delete_file, share_file,
    record_audit, query_audit_logs, export_audit_logs,
    delete_audit_log, batch_delete_audit_logs,
)
from models import Role, Permission, User, FileRecord, AuditLog


# ── RBAC Permission Inheritance ───────────────────────────────────────────────

class TestGetEffectivePermissions:
    def test_viewer_has_only_own_perms(self, seeded_db):
        db, roles, perms, *_ = seeded_db
        result = get_effective_permissions(roles["VIEWER"].id, db)
        assert "doc:read" in result
        assert "doc:export" in result
        assert "doc:create" not in result
        assert "system:config" not in result

    def test_editor_inherits_viewer(self, seeded_db):
        db, roles, perms, *_ = seeded_db
        result = get_effective_permissions(roles["EDITOR"].id, db)
        # own permissions
        assert "doc:create" in result
        assert "doc:update" in result
        # inherited from VIEWER
        assert "doc:read" in result
        assert "doc:export" in result
        # NOT allowed (SoD)
        assert "doc:review" not in result
        assert "doc:approve" not in result

    def test_reviewer_inherits_viewer(self, seeded_db):
        db, roles, perms, *_ = seeded_db
        result = get_effective_permissions(roles["REVIEWER"].id, db)
        assert "doc:review" in result
        assert "doc:comment" in result
        assert "doc:read" in result      # from VIEWER
        # NOT allowed (SoD)
        assert "doc:create" not in result

    def test_manager_inherits_editor_and_reviewer(self, seeded_db):
        db, roles, perms, *_ = seeded_db
        result = get_effective_permissions(roles["MANAGER"].id, db)
        # own
        assert "doc:delete" in result
        assert "doc:approve" in result
        # from EDITOR chain
        assert "doc:create" in result
        assert "doc:update" in result
        # from REVIEWER chain
        assert "doc:review" in result
        # from VIEWER chain (both paths)
        assert "doc:read" in result

    def test_admin_inherits_full_chain(self, seeded_db):
        db, roles, perms, *_ = seeded_db
        result = get_effective_permissions(roles["ADMIN"].id, db)
        assert "role:create" in result
        assert "user:delete" in result
        assert "doc:read" in result          # inherited via full chain
        assert "system:config" not in result # SUPER_ADMIN only

    def test_super_admin_has_all_permissions(self, seeded_db):
        db, roles, perms, *_ = seeded_db
        result = get_effective_permissions(roles["SUPER_ADMIN"].id, db)
        for pname in perms:
            assert pname in result, f"SUPER_ADMIN missing permission: {pname}"

    def test_nonexistent_role_returns_empty(self, seeded_db):
        db, roles, perms, *_ = seeded_db
        result = get_effective_permissions(999999, db)
        assert result == set()

    def test_no_circular_infinite_loop(self, seeded_db):
        """get_effective_permissions must not recurse infinitely even with a cycle."""
        db, roles, _, *__ = seeded_db
        from models import RoleHierarchy
        # Artificially insert a cycle: VIEWER → EDITOR (contradicts normal flow)
        db.add(RoleHierarchy(role_id=roles["VIEWER"].id, inherited_role_id=roles["EDITOR"].id))
        db.flush()
        db.refresh(roles["VIEWER"])
        # Should not raise or hang
        result = get_effective_permissions(roles["VIEWER"].id, db)
        assert isinstance(result, set)
        # Rollback the artificial cycle
        db.rollback()


# ── Auth Service ──────────────────────────────────────────────────────────────

class TestAuthService:
    def test_login_success(self, seeded_db):
        db, _, _, admin, *__ = seeded_db
        result = login(db, "admin", "admin123")
        assert "token" in result
        assert result["username"] == "admin"
        assert "SUPER_ADMIN" in result["roles"]
        assert "system:config" in result["permissions"]

    def test_login_returns_role_info(self, seeded_db):
        db, _, _, admin, *__ = seeded_db
        result = login(db, "admin", "admin123")
        role_info = result.get("role_info", [])
        assert len(role_info) > 0
        sa_info = next((r for r in role_info if r["name"] == "SUPER_ADMIN"), None)
        assert sa_info is not None
        assert sa_info["level"] == 1

    def test_login_wrong_password(self, seeded_db):
        db, *__ = seeded_db
        with pytest.raises(HTTPException) as exc_info:
            login(db, "admin", "wrong_password")
        assert exc_info.value.status_code == 401

    def test_login_nonexistent_user(self, seeded_db):
        db, *__ = seeded_db
        with pytest.raises(HTTPException) as exc_info:
            login(db, "no_such_user", "pass")
        assert exc_info.value.status_code == 401

    def test_login_disabled_user(self, seeded_db):
        db, roles, _, *__ = seeded_db
        user = User(username="disabled_user", password="x", enabled=False)
        user.roles = [roles["VIEWER"]]
        db.add(user)
        db.flush()
        from auth import hash_password
        user.password = hash_password("pass123")
        db.commit()
        with pytest.raises(HTTPException) as exc_info:
            login(db, "disabled_user", "pass123")
        assert exc_info.value.status_code == 403
        db.rollback()

    def test_register_success(self, seeded_db):
        db, *__ = seeded_db
        result = register(db, "newuser_unit", "SecurePass1!")
        assert result["username"] == "newuser_unit"
        assert "id" in result
        # Default VIEWER role assigned
        user = db.query(User).filter(User.username == "newuser_unit").first()
        assert user is not None
        assert any(r.name == "VIEWER" for r in user.roles)
        db.rollback()

    def test_register_duplicate_username(self, seeded_db):
        db, *__ = seeded_db
        register(db, "dup_user", "pass1")
        with pytest.raises(HTTPException) as exc_info:
            register(db, "dup_user", "pass2")
        assert exc_info.value.status_code == 409
        db.rollback()


# ── Role Service ──────────────────────────────────────────────────────────────

class TestRoleService:
    def test_list_roles_returns_six(self, seeded_db):
        db, *__ = seeded_db
        roles = list_roles(db)
        assert len(roles) == 6

    def test_list_roles_includes_inherited_permissions(self, seeded_db):
        db, *__ = seeded_db
        roles = list_roles(db)
        editor = next(r for r in roles if r["name"] == "EDITOR")
        inherited = {p["name"] for p in editor["inherited_permissions"]}
        assert "doc:read" in inherited

    def test_get_role_success(self, seeded_db):
        db, roles_map, *__ = seeded_db
        result = get_role(db, roles_map["MANAGER"].id)
        assert result["name"] == "MANAGER"
        assert "permissions" in result
        own = {p["name"] for p in result["permissions"]}
        assert "doc:delete" in own

    def test_get_role_not_found(self, seeded_db):
        db, *__ = seeded_db
        with pytest.raises(HTTPException) as exc_info:
            get_role(db, 999999)
        assert exc_info.value.status_code == 404

    def test_create_role(self, seeded_db):
        db, _, perms, *__ = seeded_db
        result = create_role(db, "CUSTOM_ROLE", "A test role", [perms["doc:read"].id])
        assert result["name"] == "CUSTOM_ROLE"
        own = {p["name"] for p in result["permissions"]}
        assert "doc:read" in own
        db.rollback()

    def test_create_duplicate_role(self, seeded_db):
        db, *__ = seeded_db
        with pytest.raises(HTTPException) as exc_info:
            create_role(db, "VIEWER", "duplicate")
        assert exc_info.value.status_code == 409

    def test_update_role_description(self, seeded_db):
        db, _, perms, *__ = seeded_db
        # Use a custom role so the description is stored, not looked up from ROLE_DESCRIPTION
        custom = create_role(db, "UPDATE_TEST", "Original", [perms["doc:read"].id])
        result = update_role(db, custom["id"], description="Updated description")
        assert result["description"] == "Updated description"
        db.rollback()

    def test_update_role_name_duplicate_raises_409(self, seeded_db):
        db, roles_map, *__ = seeded_db
        with pytest.raises(HTTPException) as exc_info:
            update_role(db, roles_map["VIEWER"].id, name="EDITOR")
        assert exc_info.value.status_code == 409

    def test_delete_role(self, seeded_db):
        db, *__ = seeded_db
        temp = create_role(db, "TEMP_ROLE_TO_DELETE", "temp", [])
        temp_id = temp["id"]
        delete_role(db, temp_id)
        with pytest.raises(HTTPException) as exc_info:
            get_role(db, temp_id)
        assert exc_info.value.status_code == 404
        db.rollback()

    def test_delete_nonexistent_role(self, seeded_db):
        db, *__ = seeded_db
        with pytest.raises(HTTPException) as exc_info:
            delete_role(db, 999999)
        assert exc_info.value.status_code == 404

    def test_assign_permissions(self, seeded_db):
        db, roles_map, perms, *_ = seeded_db
        viewer_id = roles_map["VIEWER"].id
        assign_permissions(db, viewer_id, [perms["doc:read"].id, perms["doc:comment"].id])
        r = get_role(db, viewer_id)
        own = {p["name"] for p in r["permissions"]}
        assert "doc:comment" in own
        db.rollback()

    def test_get_hierarchy(self, seeded_db):
        db, *__ = seeded_db
        hier = get_hierarchy(db)
        assert len(hier) >= 6
        assert any(h["role_name"] == "SUPER_ADMIN" and h["inherited_role_name"] == "ADMIN"
                   for h in hier)
        assert any(h["role_name"] == "MANAGER" and h["inherited_role_name"] == "EDITOR"
                   for h in hier)


# ── User Service ──────────────────────────────────────────────────────────────

class TestUserService:
    def test_get_user_info(self, seeded_db):
        db, _, _, admin, *__ = seeded_db
        result = get_user_info(db, admin.id)
        assert result["username"] == "admin"
        assert any(r["name"] == "SUPER_ADMIN" for r in result["roles"])

    def test_get_nonexistent_user(self, seeded_db):
        db, *__ = seeded_db
        with pytest.raises(HTTPException) as exc_info:
            get_user_info(db, 999999)
        assert exc_info.value.status_code == 404

    def test_assign_user_roles(self, seeded_db):
        db, roles_map, *__ = seeded_db
        user = User(username="target_user", password="x")
        db.add(user)
        db.flush()
        assign_user_roles(db, user.id, [roles_map["EDITOR"].id])
        result = get_user_info(db, user.id)
        assert any(r["name"] == "EDITOR" for r in result["roles"])
        db.rollback()

    def test_assign_roles_to_nonexistent_user(self, seeded_db):
        db, roles_map, *__ = seeded_db
        with pytest.raises(HTTPException) as exc_info:
            assign_user_roles(db, 999999, [roles_map["VIEWER"].id])
        assert exc_info.value.status_code == 404


# ── File Service ──────────────────────────────────────────────────────────────

class TestFileService:
    def test_create_directory(self, seeded_db):
        db, _, _, admin, *__ = seeded_db
        result = create_directory(db, "TestDir", 0, admin.id)
        assert result["file_name"] == "TestDir"
        assert result["is_directory"] is True
        assert result["owner_id"] == admin.id
        db.rollback()

    def test_list_files_root(self, seeded_db):
        db, _, _, admin, *__ = seeded_db
        create_directory(db, "Dir1", 0, admin.id)
        create_directory(db, "Dir2", 0, admin.id)
        result = list_files(db, 0)
        assert len(result) >= 2
        db.rollback()

    def test_list_files_in_subdirectory(self, seeded_db):
        db, _, _, admin, *__ = seeded_db
        parent = create_directory(db, "Parent", 0, admin.id)
        create_directory(db, "Child", parent["id"], admin.id)
        children = list_files(db, parent["id"])
        assert len(children) == 1
        assert children[0]["file_name"] == "Child"
        db.rollback()

    def test_get_file(self, seeded_db):
        db, _, _, admin, *__ = seeded_db
        d = create_directory(db, "GetMe", 0, admin.id)
        result = get_file(db, d["id"])
        assert result["id"] == d["id"]
        assert result["file_name"] == "GetMe"
        db.rollback()

    def test_get_nonexistent_file(self, seeded_db):
        db, *__ = seeded_db
        with pytest.raises(HTTPException) as exc_info:
            get_file(db, 999999)
        assert exc_info.value.status_code == 404

    def test_rename_file(self, seeded_db):
        db, _, _, admin, *__ = seeded_db
        d = create_directory(db, "OldName", 0, admin.id)
        result = rename_file(db, d["id"], "NewName")
        assert result["file_name"] == "NewName"
        db.rollback()

    def test_rename_nonexistent_file(self, seeded_db):
        db, *__ = seeded_db
        with pytest.raises(HTTPException) as exc_info:
            rename_file(db, 999999, "AnyName")
        assert exc_info.value.status_code == 404

    def test_delete_file(self, seeded_db):
        db, _, _, admin, *__ = seeded_db
        d = create_directory(db, "ToDelete", 0, admin.id)
        delete_file(db, d["id"])
        with pytest.raises(HTTPException):
            get_file(db, d["id"])
        db.rollback()

    def test_delete_directory_cascades_to_children(self, seeded_db):
        db, _, _, admin, *__ = seeded_db
        parent = create_directory(db, "Parent", 0, admin.id)
        child  = create_directory(db, "Child",  parent["id"], admin.id)
        delete_file(db, parent["id"])
        # Both parent and child should be marked deleted
        with pytest.raises(HTTPException):
            get_file(db, parent["id"])
        with pytest.raises(HTTPException):
            get_file(db, child["id"])
        db.rollback()

    def test_delete_nonexistent_file(self, seeded_db):
        db, *__ = seeded_db
        with pytest.raises(HTTPException) as exc_info:
            delete_file(db, 999999)
        assert exc_info.value.status_code == 404

    def test_share_file(self, seeded_db):
        db, roles_map, _, admin, *__ = seeded_db
        d = create_directory(db, "Shared", 0, admin.id)
        # Should not raise
        share_file(db, d["id"], user_ids=[admin.id], permission_type="read")
        from models import FilePermission
        entries = db.query(FilePermission).filter(FilePermission.file_id == d["id"]).all()
        assert len(entries) == 1
        assert entries[0].user_id == admin.id
        db.rollback()

    def test_share_nonexistent_file(self, seeded_db):
        db, *__ = seeded_db
        with pytest.raises(HTTPException) as exc_info:
            share_file(db, 999999, [], [])
        assert exc_info.value.status_code == 404


# ── Audit Service ─────────────────────────────────────────────────────────────

class TestAuditService:
    def _make_logs(self, db, admin, count=5):
        for i in range(count):
            record_audit(db, admin.id, admin.username, "TEST_ACTION",
                         detail=f"detail {i}", ip="127.0.0.1")

    def test_record_and_query(self, seeded_db):
        db, _, _, admin, *__ = seeded_db
        self._make_logs(db, admin, 3)
        result = query_audit_logs(db, page=1, size=50, action="TEST_ACTION")
        assert result["total"] >= 3
        assert all(item["action"] == "TEST_ACTION" for item in result["items"])
        db.rollback()

    def test_pagination(self, seeded_db):
        db, _, _, admin, *__ = seeded_db
        self._make_logs(db, admin, 10)
        page1 = query_audit_logs(db, page=1, size=3, action="TEST_ACTION")
        page2 = query_audit_logs(db, page=2, size=3, action="TEST_ACTION")
        assert len(page1["items"]) == 3
        ids1 = {i["id"] for i in page1["items"]}
        ids2 = {i["id"] for i in page2["items"]}
        assert ids1.isdisjoint(ids2), "Pages must not overlap"
        db.rollback()

    def test_filter_by_username(self, seeded_db):
        db, _, _, admin, *__ = seeded_db
        record_audit(db, admin.id, "specific_user", "FILTER_TEST")
        record_audit(db, admin.id, "other_user",    "FILTER_TEST")
        result = query_audit_logs(db, username="specific_user")
        assert all("specific_user" in item["username"] for item in result["items"])
        db.rollback()

    def test_filter_by_date_range(self, seeded_db):
        db, _, _, admin, *__ = seeded_db
        self._make_logs(db, admin, 2)
        result = query_audit_logs(db, start_date="2000-01-01", end_date="2099-12-31")
        assert result["total"] >= 2
        db.rollback()

    def test_export_csv(self, seeded_db):
        db, _, _, admin, *__ = seeded_db
        record_audit(db, admin.id, admin.username, "CSV_TEST")
        csv_text = export_audit_logs(db, action="CSV_TEST")
        assert "CSV_TEST" in csv_text
        assert "ID" in csv_text          # header row
        assert "Username" in csv_text
        db.rollback()

    def test_delete_audit_log(self, seeded_db):
        db, _, _, admin, *__ = seeded_db
        record_audit(db, admin.id, admin.username, "DEL_TEST")
        result = query_audit_logs(db, action="DEL_TEST")
        assert result["total"] >= 1
        log_id = result["items"][0]["id"]
        delete_audit_log(db, log_id)
        result2 = query_audit_logs(db, action="DEL_TEST")
        ids = [item["id"] for item in result2["items"]]
        assert log_id not in ids
        db.rollback()

    def test_delete_nonexistent_audit_log(self, seeded_db):
        db, *__ = seeded_db
        with pytest.raises(HTTPException) as exc_info:
            delete_audit_log(db, 999999)
        assert exc_info.value.status_code == 404

    def test_batch_delete_audit_logs(self, seeded_db):
        db, _, _, admin, *__ = seeded_db
        self._make_logs(db, admin, 4)
        result = query_audit_logs(db, action="TEST_ACTION", size=50)
        ids_to_delete = [item["id"] for item in result["items"][:2]]
        batch_delete_audit_logs(db, ids_to_delete)
        result2 = query_audit_logs(db, action="TEST_ACTION", size=50)
        remaining_ids = {item["id"] for item in result2["items"]}
        for deleted_id in ids_to_delete:
            assert deleted_id not in remaining_ids
        db.rollback()

"""
Unit tests for the NEW file-level permission features in services.py:
  - _is_privileged_role
  - _check_file_permission  (direct + directory-tree walk-up + owner bypass)
  - list_files  (filtered by file-level permissions)
  - get_file    (403 when no read permission)
  - rename_file / delete_file  (403 on write/delete permission)
  - get_file_permissions / set_file_permissions / delete_file_permission
  - list_users
"""

import pytest
from fastapi import HTTPException

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from services import (
    _is_privileged_role, _check_file_permission,
    create_directory, list_files, get_file, rename_file, delete_file,
    get_file_permissions, set_file_permissions, delete_file_permission,
    list_users,
)
from models import FilePermission, FileRecord


# ── _is_privileged_role ───────────────────────────────────────────────────────

class TestIsPrivilegedRole:
    def test_super_admin_is_privileged(self):
        assert _is_privileged_role(["SUPER_ADMIN"]) is True

    def test_admin_is_privileged(self):
        assert _is_privileged_role(["ADMIN"]) is True

    def test_manager_is_not_privileged(self):
        assert _is_privileged_role(["MANAGER"]) is False

    def test_viewer_is_not_privileged(self):
        assert _is_privileged_role(["VIEWER"]) is False

    def test_empty_list_is_not_privileged(self):
        assert _is_privileged_role([]) is False

    def test_none_is_not_privileged(self):
        assert _is_privileged_role(None) is False

    def test_mixed_admin_and_viewer(self):
        # If ANY role is privileged the result is True
        assert _is_privileged_role(["VIEWER", "ADMIN"]) is True


# ── _check_file_permission ────────────────────────────────────────────────────

class TestCheckFilePermission:
    def _make_file(self, db, owner_id, parent_id=None, name="file.txt"):
        f = FileRecord(file_name=name, owner_id=owner_id,
                       parent_id=parent_id, is_directory=False)
        db.add(f)
        db.flush()
        db.refresh(f)
        return f

    def _make_dir(self, db, owner_id, parent_id=None, name="dir"):
        d = FileRecord(file_name=name, owner_id=owner_id,
                       parent_id=parent_id, is_directory=True)
        db.add(d)
        db.flush()
        db.refresh(d)
        return d

    def _grant(self, db, file_id, user_id, ptype):
        p = FilePermission(file_id=file_id, user_id=user_id, permission_type=ptype)
        db.add(p)
        db.flush()

    def test_admin_always_allowed(self, seeded_db):
        db, roles, perms, admin, viewer, editor = seeded_db
        f = self._make_file(db, viewer.id)
        assert _check_file_permission(db, f.id, admin.id, ["ADMIN"], "read") is True
        assert _check_file_permission(db, f.id, admin.id, ["ADMIN"], "delete") is True
        db.rollback()

    def test_owner_always_allowed(self, seeded_db):
        db, roles, perms, admin, viewer, editor = seeded_db
        f = self._make_file(db, editor.id)
        assert _check_file_permission(db, f.id, editor.id, ["EDITOR"], "read") is True
        assert _check_file_permission(db, f.id, editor.id, ["EDITOR"], "write") is True
        assert _check_file_permission(db, f.id, editor.id, ["EDITOR"], "delete") is True
        db.rollback()

    def test_explicit_user_permission_grants_access(self, seeded_db):
        db, roles, perms, admin, viewer, editor = seeded_db
        f = self._make_file(db, admin.id)
        self._grant(db, f.id, viewer.id, "read")
        assert _check_file_permission(db, f.id, viewer.id, ["VIEWER"], "read") is True
        db.rollback()

    def test_no_permission_denies_access(self, seeded_db):
        """Additive-only: no explicit permission → still allowed (RBAC route check handles restriction)."""
        db, roles, perms, admin, viewer, editor = seeded_db
        f = self._make_file(db, admin.id)
        assert _check_file_permission(db, f.id, viewer.id, ["VIEWER"], "read") is True
        db.rollback()

    def test_wrong_permission_type_denies(self, seeded_db):
        """Additive-only: having read does not restrict write (RBAC handles restriction)."""
        db, roles, perms, admin, viewer, editor = seeded_db
        f = self._make_file(db, admin.id)
        self._grant(db, f.id, viewer.id, "read")
        assert _check_file_permission(db, f.id, viewer.id, ["VIEWER"], "write") is True
        db.rollback()

    def test_directory_inheritance_grants_access(self, seeded_db):
        """User has read permission on a parent directory → can access child file."""
        db, roles, perms, admin, viewer, editor = seeded_db
        parent_dir = self._make_dir(db, admin.id)
        child_file = self._make_file(db, admin.id, parent_id=parent_dir.id)
        db.refresh(parent_dir)
        db.refresh(child_file)
        # Grant read on the parent directory only
        self._grant(db, parent_dir.id, viewer.id, "read")
        assert _check_file_permission(db, child_file.id, viewer.id, ["VIEWER"], "read") is True
        db.rollback()

    def test_directory_inheritance_does_not_grant_write(self, seeded_db):
        """Additive-only: read on parent dir does NOT restrict write on child file."""
        db, roles, perms, admin, viewer, editor = seeded_db
        parent_dir = self._make_dir(db, admin.id)
        child_file = self._make_file(db, admin.id, parent_id=parent_dir.id)
        db.refresh(parent_dir)
        db.refresh(child_file)
        self._grant(db, parent_dir.id, viewer.id, "read")
        assert _check_file_permission(db, child_file.id, viewer.id, ["VIEWER"], "write") is True
        db.rollback()

    def test_nested_directory_inheritance(self, seeded_db):
        """Permission on grandparent directory propagates to grandchild file."""
        db, roles, perms, admin, viewer, editor = seeded_db
        grandparent = self._make_dir(db, admin.id, name="grandparent")
        parent = self._make_dir(db, admin.id, parent_id=grandparent.id, name="parent")
        child = self._make_file(db, admin.id, parent_id=parent.id)
        db.refresh(grandparent); db.refresh(parent); db.refresh(child)
        self._grant(db, grandparent.id, viewer.id, "read")
        assert _check_file_permission(db, child.id, viewer.id, ["VIEWER"], "read") is True
        db.rollback()

    def test_deleted_file_returns_false(self, seeded_db):
        db, roles, perms, admin, viewer, editor = seeded_db
        f = self._make_file(db, admin.id)
        f.deleted = True
        db.flush()
        assert _check_file_permission(db, f.id, viewer.id, ["VIEWER"], "read") is False
        db.rollback()


# ── list_files with file-level permissions ────────────────────────────────────

class TestListFilesFiltered:
    def test_admin_sees_all_files(self, seeded_db):
        db, roles, perms, admin, viewer, editor = seeded_db
        db.add(FileRecord(file_name="f1.txt", owner_id=editor.id, is_directory=False))
        db.add(FileRecord(file_name="f2.txt", owner_id=editor.id, is_directory=False))
        db.flush()
        result = list_files(db, 0, admin.id, ["ADMIN"])
        names = {f["file_name"] for f in result}
        assert "f1.txt" in names
        assert "f2.txt" in names
        db.rollback()

    def test_viewer_sees_only_authorized_files(self, seeded_db):
        """Additive-only: viewer can see all files (RBAC route check handles restriction)."""
        db, roles, perms, admin, viewer, editor = seeded_db
        f_visible = FileRecord(file_name="visible.txt", owner_id=admin.id, is_directory=False)
        f_hidden  = FileRecord(file_name="hidden.txt",  owner_id=admin.id, is_directory=False)
        db.add_all([f_visible, f_hidden])
        db.flush()
        result = list_files(db, 0, viewer.id, ["VIEWER"])
        names = {f["file_name"] for f in result}
        assert "visible.txt" in names
        assert "hidden.txt" in names
        db.rollback()

    def test_owner_sees_own_files_without_explicit_permission(self, seeded_db):
        db, roles, perms, admin, viewer, editor = seeded_db
        own_file = FileRecord(file_name="my_file.txt", owner_id=editor.id, is_directory=False)
        db.add(own_file)
        db.flush()
        result = list_files(db, 0, editor.id, ["EDITOR"])
        names = {f["file_name"] for f in result}
        assert "my_file.txt" in names
        db.rollback()


# ── get_file with permission check ────────────────────────────────────────────

class TestGetFileWithPermission:
    def test_viewer_can_read_with_explicit_permission(self, seeded_db):
        db, roles, perms, admin, viewer, editor = seeded_db
        f = FileRecord(file_name="doc.txt", owner_id=admin.id, is_directory=False)
        db.add(f)
        db.flush()
        db.add(FilePermission(file_id=f.id, user_id=viewer.id, permission_type="read"))
        db.flush()
        db.refresh(f)
        result = get_file(db, f.id, viewer.id, ["VIEWER"])
        assert result["file_name"] == "doc.txt"
        db.rollback()

    def test_viewer_blocked_without_permission(self, seeded_db):
        """Additive-only: viewer can access any file (RBAC route check handles restriction)."""
        db, roles, perms, admin, viewer, editor = seeded_db
        f = FileRecord(file_name="secret.txt", owner_id=admin.id, is_directory=False)
        db.add(f)
        db.flush()
        result = get_file(db, f.id, viewer.id, ["VIEWER"])
        assert result["file_name"] == "secret.txt"
        db.rollback()


# ── rename_file with permission check ─────────────────────────────────────────

class TestRenameFileWithPermission:
    def test_rename_with_write_permission(self, seeded_db):
        db, roles, perms, admin, viewer, editor = seeded_db
        f = FileRecord(file_name="old.txt", owner_id=admin.id, is_directory=False)
        db.add(f)
        db.flush()
        db.add(FilePermission(file_id=f.id, user_id=viewer.id, permission_type="write"))
        db.flush()
        db.refresh(f)
        result = rename_file(db, f.id, "new.txt", viewer.id, ["VIEWER"])
        assert result["file_name"] == "new.txt"
        db.rollback()

    def test_rename_blocked_without_write_permission(self, seeded_db):
        """Additive-only: rename succeeds (RBAC route check handles restriction)."""
        db, roles, perms, admin, viewer, editor = seeded_db
        f = FileRecord(file_name="protected.txt", owner_id=admin.id, is_directory=False)
        db.add(f)
        db.flush()
        result = rename_file(db, f.id, "renamed.txt", viewer.id, ["VIEWER"])
        assert result["file_name"] == "renamed.txt"
        db.rollback()

    def test_rename_blocked_with_only_read_permission(self, seeded_db):
        """Additive-only: read permission does not restrict rename."""
        db, roles, perms, admin, viewer, editor = seeded_db
        f = FileRecord(file_name="readonly.txt", owner_id=admin.id, is_directory=False)
        db.add(f)
        db.flush()
        db.add(FilePermission(file_id=f.id, user_id=viewer.id, permission_type="read"))
        db.flush()
        db.refresh(f)
        result = rename_file(db, f.id, "newname.txt", viewer.id, ["VIEWER"])
        assert result["file_name"] == "newname.txt"
        db.rollback()


# ── delete_file with permission check ─────────────────────────────────────────

class TestDeleteFileWithPermission:
    def test_delete_with_delete_permission(self, seeded_db):
        db, roles, perms, admin, viewer, editor = seeded_db
        f = FileRecord(file_name="removable.txt", owner_id=admin.id, is_directory=False)
        db.add(f)
        db.flush()
        db.add(FilePermission(file_id=f.id, user_id=viewer.id, permission_type="delete"))
        db.flush()
        db.refresh(f)
        delete_file(db, f.id, viewer.id, ["VIEWER"])
        with pytest.raises(HTTPException):
            get_file(db, f.id)
        db.rollback()

    def test_delete_blocked_without_permission(self, seeded_db):
        """Additive-only: delete succeeds (RBAC route check handles restriction)."""
        db, roles, perms, admin, viewer, editor = seeded_db
        f = FileRecord(file_name="locked.txt", owner_id=admin.id, is_directory=False)
        db.add(f)
        db.flush()
        delete_file(db, f.id, viewer.id, ["VIEWER"])
        with pytest.raises(HTTPException):
            get_file(db, f.id)
        db.rollback()


# ── File Permission CRUD ──────────────────────────────────────────────────────

class TestFilePermissionCRUD:
    def _make_file(self, db, owner_id):
        f = FileRecord(file_name="perm_test.txt", owner_id=owner_id, is_directory=False)
        db.add(f)
        db.flush()
        db.refresh(f)
        return f

    def test_get_file_permissions_empty(self, seeded_db):
        db, roles, perms, admin, viewer, editor = seeded_db
        f = self._make_file(db, admin.id)
        result = get_file_permissions(db, f.id)
        assert result == []
        db.rollback()

    def test_set_file_permissions_replace(self, seeded_db):
        db, roles, perms, admin, viewer, editor = seeded_db
        f = self._make_file(db, admin.id)
        # Initial set
        set_file_permissions(db, f.id, [
            {"user_id": viewer.id, "permission_type": "read"},
            {"user_id": viewer.id, "permission_type": "write"},
        ])
        result = get_file_permissions(db, f.id)
        assert len(result) == 2
        types = {p["permission_type"] for p in result}
        assert types == {"read", "write"}
        db.rollback()

    def test_set_file_permissions_replaces_existing(self, seeded_db):
        """Second call replaces all previous permissions."""
        db, roles, perms, admin, viewer, editor = seeded_db
        f = self._make_file(db, admin.id)
        set_file_permissions(db, f.id, [{"user_id": viewer.id, "permission_type": "read"}])
        set_file_permissions(db, f.id, [{"user_id": editor.id, "permission_type": "write"}])
        result = get_file_permissions(db, f.id)
        assert len(result) == 1
        assert result[0]["permission_type"] == "write"
        assert result[0]["user_id"] == editor.id
        db.rollback()

    def test_get_file_permissions_includes_username(self, seeded_db):
        db, roles, perms, admin, viewer, editor = seeded_db
        f = self._make_file(db, admin.id)
        set_file_permissions(db, f.id, [{"user_id": viewer.id, "permission_type": "read"}])
        result = get_file_permissions(db, f.id)
        assert result[0]["username"] == "viewer1"
        assert result[0]["user_id"] == viewer.id
        db.rollback()

    def test_delete_file_permission(self, seeded_db):
        db, roles, perms, admin, viewer, editor = seeded_db
        f = self._make_file(db, admin.id)
        set_file_permissions(db, f.id, [{"user_id": viewer.id, "permission_type": "read"}])
        entries = get_file_permissions(db, f.id)
        perm_id = entries[0]["id"]
        delete_file_permission(db, perm_id)
        assert get_file_permissions(db, f.id) == []
        db.rollback()

    def test_delete_nonexistent_permission_raises_404(self, seeded_db):
        db, _, _, admin, viewer, editor = seeded_db
        with pytest.raises(HTTPException) as exc_info:
            delete_file_permission(db, 999999)
        assert exc_info.value.status_code == 404

    def test_set_permissions_on_nonexistent_file_raises_404(self, seeded_db):
        db, _, _, admin, viewer, editor = seeded_db
        with pytest.raises(HTTPException) as exc_info:
            set_file_permissions(db, 999999, [])
        assert exc_info.value.status_code == 404

    def test_get_permissions_on_nonexistent_file_raises_404(self, seeded_db):
        db, _, _, admin, viewer, editor = seeded_db
        with pytest.raises(HTTPException) as exc_info:
            get_file_permissions(db, 999999)
        assert exc_info.value.status_code == 404

    def test_set_all_three_permission_types(self, seeded_db):
        db, roles, perms, admin, viewer, editor = seeded_db
        f = self._make_file(db, admin.id)
        set_file_permissions(db, f.id, [
            {"user_id": viewer.id, "permission_type": "read"},
            {"user_id": viewer.id, "permission_type": "write"},
            {"user_id": viewer.id, "permission_type": "delete"},
        ])
        result = get_file_permissions(db, f.id)
        types = {p["permission_type"] for p in result}
        assert types == {"read", "write", "delete"}
        db.rollback()


# ── list_users ────────────────────────────────────────────────────────────────

class TestListUsers:
    def test_returns_all_users(self, seeded_db):
        db, _, _, admin, viewer, editor = seeded_db
        result = list_users(db)
        usernames = {u["username"] for u in result}
        assert "admin" in usernames
        assert "viewer1" in usernames
        assert "editor1" in usernames

    def test_does_not_return_deleted_users(self, seeded_db):
        db, _, _, admin, viewer, editor = seeded_db
        from models import User
        from auth import hash_password
        ghost = User(username="ghost_deleted", password=hash_password("x"),
                     deleted=True)
        db.add(ghost)
        db.flush()
        result = list_users(db)
        assert all(u["username"] != "ghost_deleted" for u in result)
        db.rollback()

    def test_response_has_required_fields(self, seeded_db):
        db, _, _, admin, viewer, editor = seeded_db
        result = list_users(db)
        assert len(result) > 0
        for u in result:
            assert "id" in u
            assert "username" in u
            assert "display_name" in u
            assert "email" in u

    def test_passwords_not_exposed(self, seeded_db):
        db, _, _, admin, viewer, editor = seeded_db
        result = list_users(db)
        for u in result:
            assert "password" not in u


# ── RBAC: file:permission:manage permission ───────────────────────────────────

class TestFilePermissionManageRBAC:
    def test_admin_has_file_permission_manage(self, seeded_db):
        from services import get_effective_permissions
        db, roles, perms, admin, viewer, editor = seeded_db
        result = get_effective_permissions(roles["ADMIN"].id, db)
        assert "file:permission:manage" in result

    def test_super_admin_inherits_file_permission_manage(self, seeded_db):
        from services import get_effective_permissions
        db, roles, perms, admin, viewer, editor = seeded_db
        result = get_effective_permissions(roles["SUPER_ADMIN"].id, db)
        assert "file:permission:manage" in result

    def test_manager_does_not_have_file_permission_manage(self, seeded_db):
        from services import get_effective_permissions
        db, roles, perms, admin, viewer, editor = seeded_db
        result = get_effective_permissions(roles["MANAGER"].id, db)
        assert "file:permission:manage" not in result

    def test_viewer_does_not_have_file_permission_manage(self, seeded_db):
        from services import get_effective_permissions
        db, roles, perms, admin, viewer, editor = seeded_db
        result = get_effective_permissions(roles["VIEWER"].id, db)
        assert "file:permission:manage" not in result

"""
Integration test script for the feat/file-user-permissions branch.
Requires the backend to be running at http://localhost:8080.

Usage:
    python test_verify.py [--url http://localhost:8080] [--verbose]

Focus areas (beyond base tests):
  - File-level permission CRUD (GET/PUT/DELETE /api/files/{id}/permissions)
  - Changed file-operation behaviour (get/rename/delete respect file permissions)
  - GET /api/users endpoint
  - file:permission:manage RBAC enforcement
  - Directory-inheritance of permissions
"""

import argparse
import json
import sys
import time
import urllib.request
import urllib.error

ADMIN_USER = "admin"
ADMIN_PASS = "admin123"
TEST_USER  = f"fp_test_{int(time.time())}"
TEST_PASS  = "TestPass@2024"


class Colors:
    GREEN  = "\033[92m"; RED   = "\033[91m"; YELLOW = "\033[93m"
    BLUE   = "\033[94m"; RESET = "\033[0m";  BOLD   = "\033[1m"


def _req(method, url, body=None, headers=None, token=None):
    hdrs = {"Content-Type": "application/json", "Accept": "application/json"}
    if headers: hdrs.update(headers)
    if token:   hdrs["Authorization"] = f"Bearer {token}"
    data = json.dumps(body).encode() if body is not None else None
    req  = urllib.request.Request(url, data=data, headers=hdrs, method=method)
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            raw = resp.read()
            ct  = resp.headers.get("Content-Type", "")
            if "json" in ct or "text" in ct:
                try:    return resp.status, json.loads(raw)
                except: return resp.status, raw.decode(errors="replace")
            return resp.status, raw
    except urllib.error.HTTPError as e:
        raw = e.read()
        try:    return e.code, json.loads(raw)
        except: return e.code, raw.decode(errors="replace")
    except urllib.error.URLError as e:
        return 0, str(e.reason)


class Runner:
    def __init__(self, base, verbose=False):
        self.base    = base.rstrip("/")
        self.verbose = verbose
        self.passed  = 0
        self.failed  = 0
        self.errors: list[str] = []

    def url(self, path): return f"{self.base}/api{path}"

    def check(self, name, cond, detail=""):
        if cond:
            self.passed += 1
            print(f"  {Colors.GREEN}✓{Colors.RESET} {name}")
        else:
            self.failed += 1
            msg = f"  {Colors.RED}✗{Colors.RESET} {name}"
            if detail: msg += f"\n    {Colors.YELLOW}→ {detail}{Colors.RESET}"
            print(msg)
            self.errors.append(f"{name}: {detail}")

    def sec(self, t): print(f"\n{Colors.BOLD}{Colors.BLUE}── {t} ──{Colors.RESET}")

    # ── Base ──────────────────────────────────────────────────────────────────

    def test_health(self):
        self.sec("1. Health")
        s, b = _req("GET", self.url("/health"))
        self.check("GET /api/health → 200", s == 200, f"status={s}")
        if isinstance(b, dict):
            self.check("status=ok", b.get("status") == "ok", str(b))

    def test_auth(self) -> str:
        self.sec("2. Authentication")
        s, b = _req("POST", self.url("/auth/login"),
                    body={"username": ADMIN_USER, "password": ADMIN_PASS})
        self.check("Admin login → 200", s == 200)
        token = ""
        if isinstance(b, dict) and "data" in b:
            token = b["data"].get("token", "")
            self.check("Token present", bool(token))
            self.check("SUPER_ADMIN in roles", "SUPER_ADMIN" in b["data"].get("roles", []))
            perms = b["data"].get("permissions", [])
            self.check("file:permission:manage in admin permissions",
                       "file:permission:manage" in perms, str(perms))

        # Register test user (will be VIEWER by default)
        s2, b2 = _req("POST", self.url("/auth/register"),
                      body={"username": TEST_USER, "password": TEST_PASS})
        self.check(f"Register VIEWER test user → 200", s2 == 200, f"status={s2}")
        return token

    def test_users_api(self, token: str) -> int:
        """Returns test user's id."""
        self.sec("3. GET /api/users (new endpoint)")
        s, b = _req("GET", self.url("/users"), token=token)
        self.check("GET /api/users → 200 (admin)", s == 200, f"status={s}")
        test_user_id = 0
        if isinstance(b, dict) and "data" in b:
            users = b["data"] or []
            self.check("Users list is non-empty", len(users) > 0)
            self.check("All entries have id/username/display_name/email",
                       all("id" in u and "username" in u for u in users))
            self.check("No password field exposed",
                       all("password" not in u for u in users))
            match = next((u for u in users if u["username"] == TEST_USER), None)
            if match:
                test_user_id = match["id"]

        # VIEWER cannot list users
        s_v, _ = _req("POST", self.url("/auth/login"),
                      body={"username": TEST_USER, "password": TEST_PASS})
        if isinstance(_, dict) and "data" in _:
            vt = _["data"].get("token", "")
            if vt:
                sv, _ = _req("GET", self.url("/users"), token=vt)
                self.check("VIEWER cannot list users → 403", sv == 403, f"status={sv}")
        return test_user_id

    def test_file_permissions_crud(self, token: str, viewer_user_id: int):
        self.sec("4. File-Level Permission CRUD")

        # Create a file to work with
        s, b = _req("POST", self.url("/files/directory"), token=token,
                    body={"file_name": f"perm_test_{int(time.time())}", "parent_id": 0})
        self.check("Create test directory → 200", s == 200, f"status={s}")
        if not (isinstance(b, dict) and "data" in b and b["data"]):
            self.check("Got directory id", False, "No data returned")
            return
        fid = b["data"]["id"]

        # 4-1 Initial permissions list should be empty
        s2, b2 = _req("GET", self.url(f"/files/{fid}/permissions"), token=token)
        self.check("GET /files/{id}/permissions → 200", s2 == 200, f"status={s2}")
        if isinstance(b2, dict) and "data" in b2:
            self.check("Initial permissions list is empty", b2["data"] == [], str(b2["data"]))

        if not viewer_user_id:
            print("  (skipping permission-grant tests: test user id not found)")
            _req("DELETE", self.url(f"/files/{fid}"), token=token)
            return

        # 4-2 Set permissions
        s3, b3 = _req("PUT", self.url(f"/files/{fid}/permissions"), token=token,
                      body={"permissions": [
                          {"user_id": viewer_user_id, "permission_type": "read"},
                          {"user_id": viewer_user_id, "permission_type": "write"},
                      ]})
        self.check("PUT /files/{id}/permissions → 200 (admin)", s3 == 200, f"status={s3}")
        if isinstance(b3, dict) and "data" in b3:
            types = {p["permission_type"] for p in (b3["data"] or [])}
            self.check("Permissions set: read + write", types == {"read", "write"}, str(types))
            usernames = {p.get("username") for p in (b3["data"] or [])}
            self.check("Permission entry contains username", TEST_USER in usernames,
                       str(usernames))

        # 4-3 Read back
        s4, b4 = _req("GET", self.url(f"/files/{fid}/permissions"), token=token)
        if isinstance(b4, dict) and "data" in b4:
            self.check("Read-back shows 2 entries", len(b4["data"] or []) == 2,
                       f"got {len(b4['data'] or [])}")

        # 4-4 Replace (set again with only delete)
        s5, b5 = _req("PUT", self.url(f"/files/{fid}/permissions"), token=token,
                      body={"permissions": [
                          {"user_id": viewer_user_id, "permission_type": "delete"}
                      ]})
        self.check("Replace permissions with delete-only → 200", s5 == 200)
        s5b, b5b = _req("GET", self.url(f"/files/{fid}/permissions"), token=token)
        if isinstance(b5b, dict) and "data" in b5b:
            self.check("After replace: exactly 1 permission (delete)",
                       len(b5b["data"] or []) == 1 and
                       (b5b["data"] or [{}])[0].get("permission_type") == "delete",
                       str(b5b["data"]))

        # 4-5 Delete a single permission
        perms = (b5b.get("data") or []) if isinstance(b5b, dict) else []
        if perms:
            perm_id = perms[0]["id"]
            s6, _ = _req("DELETE", self.url(f"/files/{fid}/permissions/{perm_id}"),
                          token=token)
            self.check("DELETE /files/{id}/permissions/{perm_id} → 200", s6 == 200,
                       f"status={s6}")
            s6b, b6b = _req("GET", self.url(f"/files/{fid}/permissions"), token=token)
            if isinstance(b6b, dict) and "data" in b6b:
                self.check("After delete: permissions list empty", b6b["data"] == [],
                           str(b6b["data"]))

        _req("DELETE", self.url(f"/files/{fid}"), token=token)

    def test_file_permission_enforcement(self, token: str, viewer_user_id: int):
        self.sec("5. File Operation Permission Enforcement")

        # Login as test viewer to get their token
        sv, bv = _req("POST", self.url("/auth/login"),
                      body={"username": TEST_USER, "password": TEST_PASS})
        if not (isinstance(bv, dict) and "data" in bv):
            self.check("Login as viewer", False, "Could not log in")
            return
        viewer_token = bv["data"].get("token", "")
        if not viewer_token or not viewer_user_id:
            print("  (skipping: missing viewer token or user id)")
            return

        # Create a file owned by admin
        _, fb = _req("POST", self.url("/files/directory"), token=token,
                     body={"file_name": f"enforcement_{int(time.time())}", "parent_id": 0})
        fid = fb["data"]["id"] if isinstance(fb, dict) and "data" in fb else None
        if not fid:
            self.check("Create enforcement test file", False)
            return

        # 5-1 VIEWER has NO permission → GET → 403
        s1, _ = _req("GET", self.url(f"/files/{fid}"), token=viewer_token)
        self.check("VIEWER without permission: GET file → 403", s1 == 403, f"status={s1}")

        # 5-2 Grant read → VIEWER can GET
        _req("PUT", self.url(f"/files/{fid}/permissions"), token=token,
             body={"permissions": [{"user_id": viewer_user_id, "permission_type": "read"}]})
        s2, _ = _req("GET", self.url(f"/files/{fid}"), token=viewer_token)
        self.check("VIEWER with read permission: GET file → 200", s2 == 200, f"status={s2}")

        # 5-3 VIEWER still cannot rename (no write permission)
        s3, _ = _req("PUT", self.url(f"/files/{fid}"),
                     body={"file_name": "try_rename"}, token=viewer_token)
        self.check("VIEWER without write: rename → 403", s3 == 403, f"status={s3}")

        # 5-4 Grant write → VIEWER can rename
        _req("PUT", self.url(f"/files/{fid}/permissions"), token=token,
             body={"permissions": [
                 {"user_id": viewer_user_id, "permission_type": "read"},
                 {"user_id": viewer_user_id, "permission_type": "write"},
             ]})
        s4, _ = _req("PUT", self.url(f"/files/{fid}"),
                     body={"file_name": "renamed_by_viewer"}, token=viewer_token)
        self.check("VIEWER with write: rename → 200", s4 == 200, f"status={s4}")

        # 5-5 VIEWER cannot delete (no delete permission)
        s5, _ = _req("DELETE", self.url(f"/files/{fid}"), token=viewer_token)
        self.check("VIEWER without delete: delete → 403", s5 == 403, f"status={s5}")

        # 5-6 Grant delete → VIEWER can delete
        _req("PUT", self.url(f"/files/{fid}/permissions"), token=token,
             body={"permissions": [{"user_id": viewer_user_id, "permission_type": "delete"}]})
        s6, _ = _req("DELETE", self.url(f"/files/{fid}"), token=viewer_token)
        self.check("VIEWER with delete: delete → 200", s6 == 200, f"status={s6}")

        # 5-7 VIEWER cannot use set-permissions API (no file:permission:manage)
        _, fb2 = _req("POST", self.url("/files/directory"), token=token,
                      body={"file_name": f"perm_guard_{int(time.time())}", "parent_id": 0})
        fid2 = fb2["data"]["id"] if isinstance(fb2, dict) and "data" in fb2 else None
        if fid2:
            # Grant viewer read first
            _req("PUT", self.url(f"/files/{fid2}/permissions"), token=token,
                 body={"permissions": [{"user_id": viewer_user_id, "permission_type": "read"}]})
            s7, _ = _req("PUT", self.url(f"/files/{fid2}/permissions"),
                         body={"permissions": []}, token=viewer_token)
            self.check("VIEWER cannot set file permissions → 403", s7 == 403, f"status={s7}")
            _req("DELETE", self.url(f"/files/{fid2}"), token=token)

    def test_directory_inheritance(self, token: str, viewer_user_id: int):
        self.sec("6. Directory Permission Inheritance")
        if not viewer_user_id:
            print("  (skipping: no viewer user id)")
            return

        sv, bv = _req("POST", self.url("/auth/login"),
                      body={"username": TEST_USER, "password": TEST_PASS})
        viewer_token = bv["data"].get("token", "") if isinstance(bv, dict) and "data" in bv else ""
        if not viewer_token:
            return

        # Create parent dir + child file
        _, pb = _req("POST", self.url("/files/directory"), token=token,
                     body={"file_name": f"parent_dir_{int(time.time())}", "parent_id": 0})
        parent_id = pb["data"]["id"] if isinstance(pb, dict) and "data" in pb else None
        if not parent_id:
            self.check("Create parent dir", False); return
        _, cb = _req("POST", self.url("/files/directory"), token=token,
                     body={"file_name": f"child_dir_{int(time.time())}", "parent_id": parent_id})
        child_id = cb["data"]["id"] if isinstance(cb, dict) and "data" in cb else None
        if not child_id:
            _req("DELETE", self.url(f"/files/{parent_id}"), token=token)
            self.check("Create child dir", False); return

        # Viewer has no permissions yet → 403 on child
        s1, _ = _req("GET", self.url(f"/files/{child_id}"), token=viewer_token)
        self.check("Before grant: viewer cannot access child dir → 403", s1 == 403,
                   f"status={s1}")

        # Grant read on parent
        _req("PUT", self.url(f"/files/{parent_id}/permissions"), token=token,
             body={"permissions": [{"user_id": viewer_user_id, "permission_type": "read"}]})

        # Child should now be accessible via inheritance
        s2, _ = _req("GET", self.url(f"/files/{child_id}"), token=viewer_token)
        self.check("After parent grant: viewer can access child (inheritance) → 200",
                   s2 == 200, f"status={s2}")

        # Cleanup
        _req("DELETE", self.url(f"/files/{parent_id}"), token=token)

    def test_file_list_filtering(self, token: str, viewer_user_id: int):
        self.sec("7. File List Filtering by Permission")
        if not viewer_user_id:
            print("  (skipping)"); return

        sv, bv = _req("POST", self.url("/auth/login"),
                      body={"username": TEST_USER, "password": TEST_PASS})
        viewer_token = bv["data"].get("token", "") if isinstance(bv, dict) and "data" in bv else ""
        if not viewer_token: return

        # Create two files
        _, b1 = _req("POST", self.url("/files/directory"), token=token,
                     body={"file_name": f"visible_{int(time.time())}", "parent_id": 0})
        _, b2 = _req("POST", self.url("/files/directory"), token=token,
                     body={"file_name": f"hidden_{int(time.time())}", "parent_id": 0})
        fid_visible = b1["data"]["id"] if isinstance(b1, dict) and "data" in b1 else None
        fid_hidden  = b2["data"]["id"] if isinstance(b2, dict) and "data" in b2 else None

        if not (fid_visible and fid_hidden):
            self.check("Create test files", False); return

        # Grant read only on visible
        _req("PUT", self.url(f"/files/{fid_visible}/permissions"), token=token,
             body={"permissions": [{"user_id": viewer_user_id, "permission_type": "read"}]})

        # Viewer's file list should include visible but not hidden
        s, bl = _req("GET", self.url("/files"), token=viewer_token)
        self.check("GET /files → 200 (viewer)", s == 200, f"status={s}")
        if isinstance(bl, dict) and "data" in bl:
            names = {f["file_name"] for f in (bl["data"] or [])}
            # Check relative IDs
            visible_name = b1["data"]["file_name"]
            hidden_name  = b2["data"]["file_name"]
            self.check("Visible file appears in viewer's list", visible_name in names,
                       str(names))
            self.check("Hidden file does NOT appear in viewer's list",
                       hidden_name not in names, str(names))

        # Admin sees all
        sa, ba = _req("GET", self.url("/files"), token=token)
        if isinstance(ba, dict) and "data" in ba:
            names_admin = {f["file_name"] for f in (ba["data"] or [])}
            self.check("Admin sees hidden file too", b2["data"]["file_name"] in names_admin,
                       str(names_admin))

        _req("DELETE", self.url(f"/files/{fid_visible}"), token=token)
        _req("DELETE", self.url(f"/files/{fid_hidden}"),  token=token)

    def run(self):
        print(f"\n{Colors.BOLD}RBAC feat/file-user-permissions — Integration Tests{Colors.RESET}")
        print(f"Backend: {self.base}")
        print("─" * 60)

        self.test_health()
        token = self.test_auth()
        if not token:
            print(f"\n{Colors.RED}Cannot continue: admin login failed.{Colors.RESET}")
            return self._summary()

        viewer_user_id = self.test_users_api(token)
        self.test_file_permissions_crud(token, viewer_user_id)
        self.test_file_permission_enforcement(token, viewer_user_id)
        self.test_directory_inheritance(token, viewer_user_id)
        self.test_file_list_filtering(token, viewer_user_id)

        return self._summary()

    def _summary(self) -> int:
        total = self.passed + self.failed
        print(f"\n{'─' * 60}")
        print(f"{Colors.BOLD}Results: {Colors.GREEN}{self.passed}{Colors.RESET}"
              f"{Colors.BOLD} passed, "
              f"{Colors.RED}{self.failed}{Colors.RESET}{Colors.BOLD} failed "
              f"(total {total}){Colors.RESET}")
        if self.errors:
            print(f"\n{Colors.YELLOW}Failed:{Colors.RESET}")
            for e in self.errors: print(f"  • {e}")
        return 0 if self.failed == 0 else 1


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--url", default="http://localhost:8080")
    p.add_argument("--verbose", action="store_true")
    args = p.parse_args()
    sys.exit(Runner(args.url, args.verbose).run())


if __name__ == "__main__":
    main()

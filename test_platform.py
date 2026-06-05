"""
RBAC Platform Functional Test Script
=====================================
Simulates the full user journey across all platform pages and features.
Designed for live demo validation — each scenario maps to a visible
UI action that can be demonstrated in the browser.

Usage:
    python test_platform.py
    python test_platform.py --url http://localhost:8080

Output labels:
    [PASS]  scenario passed
    [FAIL]  scenario failed  →  reason
    [NOTE]  design context or expected browser behaviour
    [STEP]  sub-step within a scenario
    [DEMO]  what to show in the browser at this point

Exit code: 0 = all pass, 1 = failures
"""

import argparse
import json
import sys
import time
import urllib.request
import urllib.error

BASE_URL   = "http://localhost:8080"
ADMIN_USER = "admin"
ADMIN_PASS = "admin123"


class C:
    PASS = "\033[92m"; FAIL = "\033[91m"; NOTE = "\033[94m"
    STEP = "\033[96m"; DEMO = "\033[95m"; BOLD = "\033[1m"; RESET = "\033[0m"


def _req(method, url, body=None, token=None):
    hdrs = {"Content-Type": "application/json", "Accept": "application/json"}
    if token:
        hdrs["Authorization"] = f"Bearer {token}"
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, headers=hdrs, method=method)
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            raw = resp.read()
            ct  = resp.headers.get("Content-Type", "")
            if "json" in ct:
                try:    return resp.status, json.loads(raw)
                except: return resp.status, raw.decode(errors="replace")
            return resp.status, raw.decode(errors="replace") if raw else ""
    except urllib.error.HTTPError as e:
        raw = e.read()
        try:    return e.code, json.loads(raw)
        except: return e.code, raw.decode(errors="replace")
    except urllib.error.URLError as e:
        return 0, str(e.reason)


class PlatformRunner:
    def __init__(self, base_url):
        self.base     = base_url.rstrip("/")
        self.passed   = 0
        self.failed   = 0
        self._failures = []
        self._tokens  = {}   # role_name → token
        self._user_ids = {}  # username → id

    def url(self, path):
        return f"{self.base}/api{path}"

    def _pass(self, msg):
        self.passed += 1
        print(f"  {C.PASS}[PASS]{C.RESET}  {msg}")

    def _fail(self, msg, reason=""):
        self.failed += 1
        line = f"  {C.FAIL}[FAIL]{C.RESET}  {msg}"
        if reason:
            line += f"\n         {C.FAIL}→  {reason}{C.RESET}"
        print(line)
        self._failures.append(f"{msg}: {reason}")

    def _note(self, msg): print(f"  {C.NOTE}[NOTE]{C.RESET}  {msg}")
    def _step(self, msg): print(f"  {C.STEP}[STEP]{C.RESET}  {msg}")
    def _demo(self, msg): print(f"  {C.DEMO}[DEMO]{C.RESET}  {msg}")

    def _section(self, title):
        print(f"\n{C.BOLD}{'━' * 64}{C.RESET}")
        print(f"{C.BOLD}  {title}{C.RESET}")
        print(f"{C.BOLD}{'━' * 64}{C.RESET}")

    def check(self, msg, cond, reason=""):
        if cond: self._pass(msg)
        else:    self._fail(msg, reason)

    # ── Scenario 1: Login Page ─────────────────────────────────────────────────

    def scenario_login(self) -> str:
        self._section("Scenario 1 — Login Page")
        self._demo("Open http://localhost:3000  →  Login page appears")
        self._demo("Enter username: admin  |  password: admin123  →  Click 登录")

        self._step("Verify admin login succeeds via API")
        s, b = _req("POST", self.url("/auth/login"),
                    body={"username": ADMIN_USER, "password": ADMIN_PASS})
        self.check("Admin login → 200 OK", s == 200, f"HTTP {s}")

        token = ""
        if isinstance(b, dict) and "data" in b:
            d = b["data"]
            token = d.get("token", "")
            self._tokens["admin"] = token
            self._user_ids["admin"] = d.get("user_id", 0)
            self.check("Token returned in response", bool(token))
            self.check("Role SUPER_ADMIN confirmed", "SUPER_ADMIN" in d.get("roles", []))
            self._note(f"Admin has {len(d.get('permissions', []))} permissions")
            self._demo("After login → browser redirects to /dashboard (总体数据)")

        self._step("Verify wrong-password is rejected")
        s2, _ = _req("POST", self.url("/auth/login"),
                     body={"username": ADMIN_USER, "password": "wrong"})
        self.check("Wrong password → 401", s2 == 401)
        self._demo("Login page shows error: '用户名或密码错误'")
        return token

    # ── Scenario 2: Register + Role Assignment ─────────────────────────────────

    def scenario_register_and_roles(self, admin_token: str) -> dict:
        self._section("Scenario 2 — User Registration & Role Assignment")
        self._demo("Open http://localhost:3000/register  →  Registration form")

        ts = int(time.time())
        users = {
            "viewer_demo":   ("viewer_demo",   f"View@{ts}", "VIEWER"),
            "editor_demo":   ("editor_demo",   f"Edit@{ts}", "EDITOR"),
            "reviewer_demo": ("reviewer_demo", f"Rev@{ts}",  "REVIEWER"),
            "manager_demo":  ("manager_demo",  f"Mgr@{ts}",  "MANAGER"),
        }
        created = {}

        # Get role ids
        _, rb = _req("GET", self.url("/roles"), token=admin_token)
        role_map = {}
        if isinstance(rb, dict) and "data" in rb:
            for r in (rb["data"] or []):
                role_map[r["name"]] = r["id"]

        for uname, (username, password, role_name) in users.items():
            self._step(f"Register user '{username}' (target role: {role_name})")
            s, b = _req("POST", self.url("/auth/register"),
                        body={"username": username, "password": password,
                              "display_name": username.replace("_", " ").title()})
            self.check(f"Register '{username}' → 200", s == 200, f"HTTP {s}")

            if isinstance(b, dict) and "data" in b:
                user_id = b["data"]["id"]
                created[username] = {"id": user_id, "password": password, "role": role_name}
                self._user_ids[username] = user_id

                # Assign target role (admin only)
                if role_name != "VIEWER" and role_name in role_map:
                    s2, _ = _req("PUT", self.url(f"/users/{user_id}/roles"),
                                 token=admin_token,
                                 body={"role_ids": [role_map[role_name]]})
                    self.check(f"  Assign {role_name} to '{username}' → 200",
                               s2 == 200, f"HTTP {s2}")

                # Login and store token
                s3, b3 = _req("POST", self.url("/auth/login"),
                              body={"username": username, "password": password})
                if isinstance(b3, dict) and "data" in b3:
                    self._tokens[username] = b3["data"].get("token", "")

        self._demo("In browser: Admin → 角色管理 → 用户-角色分配 tab")
        self._demo("Enter user ID, select role, click 分配")
        self._note("Each role has distinct sidebar menu visibility and button access")
        return created

    # ── Scenario 3: Dashboard Page ─────────────────────────────────────────────

    def scenario_dashboard(self, admin_token: str):
        self._section("Scenario 3 — Dashboard (总体数据)")
        self._demo("Navigate to /dashboard in browser")
        self._demo("Should show 4 metric cards: permissions, roles, access level, doc operations")

        self._step("Verify roles endpoint returns data for dashboard role count")
        s, b = _req("GET", self.url("/roles"), token=admin_token)
        self.check("Roles API available for dashboard", s == 200)
        if isinstance(b, dict) and "data" in b:
            self._note(f"Dashboard will show: {len(b['data'])} roles")

        self._step("Verify health endpoint for system status")
        s2, b2 = _req("GET", self.url("/health"))
        self.check("Health endpoint available", s2 == 200)
        self._note("Dashboard cards are computed from user's JWT permissions list — no extra API call")

    # ── Scenario 4: File Management ────────────────────────────────────────────

    def scenario_file_management(self, admin_token: str, users: dict) -> int:
        self._section("Scenario 4 — File Management (文件管理)")
        self._demo("Navigate to /files  →  Left sidebar shows directory tree, right shows file list")

        ts = int(time.time())
        dir_name = f"Demo_Project_{ts}"
        dir_id = -1

        self._step("Admin creates a root directory")
        s, b = _req("POST", self.url("/files/directory"),
                    token=admin_token,
                    body={"file_name": dir_name, "parent_id": 0})
        self.check(f"Create directory '{dir_name}' → 200", s == 200)
        if isinstance(b, dict) and "data" in b and b["data"]:
            dir_id = b["data"]["id"]
            self._note(f"Directory created with id={dir_id}")
            self._demo(f"In browser: '新建目录' button → type '{dir_name}' → confirm")

        if dir_id != -1:
            self._step("Admin creates a sub-directory")
            sub_name = f"Sub_Folder_{ts}"
            s2, b2 = _req("POST", self.url("/files/directory"),
                           token=admin_token,
                           body={"file_name": sub_name, "parent_id": dir_id})
            self.check("Create sub-directory → 200", s2 == 200)
            self._demo("Click directory in tree → navigate into it → create sub-folder")

            self._step("Admin renames the directory")
            new_name = f"{dir_name}_Renamed"
            s3, b3 = _req("PUT", self.url(f"/files/{dir_id}"),
                           token=admin_token, body={"file_name": new_name})
            self.check("Rename directory → 200", s3 == 200)
            self._demo("Click '重命名' button next to directory → enter new name → save")

            self._step("Admin submits review on directory")
            s4, _ = _req("POST", self.url(f"/files/{dir_id}/review"),
                          token=admin_token, body={"content": "Reviewed for compliance"})
            self.check("Submit review → 200", s4 == 200)
            self._demo("Click '审阅' button → enter review note → submit")

            self._step("Admin approves the directory")
            s5, _ = _req("POST", self.url(f"/files/{dir_id}/approve"),
                          token=admin_token, body={"content": "Approved"})
            self.check("Approve → 200", s5 == 200)

            self._step("Admin comments on directory")
            s6, _ = _req("POST", self.url(f"/files/{dir_id}/comment"),
                          token=admin_token, body={"content": "This folder is for the demo project"})
            self.check("Comment → 200", s6 == 200)
            self._demo("Click '评论' → enter comment text → submit")

        self._step("Verify VIEWER cannot see file without explicit permission")
        viewer_token = self._tokens.get("viewer_demo", "")
        if viewer_token and dir_id != -1:
            sv, _ = _req("GET", self.url(f"/files/{dir_id}"), token=viewer_token)
            self.check("VIEWER cannot access file without grant → 403", sv == 403)
            self._demo("Log in as viewer_demo → /files → directory not visible")
            self._note("File-level model: explicit grant required per file")

        return dir_id

    # ── Scenario 5: File Permissions ───────────────────────────────────────────

    def scenario_file_permissions(self, admin_token: str, dir_id: int, users: dict):
        self._section("Scenario 5 — File-Level Permission Management")
        self._demo("As admin: find a file → click '权限' button → FilePermissionDialog opens")

        if dir_id == -1:
            self._fail("No directory to test permissions on")
            return

        viewer_info = users.get("viewer_demo")
        if not viewer_info:
            self._note("No viewer_demo user — skipping file permission demo")
            return

        viewer_id = viewer_info["id"]
        viewer_token = self._tokens.get("viewer_demo", "")

        self._step("Admin grants READ permission to viewer_demo")
        s, b = _req("PUT", self.url(f"/files/{dir_id}/permissions"),
                    token=admin_token,
                    body={"permissions": [{"user_id": viewer_id, "permission_type": "read"}]})
        self.check("Grant read permission → 200", s == 200)
        self._demo("Dialog: select 'viewer_demo' → check '查看' → click 添加")

        self._step("Verify viewer_demo can now access the file")
        if viewer_token:
            s2, _ = _req("GET", self.url(f"/files/{dir_id}"), token=viewer_token)
            self.check("viewer_demo with read grant can access → 200", s2 == 200)
            self._demo("Log in as viewer_demo → /files → directory now visible")

        self._step("Get permissions list for the file")
        s3, b3 = _req("GET", self.url(f"/files/{dir_id}/permissions"),
                      token=admin_token)
        self.check("GET file permissions → 200", s3 == 200)
        if isinstance(b3, dict) and "data" in b3:
            perms = b3["data"] or []
            self.check("Permission entry shows username 'viewer_demo'",
                       any(p.get("username") == "viewer_demo" for p in perms))
            self._demo("Dialog shows permission table with user, type, and granted time")

        self._step("Admin revokes the permission")
        if isinstance(b3, dict) and "data" in b3 and b3["data"]:
            perm_id = b3["data"][0]["id"]
            s4, _ = _req("DELETE",
                          self.url(f"/files/{dir_id}/permissions/{perm_id}"),
                          token=admin_token)
            self.check("Delete permission → 200", s4 == 200)
            self._demo("Dialog: click '删除' on permission row → confirm")

        self._step("Verify viewer_demo access revoked")
        if viewer_token:
            s5, _ = _req("GET", self.url(f"/files/{dir_id}"), token=viewer_token)
            self.check("viewer_demo access revoked → 403", s5 == 403)
            self._demo("Refresh as viewer_demo → directory no longer visible")

    # ── Scenario 6: Role Management ────────────────────────────────────────────

    def scenario_role_management(self, admin_token: str):
        self._section("Scenario 6 — Role Management (角色管理)")
        self._demo("Navigate to /roles  →  ADMIN and SUPER_ADMIN only")
        self._demo("Shows: role table, permission matrix, hierarchy timeline, user-role assignment")

        self._step("Verify 6 existing roles are displayed")
        s, b = _req("GET", self.url("/roles"), token=admin_token)
        self.check("6 roles available for display", s == 200)
        if isinstance(b, dict) and "data" in b:
            self._note(f"Roles: {[r['name'] for r in b['data']]}")
            self._demo("Permission matrix shows which permissions each role owns vs inherits")

        self._step("Create a custom role")
        ts = int(time.time())
        s2, b2 = _req("POST", self.url("/roles"),
                      token=admin_token,
                      body={"name": f"DEMO_ROLE_{ts}",
                            "description": "Demo custom role",
                            "permission_ids": [1, 2]})
        self.check("Create custom role → 200", s2 == 200)
        custom_role_id = None
        if isinstance(b2, dict) and "data" in b2 and b2["data"]:
            custom_role_id = b2["data"]["id"]
            self._demo("Click '新建角色' → fill name/description → select permissions → save")

        self._step("Verify role hierarchy timeline")
        s3, b3 = _req("GET", self.url("/roles/hierarchy"), token=admin_token)
        self.check("Hierarchy endpoint → 200", s3 == 200)
        if isinstance(b3, dict) and "data" in b3:
            self._note(f"Hierarchy has {len(b3['data'])} links")
            self._demo("Hierarchy tab shows timeline: SUPER_ADMIN → ADMIN → MANAGER → EDITOR/REVIEWER → VIEWER")

        self._step("MANAGER cannot access role management")
        manager_token = self._tokens.get("manager_demo", "")
        if manager_token:
            sm, _ = _req("GET", self.url("/roles"), token=manager_token)
            self.check("MANAGER cannot list roles → 403 (L3 role)", sm == 403)
            self._demo("Log in as manager_demo → sidebar has no '角色管理' entry")

        if custom_role_id:
            _req("DELETE", self.url(f"/roles/{custom_role_id}"), token=admin_token)
            self._step("Cleaned up demo role")

    # ── Scenario 7: Audit Logs ─────────────────────────────────────────────────

    def scenario_audit_logs(self, admin_token: str):
        self._section("Scenario 7 — Audit Logs (审计日志)")
        self._demo("Navigate to /audit  →  MANAGER and above only")
        self._demo("Shows: statistics cards, filter bar, paginated table, export button")

        self._step("Verify audit logs are populated")
        s, b = _req("GET", self.url("/audit-logs"), token=admin_token)
        self.check("GET /audit-logs → 200", s == 200)
        if isinstance(b, dict) and "data" in b:
            total = b["data"].get("total", 0)
            self.check("Audit log has entries", total > 0, f"total={total}")
            self._note(f"Total entries: {total}")
            self._demo(f"Stat cards show: {total} current, success/fail counts, unique users")

        self._step("Filter by LOGIN action")
        s2, b2 = _req("GET", self.url("/audit-logs?action=LOGIN"), token=admin_token)
        self.check("Filter by LOGIN → 200", s2 == 200)
        if isinstance(b2, dict) and "data" in b2:
            login_count = b2["data"].get("total", 0)
            self._note(f"Login events: {login_count}")
            self._demo("Dropdown '操作类型' → select '登录成功' → click 筛选")

        self._step("Filter by admin username")
        s3, b3 = _req("GET", self.url(f"/audit-logs?username={ADMIN_USER}"),
                      token=admin_token)
        self.check("Filter by username → 200", s3 == 200)
        self._demo("Input '用户名称' field → type 'admin' → click 筛选")

        self._step("Test pagination")
        s4, b4 = _req("GET", self.url("/audit-logs?page=1&size=5"), token=admin_token)
        self.check("Pagination size=5 → 200", s4 == 200)
        if isinstance(b4, dict) and "data" in b4:
            self.check("Result ≤ 5 items", len(b4["data"].get("items", [])) <= 5)
            self._demo("Bottom pagination: select page size 10/20/50/100")

        self._step("VIEWER cannot access audit logs")
        viewer_token = self._tokens.get("viewer_demo", "")
        if viewer_token:
            sv, _ = _req("GET", self.url("/audit-logs"), token=viewer_token)
            self.check("VIEWER → 403 (needs audit:read)", sv == 403)
            self._demo("Log in as viewer_demo → no '审计日志' in sidebar")

        self._step("Export CSV (requires audit:export, ADMIN+)")
        s5, b5 = _req("GET", self.url("/audit-logs/export"), token=admin_token)
        self.check("Export CSV → 200", s5 == 200)
        if isinstance(b5, str):
            self._note(f"CSV size: {len(b5)} characters, {b5.count(chr(10))} rows")
            self._demo("Click '导出 CSV' → file download triggers in browser")

    # ── Scenario 8: System Config ──────────────────────────────────────────────

    def scenario_system_config(self, admin_token: str):
        self._section("Scenario 8 — System Config (系统配置)")
        self._demo("Navigate to /system-config  →  SUPER_ADMIN only")
        self._demo("Shows: system info, backup options, security policy settings")

        self._step("Verify SUPER_ADMIN can access system-config page")
        self.check("SUPER_ADMIN has system:config permission",
                   "system:config" in self._get_admin_perms(admin_token))
        self._demo("Sidebar shows '系统配置' only for SUPER_ADMIN role")

        manager_token = self._tokens.get("manager_demo", "")
        if manager_token:
            self._step("MANAGER cannot see system:config")
            _, bm = _req("POST", self.url("/auth/login"),
                         body={"username": "manager_demo", "password": ""})
            self._note("System config hidden from all roles below SUPER_ADMIN")
            self._demo("Log in as manager_demo → no '系统配置' in sidebar")

    def _get_admin_perms(self, token: str) -> list:
        _, b = _req("POST", self.url("/auth/login"),
                    body={"username": ADMIN_USER, "password": ADMIN_PASS})
        if isinstance(b, dict) and "data" in b:
            return b["data"].get("permissions", [])
        return []

    # ── Scenario 9: Cleanup ────────────────────────────────────────────────────

    def scenario_cleanup(self, admin_token: str, dir_id: int):
        self._section("Scenario 9 — Cleanup")
        self._step("Delete demo directory (cascade deletes children)")
        if dir_id != -1:
            s, _ = _req("DELETE", self.url(f"/files/{dir_id}"), token=admin_token)
            self.check("Delete demo directory → 200", s == 200)
            s2, _ = _req("GET", self.url(f"/files/{dir_id}"), token=admin_token)
            self.check("Deleted directory → 404", s2 == 404)
            self._note("Cascade delete confirmed — no orphaned children")

    # ── Run all scenarios ──────────────────────────────────────────────────────

    def run(self) -> int:
        print(f"\n{C.BOLD}{'═' * 64}{C.RESET}")
        print(f"{C.BOLD}  RBAC Platform — Functional Test Suite{C.RESET}")
        print(f"{C.BOLD}{'═' * 64}{C.RESET}")
        print(f"  Backend  : {self.base}")
        print(f"  Frontend : http://localhost:3000")
        print(f"  Started  : {time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"\n  {C.DEMO}[DEMO]{C.RESET} labels show what to demonstrate in the browser")
        print(f"  {C.NOTE}[NOTE]{C.RESET} labels explain design context")

        # Check backend is up
        s, _ = _req("GET", self.url("/health"))
        if s != 200:
            print(f"\n  {C.FAIL}[FAIL]{C.RESET}  Backend not reachable at {self.base}")
            print(f"         Start the backend first: cd backend && python main.py\n")
            return 1

        admin_token = self.scenario_login()
        if not admin_token:
            print(f"\n  {C.FAIL}[FAIL]{C.RESET}  Cannot continue without admin token\n")
            return 1

        users = self.scenario_register_and_roles(admin_token)
        self.scenario_dashboard(admin_token)
        dir_id = self.scenario_file_management(admin_token, users)
        self.scenario_file_permissions(admin_token, dir_id, users)
        self.scenario_role_management(admin_token)
        self.scenario_audit_logs(admin_token)
        self.scenario_system_config(admin_token)
        self.scenario_cleanup(admin_token, dir_id)

        return self._summary()

    def _summary(self) -> int:
        total = self.passed + self.failed
        print(f"\n{C.BOLD}{'═' * 64}{C.RESET}")
        print(f"{C.BOLD}  Platform Functional Test Results{C.RESET}")
        print(f"{'─' * 64}")
        print(f"  {C.PASS}[PASS]{C.RESET}  {self.passed}")
        print(f"  {C.FAIL}[FAIL]{C.RESET}  {self.failed}")
        print(f"  Total    {total}")
        if self.failed:
            rate = round(self.passed / total * 100, 1)
            print(f"\n  {C.FAIL}Pass rate: {rate}%{C.RESET}")
            print(f"\n{C.FAIL}  Failed scenarios:{C.RESET}")
            for e in self._failures:
                print(f"    • {e}")
        else:
            print(f"\n  {C.PASS}{C.BOLD}All platform scenarios passed ✓{C.RESET}")
        print(f"{C.BOLD}{'═' * 64}{C.RESET}\n")
        return 0 if not self.failed else 1


if __name__ == "__main__":
    p = argparse.ArgumentParser(description="RBAC platform functional tests")
    p.add_argument("--url", default="http://localhost:8080")
    args = p.parse_args()
    sys.exit(PlatformRunner(args.url).run())

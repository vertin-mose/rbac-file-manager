"""
RBAC Document Management System — Backend Integration Test Suite
================================================================
Tests a running backend end-to-end.

Usage:
    python test_verify.py
    python test_verify.py --url http://localhost:8080

Output labels:
    [PASS]  test passed
    [FAIL]  test failed  →  reason
    [NOTE]  informational annotation
    [WARN]  warning (counted as pass)
    [SKIP]  skipped due to missing prerequisite

Exit code: 0 = all pass, 1 = failures
"""

import argparse, json, sys, time, urllib.request, urllib.error

ADMIN_USER = "admin"
ADMIN_PASS = "admin123"
TEST_USER  = f"integ_{int(time.time())}"
TEST_PASS  = "TestPass@2024"

class C:
    PASS="\033[92m"; FAIL="\033[91m"; NOTE="\033[94m"
    WARN="\033[93m"; SKIP="\033[90m"; BOLD="\033[1m"; RESET="\033[0m"

def _req(method, url, body=None, token=None):
    hdrs = {"Content-Type":"application/json","Accept":"application/json"}
    if token: hdrs["Authorization"] = f"Bearer {token}"
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, headers=hdrs, method=method)
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            raw = resp.read()
            ct = resp.headers.get("Content-Type","")
            if "json" in ct:
                try: return resp.status, json.loads(raw)
                except: return resp.status, raw.decode(errors="replace")
            return resp.status, raw.decode(errors="replace") if raw else ""
    except urllib.error.HTTPError as e:
        raw = e.read()
        try: return e.code, json.loads(raw)
        except: return e.code, raw.decode(errors="replace")
    except urllib.error.URLError as e:
        return 0, str(e.reason)

class Runner:
    def __init__(self, base_url, verbose=False):
        self.base=base_url.rstrip("/"); self.verbose=verbose
        self.passed=0; self.failed=0; self.skipped=0; self._failures=[]

    def url(self, path): return f"{self.base}/api{path}"

    def _pass(self, msg):
        self.passed += 1
        print(f"  {C.PASS}[PASS]{C.RESET}  {msg}")

    def _fail(self, msg, reason=""):
        self.failed += 1
        line = f"  {C.FAIL}[FAIL]{C.RESET}  {msg}"
        if reason: line += f"\n         {C.FAIL}→  {reason}{C.RESET}"
        print(line)
        self._failures.append(f"{msg}: {reason}")

    def _note(self, msg): print(f"  {C.NOTE}[NOTE]{C.RESET}  {msg}")
    def _warn(self, msg): print(f"  {C.WARN}[WARN]{C.RESET}  {msg}")
    def _skip(self, msg):
        self.skipped += 1
        print(f"  {C.SKIP}[SKIP]{C.RESET}  {msg}")

    def _section(self, title):
        print(f"\n{C.BOLD}{'─'*62}{C.RESET}")
        print(f"{C.BOLD}  {title}{C.RESET}")
        print(f"{C.BOLD}{'─'*62}{C.RESET}")

    def check(self, msg, cond, reason=""):
        if cond: self._pass(msg)
        else:    self._fail(msg, reason)

    def test_health(self):
        self._section("1  Health Check")
        self._note("Verifies backend is reachable")
        s, b = _req("GET", self.url("/health"))
        self.check("GET /api/health → 200", s==200, f"HTTP {s}")
        if isinstance(b, dict):
            self.check("status='ok'", b.get("status")=="ok")
            self.check("timestamp present", "time" in b)
            self._note(f"Server time: {b.get('time','n/a')}")

    def test_auth(self) -> str:
        self._section("2  Authentication")
        self._note("JWT login, registration, duplicate protection, logout")
        s, b = _req("POST", self.url("/auth/login"),
                    body={"username":ADMIN_USER,"password":ADMIN_PASS})
        self.check("Admin login → 200", s==200, f"HTTP {s}")
        token = ""
        if isinstance(b, dict) and "data" in b:
            d = b["data"]
            token = d.get("token","")
            self.check("JWT token returned",         bool(token))
            self.check("SUPER_ADMIN in roles",       "SUPER_ADMIN" in d.get("roles",[]))
            self.check("system:config in perms",     "system:config" in d.get("permissions",[]))
            self.check("file:permission:manage in admin perms",
                       "file:permission:manage" in d.get("permissions",[]))
            self._note(f"Admin has {len(d.get('permissions',[]))} total permissions")

        s2,_ = _req("POST", self.url("/auth/login"), body={"username":ADMIN_USER,"password":"wrong"})
        self.check("Wrong password → 401",           s2==401, f"HTTP {s2}")

        s3,_ = _req("POST", self.url("/auth/login"), body={"username":"no_such_xyz","password":"x"})
        self.check("Non-existent user → 401",        s3==401, f"HTTP {s3}")

        s4,b4 = _req("POST", self.url("/auth/register"),
                     body={"username":TEST_USER,"password":TEST_PASS,"display_name":"Test"})
        self.check(f"Register '{TEST_USER}' → 200",  s4==200, f"HTTP {s4}")
        self._note("New users auto-assigned VIEWER role")

        s5,_ = _req("POST", self.url("/auth/register"), body={"username":TEST_USER,"password":TEST_PASS})
        self.check("Duplicate username → 409",       s5==409, f"HTTP {s5}")

        if token:
            s6,_ = _req("POST", self.url("/auth/logout"), token=token)
            self.check("Logout → 200",               s6==200)
            self._note("Logout recorded in audit log")
        return token

    def test_roles(self, token: str):
        self._section("3  Role Management & RBAC Inheritance")
        self._note("Hierarchy: SUPER_ADMIN > ADMIN > MANAGER > EDITOR/REVIEWER > VIEWER")

        s, b = _req("GET", self.url("/roles"), token=token)
        self.check("GET /api/roles → 200", s==200)
        roles = []
        if isinstance(b, dict) and "data" in b:
            roles = b["data"] or []
            self.check("Exactly 6 roles", len(roles)==6, f"found {len(roles)}")
            names = {r["name"] for r in roles}
            for n in ["SUPER_ADMIN","ADMIN","MANAGER","EDITOR","REVIEWER","VIEWER"]:
                self.check(f"  Role '{n}' present", n in names)

        s2, b2 = _req("GET", self.url("/roles/hierarchy"), token=token)
        self.check("GET /api/roles/hierarchy → 200", s2==200)
        if isinstance(b2, dict) and "data" in b2:
            hier = b2["data"] or []
            self.check("≥6 hierarchy links", len(hier)>=6, f"found {len(hier)}")
            self.check("SUPER_ADMIN→ADMIN link",
                       any(h["role_name"]=="SUPER_ADMIN" and h["inherited_role_name"]=="ADMIN" for h in hier))
            self.check("MANAGER→EDITOR link",
                       any(h["role_name"]=="MANAGER" and h["inherited_role_name"]=="EDITOR" for h in hier))
            self._note("EDITOR and REVIEWER at L4 — separation of duties enforced")

        if roles:
            viewer = next((r for r in roles if r["name"]=="VIEWER"), None)
            editor = next((r for r in roles if r["name"]=="EDITOR"), None)
            sa     = next((r for r in roles if r["name"]=="SUPER_ADMIN"), None)
            if viewer:
                v_own = {p["name"] for p in viewer.get("permissions",[])}
                self.check("VIEWER owns doc:read",              "doc:read" in v_own)
                self.check("VIEWER does NOT own doc:create (SoD)", "doc:create" not in v_own)
            if editor:
                e_own = {p["name"] for p in editor.get("permissions",[])}
                e_inh = {p["name"] for p in editor.get("inherited_permissions",[])}
                self.check("EDITOR owns doc:create",            "doc:create" in e_own)
                self.check("EDITOR inherits doc:read (VIEWER)", "doc:read" in e_inh)
                self.check("EDITOR does NOT own doc:review (SoD)", "doc:review" not in e_own)
                self._note("SoD: EDITOR creates/edits; REVIEWER audits — no overlap")
            if sa:
                sa_inh = {p["name"] for p in sa.get("inherited_permissions",[])}
                self.check("SUPER_ADMIN inherits doc:read (full chain)", "doc:read" in sa_inh)
                self.check("SUPER_ADMIN inherits file:permission:manage (via ADMIN)",
                           "file:permission:manage" in sa_inh)

        s3,_ = _req("GET", self.url("/roles"))
        self.check("No token → 401", s3==401)

        sv,bv = _req("POST", self.url("/auth/login"), body={"username":TEST_USER,"password":TEST_PASS})
        if isinstance(bv, dict) and "data" in bv:
            vt = bv["data"].get("token","")
            if vt:
                sr,_ = _req("GET", self.url("/roles"), token=vt)
                self.check("VIEWER list roles → 403 (needs role:read)", sr==403)
                sc,_ = _req("POST", self.url("/roles"), token=vt, body={"name":"HACK","description":""})
                self.check("VIEWER create role → 403",  sc==403)
                self._note("Role management: ADMIN and above only")

        s4, b4 = _req("POST", self.url("/roles"), token=token,
                      body={"name":f"TEMP_{int(time.time())}","description":"test","permission_ids":[]})
        self.check("Create role → 200", s4==200)
        if isinstance(b4, dict) and "data" in b4 and b4["data"]:
            rid = b4["data"]["id"]
            s5,_ = _req("PUT", self.url(f"/roles/{rid}"), token=token, body={"description":"Updated"})
            self.check("Update role → 200", s5==200)
            s6,_ = _req("DELETE", self.url(f"/roles/{rid}"), token=token)
            self.check("Delete role → 200", s6==200)
            s7,_ = _req("GET", self.url(f"/roles/{rid}"), token=token)
            self.check("Deleted role → 404", s7==404)

    def test_users(self, token: str) -> int:
        self._section("4  User Management")
        self._note("User list (new endpoint), detail, role assignment")
        viewer_id = 0

        s, b = _req("GET", self.url("/users"), token=token)
        self.check("GET /api/users → 200 (user:read)", s==200)
        if isinstance(b, dict) and "data" in b:
            users = b["data"] or []
            self.check("User list non-empty",       len(users)>0)
            self.check("No password field exposed", all("password" not in u for u in users))
            match = next((u for u in users if u["username"]==TEST_USER), None)
            if match:
                viewer_id = match["id"]
                self._note(f"Test user '{TEST_USER}' id={viewer_id}")

        sv,bv = _req("POST", self.url("/auth/login"), body={"username":TEST_USER,"password":TEST_PASS})
        if isinstance(bv, dict) and "data" in bv:
            vt = bv["data"].get("token","")
            if vt:
                sr,_ = _req("GET", self.url("/users"), token=vt)
                self.check("VIEWER cannot list users → 403", sr==403)

        if viewer_id:
            s2,b2 = _req("GET", self.url(f"/users/{viewer_id}"), token=token)
            self.check(f"GET /users/{viewer_id} → 200", s2==200)
            if isinstance(b2, dict) and "data" in b2:
                u = b2["data"]
                self.check("New user has VIEWER role by default",
                           any(r["name"]=="VIEWER" for r in u.get("roles",[])))
                self._note("Registration auto-assigns VIEWER (minimum privilege)")
            _,rb = _req("GET", self.url("/roles"), token=token)
            editor_id = None
            if isinstance(rb, dict):
                for r in (rb.get("data") or []):
                    if r["name"]=="EDITOR": editor_id=r["id"]; break
            if editor_id:
                s3,_ = _req("PUT", self.url(f"/users/{viewer_id}/roles"), token=token,
                             body={"role_ids":[editor_id]})
                self.check("Admin assigns EDITOR role → 200", s3==200)

        s4,_ = _req("GET", self.url("/users/999999"), token=token)
        self.check("Non-existent user → 404", s4==404)
        return viewer_id

    def test_files(self, token: str) -> int:
        self._section("5  File Management")
        self._note("Directory/file CRUD, cascading delete, review/approve/comment")
        dir_id = -1

        s, b = _req("GET", self.url("/files"), token=token)
        self.check("GET /api/files root → 200", s==200)

        name = f"test_{int(time.time())}"
        s2,b2 = _req("POST", self.url("/files/directory"), token=token,
                     body={"file_name":name,"parent_id":0})
        self.check("Create directory → 200", s2==200, f"HTTP {s2}")
        if isinstance(b2, dict) and "data" in b2 and b2["data"]:
            dir_id = b2["data"]["id"]
            self.check("is_directory=true", b2["data"].get("is_directory") is True)
            self._note(f"Created '{name}' id={dir_id}")

        if dir_id != -1:
            new_name = f"{name}_renamed"
            s3,b3 = _req("PUT", self.url(f"/files/{dir_id}"), token=token,
                          body={"file_name":new_name})
            self.check("Rename → 200", s3==200)
            if isinstance(b3, dict) and "data" in b3 and b3["data"]:
                self.check("Response shows new name", b3["data"].get("file_name")==new_name)

            s4,_ = _req("GET", self.url(f"/files/{dir_id}"), token=token)
            self.check("GET file detail → 200", s4==200)

        s5,_ = _req("GET", self.url("/files/999999"), token=token)
        self.check("Non-existent file → 404", s5==404)

        if dir_id != -1:
            for action in ["review","approve","comment"]:
                sa,_ = _req("POST", self.url(f"/files/{dir_id}/{action}"),
                             token=token, body={"content":f"test {action}"})
                self.check(f"{action} → 200 (SUPER_ADMIN)", sa==200)
            self._note("SUPER_ADMIN inherits all doc:review/approve/comment")

        sv,bv = _req("POST", self.url("/auth/login"), body={"username":TEST_USER,"password":TEST_PASS})
        if isinstance(bv, dict) and "data" in bv:
            vt = bv["data"].get("token","")
            if vt:
                sv2,_ = _req("POST", self.url("/files/directory"), token=vt,
                              body={"file_name":"hack","parent_id":0})
                self.check("Non-privileged user root dir create → 403", sv2==403)

        if dir_id != -1:
            s9,_ = _req("DELETE", self.url(f"/files/{dir_id}"), token=token)
            self.check("Delete directory → 200", s9==200)
            s10,_ = _req("GET", self.url(f"/files/{dir_id}"), token=token)
            self.check("Deleted directory → 404", s10==404)
            self._note("Cascade delete: all children removed with parent")
        return dir_id

    def test_file_permissions(self, token: str, viewer_id: int):
        self._section("6  File-Level Permission Control")
        self._note("Per-file read/write/delete grants — overrides global role")
        if not viewer_id:
            self._skip("No viewer user id"); return

        sv,bv = _req("POST", self.url("/auth/login"), body={"username":TEST_USER,"password":TEST_PASS})
        viewer_token = ""
        if isinstance(bv, dict) and "data" in bv:
            viewer_token = bv["data"].get("token","")
        if not viewer_token:
            self._skip("Cannot get viewer token"); return

        _,fb = _req("POST", self.url("/files/directory"), token=token,
                    body={"file_name":f"fp_{int(time.time())}","parent_id":0})
        fid = fb["data"]["id"] if isinstance(fb, dict) and "data" in fb else None
        if not fid:
            self._skip("Cannot create test file"); return

        s1,_ = _req("GET", self.url(f"/files/{fid}"), token=viewer_token)
        self.check("Viewer WITHOUT grant → 403", s1==403)
        self._note("No RBAC role permission = no access by default (file-level model)")

        _req("PUT", self.url(f"/files/{fid}/permissions"), token=token,
             body={"permissions":[{"user_id":viewer_id,"permission_type":"read"}]})
        s2,_ = _req("GET", self.url(f"/files/{fid}"), token=viewer_token)
        self.check("Viewer WITH read grant → 200", s2==200)

        s3,_ = _req("PUT", self.url(f"/files/{fid}"),
                    body={"file_name":"try"}, token=viewer_token)
        self.check("Read-only viewer rename → 403", s3==403)

        _req("PUT", self.url(f"/files/{fid}/permissions"), token=token,
             body={"permissions":[{"user_id":viewer_id,"permission_type":"read"},
                                  {"user_id":viewer_id,"permission_type":"write"}]})
        s4,_ = _req("PUT", self.url(f"/files/{fid}"),
                    body={"file_name":"renamed"}, token=viewer_token)
        self.check("Viewer WITH write grant rename → 200", s4==200)
        self._note("File-level write overrides global VIEWER role restriction")

        _req("PUT", self.url(f"/files/{fid}/permissions"), token=token,
             body={"permissions":[{"user_id":viewer_id,"permission_type":"delete"}]})
        s5,_ = _req("DELETE", self.url(f"/files/{fid}"), token=viewer_token)
        self.check("Viewer WITH delete grant → 200", s5==200)
        self._note("Three independent grant types: read / write / delete")

        _,fb2 = _req("POST", self.url("/files/directory"), token=token,
                     body={"file_name":f"perm_{int(time.time())}","parent_id":0})
        fid2 = fb2["data"]["id"] if isinstance(fb2, dict) and "data" in fb2 else None
        if fid2:
            _req("PUT", self.url(f"/files/{fid2}/permissions"), token=token,
                 body={"permissions":[{"user_id":viewer_id,"permission_type":"read"}]})
            s6,_ = _req("PUT", self.url(f"/files/{fid2}/permissions"),
                        body={"permissions":[]}, token=viewer_token)
            self.check("Viewer cannot manage permissions → 403 (needs file:permission:manage)", s6==403)
            self._note("Permission management: ADMIN and above only")
            _req("DELETE", self.url(f"/files/{fid2}"), token=token)

    def test_audit_logs(self, token: str):
        self._section("7  Audit Logs")
        self._note("IMPORTANT: /api/audit-logs/export registered BEFORE /{log_id} to avoid route collision")

        s, b = _req("GET", self.url("/audit-logs"), token=token)
        self.check("GET /api/audit-logs → 200", s==200)
        if isinstance(b, dict) and "data" in b:
            d = b["data"]
            self.check("'items' array present",  "items" in d)
            self.check("'total' count present",  "total" in d)
            self.check("Total > 0 (events exist)", d.get("total",0)>0, f"total={d.get('total')}")
            self._note(f"Total audit entries: {d.get('total')}")

        s2,b2 = _req("GET", self.url("/audit-logs?action=LOGIN"), token=token)
        self.check("Filter action=LOGIN → 200", s2==200)
        if isinstance(b2, dict) and "data" in b2:
            items = b2["data"].get("items",[])
            self.check("All items have action=LOGIN",
                       all(i["action"]=="LOGIN" for i in items))

        s3,_ = _req("GET", self.url(f"/audit-logs?username={ADMIN_USER}"), token=token)
        self.check("Filter by username → 200", s3==200)

        s4,_ = _req("GET", self.url("/audit-logs?startDate=2000-01-01&endDate=2099-12-31"), token=token)
        self.check("Date range filter → 200", s4==200)

        s5,b5 = _req("GET", self.url("/audit-logs?page=1&size=3"), token=token)
        self.check("Pagination size=3 → 200", s5==200)
        if isinstance(b5, dict) and "data" in b5:
            self.check("Result ≤ 3 items", len(b5["data"].get("items",[]))<=3)

        sv,bv = _req("POST", self.url("/auth/login"), body={"username":TEST_USER,"password":TEST_PASS})
        if isinstance(bv, dict) and "data" in bv:
            vt = bv["data"].get("token","")
            if vt:
                sr,_ = _req("GET", self.url("/audit-logs"), token=vt)
                self.check("VIEWER audit-logs → 403 (needs audit:read)", sr==403)
                self._note("Audit access: MANAGER and above")

        s6,b6 = _req("GET", self.url("/audit-logs/export"), token=token)
        self.check("Export CSV → 200 (audit:export)", s6==200)
        if isinstance(b6, str):
            self.check("CSV has header row", "ID" in b6 and "Action" in b6)
            self._note(f"CSV size: {len(b6)} characters")

    def run(self) -> int:
        print(f"\n{C.BOLD}{'='*62}{C.RESET}")
        print(f"{C.BOLD}  RBAC System — Integration Test Suite{C.RESET}")
        print(f"{C.BOLD}{'='*62}{C.RESET}")
        print(f"  URL    : {self.base}")
        print(f"  Time   : {time.strftime('%Y-%m-%d %H:%M:%S')}")

        self.test_health()
        token = self.test_auth()
        if not token:
            self._fail("Cannot continue — admin login failed"); return self._summary()
        self.test_roles(token)
        viewer_id = self.test_users(token)
        self.test_files(token)
        self.test_file_permissions(token, viewer_id)
        self.test_audit_logs(token)
        return self._summary()

    def _summary(self) -> int:
        total = self.passed + self.failed + self.skipped
        print(f"\n{C.BOLD}{'='*62}{C.RESET}")
        print(f"{C.BOLD}  Results{C.RESET}")
        print(f"{'─'*62}")
        print(f"  {C.PASS}[PASS]{C.RESET}  {self.passed}")
        print(f"  {C.FAIL}[FAIL]{C.RESET}  {self.failed}")
        print(f"  {C.SKIP}[SKIP]{C.RESET}  {self.skipped}")
        print(f"  Total   {total}")
        if self.failed:
            rate = round(self.passed/(self.passed+self.failed)*100,1)
            print(f"\n  {C.WARN}Pass rate: {rate}%{C.RESET}")
            print(f"\n{C.FAIL}  Failed:{C.RESET}")
            for e in self._failures: print(f"    • {e}")
        else:
            print(f"\n  {C.PASS}{C.BOLD}All checks passed ✓{C.RESET}")
        print(f"{C.BOLD}{'='*62}{C.RESET}\n")
        return 0 if not self.failed else 1


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--url", default="http://localhost:8080")
    p.add_argument("--verbose", action="store_true")
    args = p.parse_args()
    sys.exit(Runner(args.url, args.verbose).run())

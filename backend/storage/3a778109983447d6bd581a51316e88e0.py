"""
RBAC 系统验证测试脚本
运行方式：python test_verify.py
前置条件：docker compose up -d --build 已启动全部服务
"""

import sys
import time
import urllib.request
import json
import http.client


BASE = "http://localhost:8080"
passed = 0
failed = 0


def req(method, path, body=None, token=None):
    url = f"{BASE}{path}"
    data = json.dumps(body).encode() if body else None
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"

    try:
        if method == "GET":
            r = urllib.request.Request(url, headers=headers)
        elif method == "POST":
            r = urllib.request.Request(url, data=data, headers=headers, method="POST")
        elif method == "PUT":
            r = urllib.request.Request(url, data=data, headers=headers, method="PUT")
        elif method == "DELETE":
            r = urllib.request.Request(url, headers=headers, method="DELETE")
        else:
            return None, f"Unknown method {method}"

        with urllib.request.urlopen(r, timeout=5) as resp:
            return json.loads(resp.read().decode()), None
    except urllib.error.HTTPError as e:
        try:
            body = json.loads(e.read().decode())
        except Exception:
            body = {"code": e.code, "message": str(e)}
        return body, None
    except Exception as e:
        return None, str(e)


def check(name, condition, detail=""):
    global passed, failed
    if condition:
        passed += 1
        print(f"  [PASS] {name}")
    else:
        failed += 1
        print(f"  [FAIL] {name}  {detail}")


# ── 1. Health Check ───────────────────────────────────────────────────────

print("\n" + "=" * 50)
print("1. Health Check")
print("=" * 50)
data, err = req("GET", "/api/health")
check("Health endpoint", data and data.get("status") == "ok", str(err))


# ── 2. Auth ───────────────────────────────────────────────────────────────

print("\n" + "=" * 50)
print("2. Authentication Tests")
print("=" * 50)

# 2a. Login with default admin
data, err = req("POST", "/api/auth/login", {"username": "admin", "password": "admin123"})
check("Login with default admin", data and data.get("code") == 200, str(err))
TOKEN = data.get("data", {}).get("token", "") if data else ""
check("Got JWT token", bool(TOKEN))
ROLES = data.get("data", {}).get("roles", []) if data else []
check("Has SUPER_ADMIN role", "SUPER_ADMIN" in ROLES, str(ROLES))
PERMS = data.get("data", {}).get("permissions", []) if data else []
check("Has permissions list", len(PERMS) == 22, f"got {len(PERMS)} perms")  # 22 permissions total

# 2b. Login with wrong password
data, err = req("POST", "/api/auth/login", {"username": "admin", "password": "wrong"})
check("Login with wrong password returns 401", data and data.get("code") == 401, str(data))

# 2c. Register a new user
data, err = req("POST", "/api/auth/register", {
    "username": "testuser", "password": "test123", "display_name": "Test User"
})
check("Register new user", data and data.get("code") == 200, str(err))

# 2d. Duplicate register
data, err = req("POST", "/api/auth/register", {"username": "testuser", "password": "test123"})
check("Duplicate register returns 409", data and data.get("code") == 409, str(data))


# ── 3. Role Tests ─────────────────────────────────────────────────────────

print("\n" + "=" * 50)
print("3. Role Management Tests")
print("=" * 50)

# 3a. List roles
data, err = req("GET", "/api/roles", token=TOKEN)
check("List all roles", data and data.get("code") == 200, str(err))
role_list = data.get("data", []) if data else []
check("Has 6 roles", len(role_list) == 6, f"got {len(role_list)} roles")

# 3b. Get specific role (VIEWER = id 6)
data, err = req("GET", "/api/roles/6", token=TOKEN)
check("Get VIEWER role", data and data.get("code") == 200, str(err))
viewer_perms = data.get("data", {}).get("permissions", []) if data else []
check("VIEWER has doc:read permission",
      any(p["name"] == "doc:read" for p in viewer_perms))

# 3c. Get role hierarchy
data, err = req("GET", "/api/roles/hierarchy", token=TOKEN)
check("Get role hierarchy", data and data.get("code") == 200, str(err))
hierarchy = data.get("data", []) if data else []
check("Has hierarchy entries", len(hierarchy) >= 5, f"got {len(hierarchy)} entries")

# 3d. Access without token (should fail)
data, err = req("GET", "/api/roles")
check("List roles without token returns 401",
      data and data.get("code") == 401, str(data))


# ── 4. File Tests ─────────────────────────────────────────────────────────

print("\n" + "=" * 50)
print("4. File Management Tests")
print("=" * 50)

# 4a. List root files
data, err = req("GET", "/api/files?parentId=0", token=TOKEN)
check("List root files", data and data.get("code") == 200, str(err))

# 4b. Create directory
data, err = req("POST", "/api/files/directory",
                {"file_name": "TestDir", "parent_id": 0}, token=TOKEN)
check("Create directory", data and data.get("code") == 200, str(err))
dir_id = data.get("data", {}).get("id") if data else None
check("Got directory ID", bool(dir_id))

# 4c. Verify directory appears in list
data, err = req("GET", "/api/files?parentId=0", token=TOKEN)
files = data.get("data", []) if data else []
check("Directory appears in listing", any(f.get("file_name") == "TestDir" for f in files))

# 4d. Rename
if dir_id:
    data, err = req("PUT", f"/api/files/{dir_id}", {"file_name": "RenamedDir"}, token=TOKEN)
    check("Rename directory", data and data.get("code") == 200, str(err))

# 4e. Delete
if dir_id:
    data, err = req("DELETE", f"/api/files/{dir_id}", token=TOKEN)
    check("Delete directory", data and data.get("code") == 200, str(err))

# 4f. Get non-existent file
data, err = req("GET", "/api/files/99999", token=TOKEN)
check("Get non-existent file returns 404", data and data.get("code") == 404, str(data))


# ── 5. Audit Tests ────────────────────────────────────────────────────────

print("\n" + "=" * 50)
print("5. Audit Log Tests")
print("=" * 50)

# 5a. Query audit logs
data, err = req("GET", "/api/audit-logs?page=1&size=10", token=TOKEN)
check("Query audit logs", data and data.get("code") == 200, str(err))
items = data.get("data", {}).get("items", []) if data else []
check("Has audit entries", len(items) > 0, f"got {len(items)} entries")

# 5b. Check LOGIN was recorded
actions = [item["action"] for item in items]
check("LOGIN action recorded", "LOGIN" in actions, str(actions))

# 5c. Export audit logs
data, err = req("GET", "/api/audit-logs/export", token=TOKEN)
check("Export audit logs as CSV", data is not None, str(err))


# ── 6. RBAC Permission Inheritance Test ───────────────────────────────────

print("\n" + "=" * 50)
print("6. RBAC Permission Inheritance Test")
print("=" * 50)

# Login as a user with no roles → should not exist
data, err = req("POST", "/api/auth/login", {"username": "testuser", "password": "test123"})
test_token = data.get("data", {}).get("token", "") if data else ""

# testuser has no roles assigned, so they should have NO permissions
data, err = req("GET", "/api/files?parentId=0", token=test_token)
if data:
    code = data.get("code", 200)
    check("User without roles denied access", code in (401, 403), f"got code {code}")
else:
    failed += 1
    print(f"  [FAIL] RBAC check request failed")


# ── Summary ───────────────────────────────────────────────────────────────

print("\n" + "=" * 50)
print(f"Results:  {passed} passed  /  {failed} failed  /  {passed+failed} total")
print("=" * 50)

if failed == 0:
    print("\nAll tests passed! System is working correctly.")
else:
    print(f"\n{failed} test(s) failed. Check details above.")
    sys.exit(1)

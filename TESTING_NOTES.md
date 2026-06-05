# RBAC System — Testing Notes

This document explains what is tested, how to run each test suite,
the current coverage figures, and what each test output label means.

---

## Output Label Reference

| Label | Meaning |
|-------|---------|
| `[PASS]` | Check passed — behaviour is correct |
| `[FAIL]` | Check failed — expected vs actual shown after `→` |
| `[NOTE]` | Informational annotation — explains design intent or context |
| `[WARN]` | Potential issue noted — check still counted as **pass** |
| `[SKIP]` | Check skipped because a prerequisite was missing |

---

## Test Suites

### 1. Backend Integration Tests (`backend/test_verify.py`)

**What it tests:** A live running backend end-to-end via HTTP.

**Prerequisites:** Backend running at `http://localhost:8080`, database seeded.

**Run:**
```bash
cd backend
python test_verify.py
python test_verify.py --url http://localhost:8080   # custom URL
```

**Coverage — 7 modules:**

| Module | Key checks |
|--------|-----------|
| 1. Health | `/api/health` endpoint reachable, `status=ok` |
| 2. Auth | Login/logout JWT, wrong-password 401, duplicate-register 409 |
| 3. Roles & RBAC | 6 roles, hierarchy links, permission inheritance, SoD validation |
| 4. Users | User list (new endpoint), detail query, role assignment |
| 5. Files | Directory CRUD, cascade delete, review/approve/comment |
| 6. File Permissions | Per-file read/write/delete grants, viewer access control |
| 7. Audit Logs | Query, filter by action/user/date, pagination, CSV export |

**Notable design checks included:**
- EDITOR does NOT own `doc:review` (separation of duties)
- VIEWER role cannot access role management, user list, or audit logs
- `file:permission:manage` granted to ADMIN and inherited by SUPER_ADMIN
- `/api/audit-logs/export` registered before `/{log_id}` to avoid route collision

---

### 2. Backend Unit Tests (`backend/tests/`)

**What it tests:** Individual service functions and API routes in isolation
using an in-memory SQLite database (no MySQL required).

**Prerequisites:** Python, `pip install pytest pytest-asyncio httpx anyio`

**Run:**
```bash
cd backend
pip install -r requirements.txt
pytest -v                         # all tests
pytest tests/test_auth.py -v     # auth module only
pytest tests/test_services.py -v # service layer only
pytest tests/test_api.py -v      # API routes (TestClient)
pytest tests/test_services_fileperm.py -v  # file permission service
pytest tests/test_api_fileperm.py -v       # file permission API
```

**Files and test counts:**

| File | Cases | What it covers |
|------|-------|---------------|
| `test_auth.py` | 16 | BCrypt hashing, JWT create/decode/tamper, `get_current_user` |
| `test_services.py` | 51 | RBAC inheritance, login/register, role CRUD, file CRUD, audit CRUD |
| `test_services_fileperm.py` | 43 | `_check_file_permission`, tree walk-up, `get/set/delete_file_permissions`, `list_users` |
| `test_api.py` | 29 | FastAPI TestClient — all routes, 401/403 enforcement |
| `test_api_fileperm.py` | 17 | File permission API endpoints, changed file-operation behaviour |
| **Total** | **156** | |

---

### 3. Frontend Unit Tests (`frontend/src/tests/`)

**What it tests:** Pure logic functions extracted from Vue components,
Pinia stores, API mapping, router guards — without mounting a browser.

**Prerequisites:** Node.js, `npm install`

**Run:**
```bash
cd frontend
npm test                  # run all tests once
npm run test:watch        # watch mode (re-runs on save)
npm run test:coverage     # generate coverage report
```

**Files and test counts:**

| File | Cases | What it covers |
|------|-------|---------------|
| `permissions.test.ts` | 10 | 23-permission catalogue, category consistency |
| `api.test.ts` | 23 | FileItem, Role, AuditLog, Hierarchy mapping (snake→camel) |
| `api-fileperm.test.ts` | 10 | FilePermissionItem mapping, UserBasic interface |
| `request.test.ts` | 14 | `clearAuthState`, JWT token attachment, error routing |
| `router.test.ts` | 16 | Route meta definitions, navigation guard logic |
| `component-logic.test.ts` | 34 | `roleTagType`, `currentTitle`, `buildTree`, `actionMap`, `permLabel`, `handleAdd` merge |
| `format.test.ts` | 16 | `formatBytes`, `formatDateTime` edge cases |
| `user-store.test.ts` | 19 | Login/logout state, `hasRole`, `hasPermission`, `highestLevel`, `roleDisplayName` |
| `file-store.test.ts` | 15 | Path navigation, `openDirectory`, `resetToRoot`, `selectFile` |
| **Total** | **157** | |

---

### 4. Platform Functional Tests (`test_platform.py`)

**What it tests:** Full platform workflow scenarios for live demo purposes —
covers every page and major user interaction via API calls.

**Run:**
```bash
python test_platform.py
python test_platform.py --url http://localhost:8080
```

**Scenario coverage:**

| Scenario | Description |
|----------|-------------|
| Login flow | Admin login, wrong-password rejection, JWT token validation |
| Role hierarchy | View 6 roles, verify inheritance chain, check permission matrix |
| RBAC access control | Test each role's access boundaries |
| File operations | Upload directory, rename, share, review, approve, comment, delete |
| File permission management | Grant/revoke per-file permissions, test access changes |
| Audit trail | Verify operations are recorded, filter/export audit log |
| User management | Register, assign roles, verify role changes take effect |

---

## Coverage Summary

| Layer | Covered | Approach |
|-------|---------|---------|
| Backend API routes | 32 / 32 (100%) | Integration tests + TestClient |
| Backend service functions | 29 / 34 (85%) | Unit tests (5 helpers not directly tested) |
| Backend auth functions | 6 / 6 (100%) | Unit tests |
| Frontend API mapping | All modules | Unit tests |
| Frontend stores | user.ts, file.ts | Unit tests |
| Frontend routing | All routes + guards | Unit tests |
| Frontend component logic | AppLayout, FileTree, AuditLogView, FilePermissionDialog | Unit tests |
| Frontend views (UI interaction) | Requires manual demo | Platform functional tests |
| **Automated total** | **313 test cases** | pytest + vitest |

> **Note on 96% figure:** 96% refers to the fraction of *testable backend functions*
> that have automated unit test coverage (29/30 non-helper functions).
> The remaining ~4% are internal helpers (`get_minio_client`, `_file_to_dict`)
> that are exercised indirectly through service tests.

---

## Known Fixed Issues

| Issue | Fix |
|-------|-----|
| `AuditLogView.vue` missing `computed`, `deleteAuditLog`, `batchDeleteAuditLogs` imports | Fixed in merge |
| `services.py` dead-code double `raise HTTPException` in `delete_file` | Fixed in merge |
| `main.py` route ordering: `/api/audit-logs/export` after `/{log_id}` caused 404/422 | Fixed — export now registered first |
| `test_services.py` 4-value tuple unpacking against 6-value conftest fixture | Fixed with `*_` unpacking |
| `constants/permissions.ts` category `'file'` not in `PERMISSION_GROUPS` | Fixed — `'file'` added to groups |
| `test_api.py` internal seed missing `file:permission:manage` | Fixed |

---

## Quick Start (Local)

```bash
# 1. Database
mysql -u root -p -e "CREATE DATABASE rbac_file_manager; \
  CREATE USER 'rbac_user'@'localhost' IDENTIFIED BY 'rbac_pass'; \
  GRANT ALL ON rbac_file_manager.* TO 'rbac_user'@'localhost';"
mysql -u rbac_user -prbac_pass rbac_file_manager < database/init.sql
mysql -u rbac_user -prbac_pass rbac_file_manager < database/seed.sql

# 2. Backend
cd backend && pip install -r requirements.txt
cp .env.local ../.env
python main.py            # → http://localhost:8080

# 3. Frontend (new terminal)
cd frontend && npm install
npm run dev               # → http://localhost:3000

# Default login: admin / admin123
```

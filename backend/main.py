"""FastAPI app — all 22 API routes for the RBAC Document Manager."""

from contextlib import asynccontextmanager
from datetime import datetime

from fastapi import Depends, FastAPI, File, Form, HTTPException, Query, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse, Response
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from auth import get_current_user
from config import settings
from models import ApiResponse
from services import (
    assign_permissions, assign_user_roles, create_directory, create_role,
    delete_file, delete_role, export_audit_logs, get_effective_permissions,
    get_file, get_file_content, get_hierarchy, get_role, get_user_info, list_files, list_roles, login,
    query_audit_logs, record_audit, register, rename_file, share_file,
    update_role, upload_file,
)

# ── Database ───────────────────────────────────────────────────────────────

engine = create_engine(settings.DATABASE_URL, pool_size=10, max_overflow=20)
SessionLocal = sessionmaker(bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ── App ────────────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    engine.dispose()


app = FastAPI(title="RBAC Document Manager", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Permission Check Helper ────────────────────────────────────────────────

def require_perm(permission: str):
    """Dependency factory: return 403 if the current user lacks `permission`."""
    async def _check(request: Request, db: Session = Depends(get_db)):
        await get_current_user(request)
        from models import Role
        for role_name in request.state.roles:
            role = db.query(Role).filter(Role.name == role_name, Role.deleted == False).first()
            if role and permission in get_effective_permissions(role.id, db):
                return True
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    return _check


def get_client_ip(request: Request) -> str:
    if request.client:
        return request.client.host or ""
    return ""


# ── Auth Routes ────────────────────────────────────────────────────────────

@app.post("/api/auth/login")
def api_login(data: dict, request: Request, db: Session = Depends(get_db)):
    result = login(db, data["username"], data["password"], get_client_ip(request))
    return ApiResponse.success(result)


@app.post("/api/auth/register")
def api_register(data: dict, db: Session = Depends(get_db)):
    result = register(db, data["username"], data["password"],
                      data.get("display_name"), data.get("email"))
    return ApiResponse.success(result)


@app.post("/api/auth/logout")
async def api_logout(request: Request, db: Session = Depends(get_db)):
    await get_current_user(request)
    record_audit(db, request.state.user_id, request.state.username, "LOGOUT",
                 ip=get_client_ip(request))
    return ApiResponse.success(message="Logged out")


# ── Role Routes ────────────────────────────────────────────────────────────

@app.get("/api/roles")
def api_list_roles(request: Request, db: Session = Depends(get_db),
                   _=Depends(require_perm("role:read"))):
    return ApiResponse.success(list_roles(db))


@app.get("/api/roles/hierarchy")
def api_role_hierarchy(request: Request, db: Session = Depends(get_db),
                       _=Depends(require_perm("role:read"))):
    return ApiResponse.success(get_hierarchy(db))


@app.get("/api/roles/{role_id}")
def api_get_role(role_id: int, request: Request, db: Session = Depends(get_db),
                 _=Depends(require_perm("role:read"))):
    return ApiResponse.success(get_role(db, role_id))


@app.post("/api/roles")
def api_create_role(data: dict, request: Request, db: Session = Depends(get_db),
                    _=Depends(require_perm("role:create"))):
    return ApiResponse.success(
        create_role(db, data["name"], data.get("description", ""),
                    data.get("permission_ids", [])),
        message="Role created")


@app.put("/api/roles/{role_id}")
def api_update_role(role_id: int, data: dict, request: Request,
                    db: Session = Depends(get_db),
                    _=Depends(require_perm("role:update"))):
    return ApiResponse.success(
        update_role(db, role_id, data.get("name"), data.get("description")),
        message="Role updated")


@app.delete("/api/roles/{role_id}")
def api_delete_role(role_id: int, request: Request, db: Session = Depends(get_db),
                    _=Depends(require_perm("role:delete"))):
    delete_role(db, role_id)
    record_audit(db, request.state.user_id, request.state.username, "DELETE_ROLE",
                 detail=f"Deleted role {role_id}")
    return ApiResponse.success(message="Role deleted")


@app.put("/api/roles/{role_id}/permissions")
def api_assign_permissions(role_id: int, data: dict, request: Request,
                           db: Session = Depends(get_db),
                           _=Depends(require_perm("role:update"))):
    assign_permissions(db, role_id, data["permission_ids"])
    record_audit(db, request.state.user_id, request.state.username, "ASSIGN_PERMISSIONS",
                 detail=f"Permissions assigned to role {role_id}")
    return ApiResponse.success(message="Permissions updated")


@app.put("/api/users/{user_id}/roles")
def api_assign_user_roles(user_id: int, data: dict, request: Request,
                          db: Session = Depends(get_db),
                          _=Depends(require_perm("role:assign"))):
    assign_user_roles(db, user_id, data["role_ids"])
    record_audit(db, request.state.user_id, request.state.username, "ASSIGN_USER_ROLES",
                 detail=f"Roles assigned to user {user_id}")
    return ApiResponse.success(message="User roles updated")


@app.get("/api/users/{user_id}")
def api_get_user(user_id: int, request: Request, db: Session = Depends(get_db),
                  _=Depends(require_perm("role:read"))):
    return ApiResponse.success(get_user_info(db, user_id))


# ── File Routes ────────────────────────────────────────────────────────────

@app.get("/api/files")
def api_list_files(parentId: int = Query(0), request: Request = None,
                   db: Session = Depends(get_db),
                   _=Depends(require_perm("doc:read"))):
    return ApiResponse.success(list_files(db, parentId))


@app.get("/api/files/{file_id}")
def api_get_file(file_id: int, request: Request = None, db: Session = Depends(get_db),
                 _=Depends(require_perm("doc:read"))):
    return ApiResponse.success(get_file(db, file_id))


@app.get("/api/files/{file_id}/download")
def api_download_file(file_id: int, request: Request = None, db: Session = Depends(get_db),
                       _=Depends(require_perm("doc:read"))):
    content, mime_type, file_name = get_file_content(db, file_id)
    return Response(content=content, media_type=mime_type,
                    headers={"Content-Disposition": f'inline; filename="{file_name}"'})


@app.post("/api/files")
async def api_upload_file(request: Request, file: UploadFile = File(...),
                          parentId: int = Form(0), db: Session = Depends(get_db)):
    await get_current_user(request)
    await require_perm("doc:create")(request, db)
    result = await upload_file(db, file, parentId, request.state.user_id)
    record_audit(db, request.state.user_id, request.state.username, "UPLOAD_FILE",
                 detail=f"Uploaded {file.filename}")
    return ApiResponse.success(result, message="File uploaded")


@app.post("/api/files/directory")
async def api_create_directory(data: dict, request: Request, db: Session = Depends(get_db)):
    await get_current_user(request)
    await require_perm("doc:create")(request, db)
    result = create_directory(db, data["file_name"], data.get("parent_id", 0),
                              request.state.user_id)
    record_audit(db, request.state.user_id, request.state.username, "CREATE_DIRECTORY",
                 detail=f"Created directory {data['file_name']}")
    return ApiResponse.success(result, message="Directory created")


@app.put("/api/files/{file_id}")
async def api_rename_file(file_id: int, data: dict, request: Request,
                          db: Session = Depends(get_db)):
    await get_current_user(request)
    await require_perm("doc:update")(request, db)
    result = rename_file(db, file_id, data.get("file_name", ""))
    record_audit(db, request.state.user_id, request.state.username, "RENAME_FILE",
                 detail=f"Renamed file {file_id}")
    return ApiResponse.success(result, message="File updated")


@app.delete("/api/files/{file_id}")
async def api_delete_file(file_id: int, request: Request, db: Session = Depends(get_db)):
    await get_current_user(request)
    await require_perm("doc:delete")(request, db)
    delete_file(db, file_id)
    record_audit(db, request.state.user_id, request.state.username, "DELETE_FILE",
                 detail=f"Deleted file {file_id}")
    return ApiResponse.success(message="File deleted")


@app.post("/api/files/{file_id}/share")
async def api_share_file(file_id: int, data: dict, request: Request,
                         db: Session = Depends(get_db)):
    await get_current_user(request)
    await require_perm("doc:share")(request, db)
    share_file(db, file_id, data.get("user_ids", []), data.get("role_ids", []))
    record_audit(db, request.state.user_id, request.state.username, "SHARE_FILE",
                 detail=f"Shared file {file_id}")
    return ApiResponse.success(message="File shared")


@app.post("/api/files/{file_id}/review")
async def api_review_file(file_id: int, data: dict, request: Request,
                          db: Session = Depends(get_db)):
    await get_current_user(request)
    await require_perm("doc:review")(request, db)
    record_audit(db, request.state.user_id, request.state.username, "REVIEW_FILE",
                 detail=f"Reviewed file {file_id}")
    return ApiResponse.success(message="Review submitted")


@app.post("/api/files/{file_id}/approve")
async def api_approve_file(file_id: int, data: dict, request: Request,
                           db: Session = Depends(get_db)):
    await get_current_user(request)
    await require_perm("doc:approve")(request, db)
    record_audit(db, request.state.user_id, request.state.username, "APPROVE_FILE",
                 detail=f"Approved file {file_id}")
    return ApiResponse.success(message="File approved")


@app.post("/api/files/{file_id}/comment")
async def api_comment_file(file_id: int, data: dict, request: Request,
                           db: Session = Depends(get_db)):
    await get_current_user(request)
    await require_perm("doc:comment")(request, db)
    record_audit(db, request.state.user_id, request.state.username, "COMMENT_FILE",
                 detail=f"Commented on file {file_id}")
    return ApiResponse.success(message="Comment added")


# ── Audit Routes ───────────────────────────────────────────────────────────

@app.get("/api/audit-logs")
def api_audit_logs(request: Request, page: int = Query(1), size: int = Query(20),
                   action: str = Query(None), userId: int = Query(None),
                   db: Session = Depends(get_db), _=Depends(require_perm("audit:read"))):
    return ApiResponse.success(query_audit_logs(db, page, size, action, userId))


@app.get("/api/audit-logs/export")
def api_export_audit(request: Request, db: Session = Depends(get_db),
                     _=Depends(require_perm("audit:export"))):
    csv_content = export_audit_logs(db)
    return PlainTextResponse(content=csv_content, media_type="text/csv",
                             headers={"Content-Disposition": "attachment; filename=audit_logs.csv"})


# ── Health ─────────────────────────────────────────────────────────────────

@app.get("/api/health")
def health():
    return {"status": "ok", "time": datetime.now().isoformat()}


# ── Entry ──────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8080, reload=True)

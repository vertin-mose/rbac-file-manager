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
from models import ApiResponse, Base
from services import (
    admin_create_user, admin_delete_user, admin_update_user,
    assign_permissions, assign_user_roles,
    batch_delete_audit_logs, can_manage_file_permissions,
    comment_file, create_directory, create_role, delete_activity, delete_audit_log, delete_file,
    delete_file_permission, delete_role,
    ensure_missing_columns, ensure_missing_permissions, export_audit_logs, get_effective_permissions,
    get_file, get_file_activities, get_file_content, get_file_permissions, get_hierarchy, get_hierarchy_structure, get_role, get_user_info,
    list_files, list_roles, list_users, login, query_audit_logs, record_audit, register,
    rename_file, review_file, approve_file,
    set_file_permissions, share_file, toggle_user_status, update_file_content, update_file_text_content, update_own_profile, update_role, upload_file,
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
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        ensure_missing_columns(db)
        ensure_missing_permissions(db)
    finally:
        db.close()
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
def api_register(data: dict, request: Request, db: Session = Depends(get_db)):
    result = register(db, data["username"], data["password"],
                      data.get("display_name"), data.get("email"))
    record_audit(db, result["id"], result["username"], "REGISTER",
                 detail=f"用户{result['username']}注册成功", ip=get_client_ip(request))
    return ApiResponse.success(result)


@app.post("/api/auth/logout")
async def api_logout(request: Request, db: Session = Depends(get_db)):
    await get_current_user(request)
    record_audit(db, request.state.user_id, request.state.username, "LOGOUT",
                 detail=f"用户{request.state.username}已登出", ip=get_client_ip(request))
    return ApiResponse.success(message="Logged out")


@app.get("/api/auth/me")
async def api_auth_me(request: Request, db: Session = Depends(get_db)):
    """Return current user info and effective permissions (fresh from DB, not cached)."""
    await get_current_user(request)
    from models import Role
    all_perms = set()
    for role_name in request.state.roles:
        role = db.query(Role).filter(Role.name == role_name, Role.deleted == False).first()
        if role:
            all_perms |= get_effective_permissions(role.id, db)
    return ApiResponse.success({
        "user_id": request.state.user_id,
        "username": request.state.username,
        "roles": request.state.roles,
        "permissions": sorted(all_perms),
    })


@app.put("/api/auth/profile")
async def api_update_profile(data: dict, request: Request,
                              db: Session = Depends(get_db)):
    """Current user updates their own display_name, email, or password."""
    await get_current_user(request)
    result = update_own_profile(
        db, request.state.user_id,
        display_name=data.get("display_name"),
        email=data.get("email"),
        old_password=data.get("old_password"),
        new_password=data.get("new_password"),
    )
    return ApiResponse.success(result, message="Profile updated")


# ── Role Routes ────────────────────────────────────────────────────────────

@app.get("/api/roles")
def api_list_roles(request: Request, db: Session = Depends(get_db),
                   _=Depends(require_perm("role:read"))):
    return ApiResponse.success(list_roles(db))


@app.get("/api/roles/hierarchy")
def api_role_hierarchy(request: Request, db: Session = Depends(get_db),
                       _=Depends(require_perm("role:read"))):
    return ApiResponse.success(get_hierarchy(db))


@app.get("/api/roles/hierarchy/structure")
def api_role_hierarchy_structure(request: Request, db: Session = Depends(get_db),
                                  _=Depends(require_perm("role:read"))):
    return ApiResponse.success(get_hierarchy_structure(db))


@app.get("/api/roles/{role_id}")
def api_get_role(role_id: int, request: Request, db: Session = Depends(get_db),
                 _=Depends(require_perm("role:read"))):
    return ApiResponse.success(get_role(db, role_id))


@app.post("/api/roles")
def api_create_role(data: dict, request: Request, db: Session = Depends(get_db),
                    _=Depends(require_perm("role:create"))):
    result = create_role(db, data["name"], data.get("description", ""),
                         data.get("permission_ids", []),
                         data.get("inherited_role_ids"),
                         data.get("rewire_children", False))
    record_audit(db, request.state.user_id, request.state.username, "CREATE_ROLE",
                 detail=f"创建了角色{data['name']}")
    return ApiResponse.success(result, message="Role created")


@app.put("/api/roles/{role_id}")
def api_update_role(role_id: int, data: dict, request: Request,
                    db: Session = Depends(get_db),
                    _=Depends(require_perm("role:update"))):
    result = update_role(db, role_id, data.get("name"), data.get("description"))
    record_audit(db, request.state.user_id, request.state.username, "UPDATE_ROLE",
                 detail=f"更新了角色{result['name']}")
    return ApiResponse.success(result, message="Role updated")


@app.delete("/api/roles/{role_id}")
def api_delete_role(role_id: int, request: Request, db: Session = Depends(get_db),
                    _=Depends(require_perm("role:delete"))):
    from models import Role
    role = db.get(Role, role_id)
    role_name = role.name if role else str(role_id)
    delete_role(db, role_id)
    record_audit(db, request.state.user_id, request.state.username, "DELETE_ROLE",
                 detail=f"删除了角色{role_name}")
    return ApiResponse.success(message="Role deleted")


@app.put("/api/roles/{role_id}/permissions")
def api_assign_permissions(role_id: int, data: dict, request: Request,
                           db: Session = Depends(get_db),
                           _=Depends(require_perm("role:update"))):
    assign_permissions(db, role_id, data["permission_ids"])
    from models import Permission, Role
    role = db.get(Role, role_id)
    perm_names = [p.name for p in db.query(Permission).filter(Permission.id.in_(data["permission_ids"]), Permission.deleted == False).all()]
    record_audit(db, request.state.user_id, request.state.username, "ASSIGN_PERMISSIONS",
                 detail=f"为角色{role.name if role else role_id}分配了权限: {', '.join(perm_names) if perm_names else '无'}")
    return ApiResponse.success(message="Permissions updated")


@app.put("/api/users/{user_id}/roles")
def api_assign_user_roles(user_id: int, data: dict, request: Request,
                          db: Session = Depends(get_db),
                          _=Depends(require_perm("role:assign"))):
    assign_user_roles(db, user_id, data["role_ids"])
    from models import Role, User
    user = db.get(User, user_id)
    role_names = [r.name for r in db.query(Role).filter(Role.id.in_(data["role_ids"]), Role.deleted == False).all()]
    record_audit(db, request.state.user_id, request.state.username, "ASSIGN_USER_ROLES",
                 detail=f"为用户{user.username if user else user_id}分配了角色: {', '.join(role_names) if role_names else '无'}")
    return ApiResponse.success(message="User roles updated")


@app.get("/api/users")
def api_list_users(request: Request, db: Session = Depends(get_db),
                   _=Depends(require_perm("user:read"))):
    return ApiResponse.success(list_users(db))


@app.get("/api/users/{user_id}")
def api_get_user(user_id: int, request: Request, db: Session = Depends(get_db),
                  _=Depends(require_perm("role:read"))):
    return ApiResponse.success(get_user_info(db, user_id))


@app.post("/api/users")
def api_admin_create_user(data: dict, request: Request, db: Session = Depends(get_db),
                           _=Depends(require_perm("user:create"))):
    result = admin_create_user(db, data["username"], data["password"],
                                data.get("display_name"), data.get("email"),
                                data.get("role_ids"))
    record_audit(db, request.state.user_id, request.state.username, "CREATE_USER",
                 detail=f"管理员创建了用户 {result['username']}")
    return ApiResponse.success(result, message="User created")


@app.put("/api/users/{user_id}/status")
def api_toggle_user_status(user_id: int, request: Request,
                            db: Session = Depends(get_db),
                            _=Depends(require_perm("user:update"))):
    result = toggle_user_status(db, user_id)
    status_text = "启用" if result["enabled"] else "禁用"
    record_audit(db, request.state.user_id, request.state.username, "TOGGLE_USER_STATUS",
                 detail=f"{status_text}了用户 {result['username']}")
    return ApiResponse.success(result, message=f"User {status_text}")


@app.delete("/api/users/{user_id}")
def api_admin_delete_user(user_id: int, request: Request,
                           db: Session = Depends(get_db),
                           _=Depends(require_perm("user:delete"))):
    from models import User
    user = db.get(User, user_id)
    username = user.username if user else str(user_id)
    admin_delete_user(db, user_id)
    record_audit(db, request.state.user_id, request.state.username, "DELETE_USER",
                 detail=f"删除了用户 {username}")
    return ApiResponse.success(message="User deleted")


@app.put("/api/users/{user_id}")
def api_admin_update_user(user_id: int, data: dict, request: Request,
                           db: Session = Depends(get_db),
                           _=Depends(require_perm("user:update"))):
    result = admin_update_user(
        db, user_id,
        display_name=data.get("display_name"),
        email=data.get("email"),
        reset_password=data.get("reset_password", False),
    )
    from models import User
    user = db.get(User, user_id)
    uname = user.username if user else str(user_id)
    record_audit(db, request.state.user_id, request.state.username, "UPDATE_USER",
                 detail=f"管理员更新了用户 {uname}")
    return ApiResponse.success(result, message="User updated")


# ── File Routes ────────────────────────────────────────────────────────────

@app.get("/api/files")
def api_list_files(parentId: int = Query(0), request: Request = None,
                   db: Session = Depends(get_db),
                   _=Depends(require_perm("doc:read"))):
    return ApiResponse.success(list_files(db, parentId,
                                          request.state.user_id, request.state.roles))


@app.get("/api/files/{file_id}")
async def api_get_file(file_id: int, request: Request = None, db: Session = Depends(get_db)):
    await get_current_user(request)
    result = get_file(db, file_id, request.state.user_id, request.state.roles)
    record_audit(db, request.state.user_id, request.state.username, "VIEW_FILE",
                 detail=f"查看了文件{result.get('file_name', file_id)}")
    return ApiResponse.success(result)


@app.get("/api/files/{file_id}/download")
async def api_download_file(file_id: int, request: Request = None, db: Session = Depends(get_db)):
    await get_current_user(request)
    content, mime_type, file_name = get_file_content(db, file_id,
                                                      request.state.user_id, request.state.roles)
    record_audit(db, request.state.user_id, request.state.username, "DOWNLOAD_FILE",
                 detail=f"下载了文件{file_name}")
    return Response(content=content, media_type=mime_type,
                    headers={"Content-Disposition": f'inline; filename="{file_name}"'})


@app.post("/api/files")
async def api_upload_file(request: Request, file: UploadFile = File(...),
                          parentId: int = Form(0), db: Session = Depends(get_db),
                          _=Depends(require_perm("doc:create"))):
    await get_current_user(request)
    if parentId:
        from services import _check_file_permission
        if not _check_file_permission(db, parentId, request.state.user_id,
                                       request.state.roles, "write"):
            raise HTTPException(status_code=403, detail="No permission to upload to this directory")
    result = await upload_file(db, file, parentId, request.state.user_id)
    record_audit(db, request.state.user_id, request.state.username, "UPLOAD_FILE",
                 detail=f"上传了文件{file.filename}")
    return ApiResponse.success(result, message="File uploaded")


@app.post("/api/files/directory")
async def api_create_directory(data: dict, request: Request, db: Session = Depends(get_db),
                                _=Depends(require_perm("doc:create"))):
    await get_current_user(request)
    parent_id = data.get("parent_id", 0)
    if parent_id:
        from services import _check_file_permission
        if not _check_file_permission(db, parent_id, request.state.user_id,
                                       request.state.roles, "write"):
            raise HTTPException(status_code=403, detail="No permission to create in this directory")
    result = create_directory(db, data["file_name"], parent_id,
                              request.state.user_id)
    record_audit(db, request.state.user_id, request.state.username, "CREATE_DIRECTORY",
                 detail=f"创建了目录{data['file_name']}")
    return ApiResponse.success(result, message="Directory created")


@app.put("/api/files/{file_id}")
async def api_rename_file(file_id: int, data: dict, request: Request,
                          db: Session = Depends(get_db),
                          _=Depends(require_perm("doc:update"))):
    await get_current_user(request)
    from models import FileRecord
    f = db.get(FileRecord, file_id)
    old_name = f.file_name if f else str(file_id)
    new_name = data.get("file_name", "")
    result = rename_file(db, file_id, new_name,
                         request.state.user_id, request.state.roles)
    record_audit(db, request.state.user_id, request.state.username, "RENAME_FILE",
                 detail=f"重命名{'目录' if f and f.is_directory else '文件'}{old_name}为{new_name}")
    return ApiResponse.success(result, message="File updated")


@app.delete("/api/files/{file_id}")
async def api_delete_file(file_id: int, request: Request, db: Session = Depends(get_db),
                           _=Depends(require_perm("doc:delete"))):
    await get_current_user(request)
    from models import FileRecord
    f = db.get(FileRecord, file_id)
    file_name = f.file_name if f else str(file_id)
    delete_file(db, file_id, request.state.user_id, request.state.roles)
    record_audit(db, request.state.user_id, request.state.username, "DELETE_FILE",
                 detail=f"删除了{'目录' if f and f.is_directory else '文件'}{file_name}")
    return ApiResponse.success(message="File deleted")


@app.post("/api/files/{file_id}/share")
async def api_share_file(file_id: int, data: dict, request: Request,
                         db: Session = Depends(get_db)):
    await get_current_user(request)
    await require_perm("doc:share")(request, db)
    from models import FileRecord
    f = db.get(FileRecord, file_id)
    file_name = f.file_name if f else str(file_id)
    user_ids = data.get("user_ids", [])
    permission_type = data.get("permission_type", "read")
    result = share_file(db, file_id, user_ids, permission_type)
    if result["granted"]:
        record_audit(db, request.state.user_id, request.state.username, "SHARE_FILE",
                     detail=f"共享了文件{file_name}给用户 {result['granted']}，权限: {permission_type}")
    return ApiResponse.success(result, message="File shared")


@app.post("/api/files/{file_id}/review")
async def api_review_file(file_id: int, data: dict, request: Request,
                          db: Session = Depends(get_db)):
    await get_current_user(request)
    await require_perm("doc:review")(request, db)
    comment = data.get("content", "")
    result = review_file(db, file_id, request.state.user_id, comment)
    record_audit(db, request.state.user_id, request.state.username, "REVIEW_FILE",
                 detail=f"审阅了文件{result.get('file_name', file_id)}，状态→审阅中")
    return ApiResponse.success(result, message="Review submitted")


@app.post("/api/files/{file_id}/approve")
async def api_approve_file(file_id: int, data: dict, request: Request,
                           db: Session = Depends(get_db)):
    await get_current_user(request)
    await require_perm("doc:approve")(request, db)
    approved = data.get("approved", True)
    comment = data.get("content", "")
    result = approve_file(db, file_id, request.state.user_id, approved, comment)
    status_label = "批准" if approved else "驳回"
    record_audit(db, request.state.user_id, request.state.username, "APPROVE_FILE",
                 detail=f"{status_label}了文件{result.get('file_name', file_id)}")
    return ApiResponse.success(result, message=f"File {status_label}")


@app.post("/api/files/{file_id}/comment")
async def api_comment_file(file_id: int, data: dict, request: Request,
                           db: Session = Depends(get_db)):
    await get_current_user(request)
    await require_perm("doc:comment")(request, db)
    from models import FileRecord
    f = db.get(FileRecord, file_id)
    result = comment_file(db, file_id, request.state.user_id, data.get("content", ""))
    record_audit(db, request.state.user_id, request.state.username, "COMMENT_FILE",
                 detail=f"评论了文件{f.file_name if f else file_id}：{data.get('content','')[:50]}")
    return ApiResponse.success(result, message="Comment added")


@app.put("/api/files/{file_id}/content")
async def api_update_file_content(file_id: int, request: Request,
                                   file: UploadFile = File(...),
                                   db: Session = Depends(get_db),
                                   _=Depends(require_perm("doc:update"))):
    await get_current_user(request)
    result = update_file_content(db, file_id, file,
                                  request.state.user_id, request.state.roles)
    from models import FileRecord
    f = db.get(FileRecord, file_id)
    record_audit(db, request.state.user_id, request.state.username, "UPDATE_FILE",
                 detail=f"更新了文件{f.file_name if f else file_id}的内容")
    return ApiResponse.success(result, message="File updated")


@app.put("/api/files/{file_id}/content/text")
async def api_update_file_text_content(file_id: int, data: dict, request: Request,
                                        db: Session = Depends(get_db),
                                        _=Depends(require_perm("doc:edit"))):
    await get_current_user(request)
    result = update_file_text_content(db, file_id, data["content"],
                                       request.state.user_id, request.state.roles)
    from models import FileRecord
    f = db.get(FileRecord, file_id)
    record_audit(db, request.state.user_id, request.state.username, "EDIT_FILE",
                 detail=f"编辑了文件{f.file_name if f else file_id}的内容")
    return ApiResponse.success(result, message="File saved")


@app.get("/api/files/{file_id}/content/text")
async def api_get_file_text_content(file_id: int, request: Request = None, db: Session = Depends(get_db),
                                     _=Depends(require_perm("doc:edit"))):
    """Return file content as plain text (for inline editing). Logs as EDIT_FILE."""
    await get_current_user(request)
    content, mime_type, file_name = get_file_content(db, file_id,
                                                      request.state.user_id, request.state.roles)
    record_audit(db, request.state.user_id, request.state.username, "EDIT_FILE",
                 detail=f"打开编辑了文件{file_name}")
    return Response(content=content, media_type="text/plain; charset=utf-8",
                    headers={"Content-Disposition": f'inline; filename="{file_name}"'})


@app.get("/api/files/{file_id}/activities")
async def api_get_file_activities(file_id: int, request: Request,
                                  db: Session = Depends(get_db)):
    await get_current_user(request)
    return ApiResponse.success(get_file_activities(db, file_id))


@app.delete("/api/files/{file_id}/activities/{activity_id}")
async def api_delete_activity(file_id: int, activity_id: int, request: Request,
                               db: Session = Depends(get_db)):
    await get_current_user(request)
    delete_activity(db, activity_id, request.state.user_id, request.state.roles)
    record_audit(db, request.state.user_id, request.state.username, "DELETE_ACTIVITY",
                 detail=f"删除了文件{file_id}的活动记录{activity_id}")
    return ApiResponse.success(message="Activity deleted")


# ── Audit Routes ───────────────────────────────────────────────────────────


@app.get("/api/files/{file_id}/permissions")
def api_get_file_permissions(file_id: int, request: Request, db: Session = Depends(get_db),
                             _=Depends(require_perm("doc:read"))):
    return ApiResponse.success(get_file_permissions(db, file_id))


@app.put("/api/files/{file_id}/permissions")
async def api_set_file_permissions(file_id: int, data: dict, request: Request,
                                   db: Session = Depends(get_db)):
    await get_current_user(request)
    if not can_manage_file_permissions(db, file_id, request.state.user_id, request.state.roles):
        raise HTTPException(status_code=403, detail="No permission to manage file permissions")
    result = set_file_permissions(db, file_id, data.get("permissions", []))
    from models import FileRecord
    f = db.get(FileRecord, file_id)
    record_audit(db, request.state.user_id, request.state.username, "SET_FILE_PERMISSIONS",
                 detail=f"更新了文件{f.file_name if f else file_id}的权限配置")
    return ApiResponse.success(result, message="File permissions updated")


@app.delete("/api/files/{file_id}/permissions/{perm_id}")
async def api_delete_file_permission(file_id: int, perm_id: int, request: Request,
                                     db: Session = Depends(get_db)):
    await get_current_user(request)
    if not can_manage_file_permissions(db, file_id, request.state.user_id, request.state.roles):
        raise HTTPException(status_code=403, detail="No permission to manage file permissions")
    delete_file_permission(db, perm_id)
    record_audit(db, request.state.user_id, request.state.username, "DELETE_FILE_PERMISSION",
                 detail=f"删除了文件{file_id}的权限记录{perm_id}")
    return ApiResponse.success(message="File permission deleted")

@app.get("/api/audit-logs/export")
def api_export_audit(request: Request, action: str = Query(None), username: str = Query(None),
                     startDate: str = Query(None), endDate: str = Query(None),
                     db: Session = Depends(get_db),
                     _=Depends(require_perm("audit:export"))):
    csv_content = export_audit_logs(db, action, username, startDate, endDate)
    return PlainTextResponse(content=csv_content, media_type="text/csv",
                             headers={"Content-Disposition": "attachment; filename=audit_logs.csv"})


@app.get("/api/audit-logs")
def api_audit_logs(request: Request, page: int = Query(1), size: int = Query(20),
                   action: str = Query(None), username: str = Query(None),
                   startDate: str = Query(None), endDate: str = Query(None),
                   db: Session = Depends(get_db), _=Depends(require_perm("audit:read"))):
    return ApiResponse.success(query_audit_logs(db, page, size, action, username,
                                                  startDate, endDate))


@app.delete("/api/audit-logs/{log_id}")
def api_delete_audit_log(log_id: int, request: Request, db: Session = Depends(get_db),
                          _=Depends(require_perm("audit:read"))):
    delete_audit_log(db, log_id)
    return ApiResponse.success(message="Audit log deleted")


@app.delete("/api/audit-logs")
def api_batch_delete_audit_logs(data: dict, request: Request, db: Session = Depends(get_db),
                                 _=Depends(require_perm("audit:read"))):
    ids = data.get("ids", [])
    if not ids:
        raise HTTPException(status_code=400, detail="ids is required")
    batch_delete_audit_logs(db, ids)
    return ApiResponse.success(message=f"{len(ids)} audit logs deleted")


# ── Health ─────────────────────────────────────────────────────────────────

@app.get("/api/health")
def health():
    return {"status": "ok", "time": datetime.now().isoformat()}


# ── Entry ──────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8080, reload=True)

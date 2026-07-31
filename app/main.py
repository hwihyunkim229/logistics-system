import os
import sys
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi import Request
from fastapi.responses import RedirectResponse
from starlette.middleware.base import (
    BaseHTTPMiddleware
)
from starlette.middleware.sessions import (
    SessionMiddleware
)
from passlib.context import CryptContext
from app.database import (
    engine,
    Base,
    SessionLocal
)
from app.models import (
    inbound,
    outbound,
    item,
    movement,
    user,
    activity_log,
    stock,
    stock_movement,
    item_master_history,
    bom,
    production_plan,
    inventory,
    inventory_movement,
    material_note,
    material_master,
    item_master,
    rental_stock,
    rental_movement,
    rental_category,
    access_log,
    user_permission,
)
from app.models.material_master import MaterialMaster
from app.models.user import User
from app.routers import (
    scan,
    upload,
    auth,
    dashboard,
    admin,
    stock,
    stock_dashboard,
    mrp,
    inventory as inventory_router,
    assistant,
    rental
)
from app.workflow.routers import (
    purchase,
    quality,
    material,
    production,
    remnant as workflow_remnant,
    dashboard as workflow_dashboard,
    history as workflow_history,
    notification as workflow_notification,
)
import app.workflow.models
from app.workflow.schema import ensure_workflow_schema
from app.rental_schema import ensure_rental_schema
import time
from fastapi.responses import JSONResponse, Response
from app.utils.access_logger import save_access_log, should_record
from app.utils.permissions import (
    ALWAYS_ALLOWED_PREFIXES,
    action_for_request,
    feature_for_path,
    first_allowed_home,
    permission_map,
)

app = FastAPI()

@app.api_route("/health", methods=["GET", "HEAD"])
async def health(request: Request):
    if request.method == "HEAD":
        return Response(status_code=200)
    return JSONResponse({"status": "ok"})

pwd_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto"
)

SECRET_KEY = os.getenv("SECRET_KEY")

if not SECRET_KEY:
    raise RuntimeError(
        "SECRET_KEY 환경변수가 설정되지 않았습니다."
    )

class AuthMiddleware(BaseHTTPMiddleware):

    async def dispatch(
        self,
        request: Request,
        call_next
    ):
        path = request.url.path

        if (
            path.startswith("/login")
            or path.startswith("/register")
            or path.startswith("/static")
            or path.startswith("/workflow/static")
            or path.startswith("/health")
            or path == "/favicon.ico"
        ):

            return await call_next(request)

        user = request.session.get("user")

        if not user:
            response = RedirectResponse("/login")
            if should_record(path):
                save_access_log(
                    request=request,
                    status_code=response.status_code,
                    user="anonymous",
                    result="인증필요",
                    detail="로그인 세션 없이 접근",
                )
            return response

        last_activity = request.session.get(
            "last_activity",
            time.time()
        )

        if time.time() - last_activity > 7200:

            request.session.clear()

            response = RedirectResponse(
                "/login?expired=1",
                status_code=302
            )
            save_access_log(
                request=request,
                status_code=response.status_code,
                user=user,
                result="세션만료",
                detail="2시간 이상 활동이 없어 세션 만료",
            )
            return response

        request.session["last_activity"] = time.time()

        db = SessionLocal()

        try:
            account = (
                db.query(User)
                .filter(User.username == user)
                .first()
            )
        finally:
            db.close()

        if account is None:
            request.session.clear()
            response = RedirectResponse("/login")
            save_access_log(
                request=request,
                status_code=response.status_code,
                user=user,
                result="계정없음",
                detail="세션의 사용자 계정이 DB에 없음",
            )
            return response

        team = (account.team or "").strip()
        role = account.role or "user"

        request.session["team"] = team
        request.session["role"] = role

        permission_db = SessionLocal()
        try:
            permissions = permission_map(permission_db, account)
        finally:
            permission_db.close()

        request.state.permissions = {
            f"{feature}.{action}": allowed
            for (feature, action), allowed in permissions.items()
        }
        request.state.is_admin = role == "admin"

        is_common_path = any(
            path.startswith(prefix)
            for prefix in ALWAYS_ALLOWED_PREFIXES
        )
        request.state.current_feature = (
            ""
            if is_common_path or role == "admin"
            else feature_for_path(path)
        )

        if not is_common_path:
            feature = feature_for_path(path)
            action = action_for_request(request.method, path)
            allowed = (
                role == "admin"
                if feature == "admin"
                else permissions.get((feature, action), False)
            )

            if not allowed:
                action_name = {
                    "view": "조회",
                    "edit": "수정",
                    "download": "다운로드",
                }[action]
                allowed_home = first_allowed_home(
                    permissions,
                    preferred_feature=feature,
                )
                if allowed_home is None:
                    return Response(
                        content=(
                            "<h2>사용 가능한 페이지가 없습니다.</h2>"
                            "<p>관리자에게 조회 권한을 요청해 주세요.</p>"
                            '<a href="/logout">로그아웃</a>'
                        ),
                        status_code=403,
                        media_type="text/html",
                    )
                return RedirectResponse(
                    f"{allowed_home}?error={action_name} 권한이 없습니다.",
                    status_code=303,
                )

        response = await call_next(request)

        response.headers["Cache-Control"] = (
            "no-store, no-cache, must-revalidate"
        )
        response.headers["Pragma"] = "no-cache"

        if should_record(path):
            save_access_log(
                request=request,
                status_code=response.status_code,
                user=user,
            )

        return response

app.add_middleware(
    AuthMiddleware
)

app.add_middleware(
    SessionMiddleware,
    secret_key=SECRET_KEY
)

app.mount(
    "/static",
    StaticFiles(
        directory="app/static"
    ),
    name="static"
)

app.mount(
    "/workflow/static",
    StaticFiles(
        directory="app/workflow/static"
    ),
    name="workflow_static"
)

app.include_router(scan.router)
app.include_router(upload.router)
app.include_router(auth.router)
app.include_router(dashboard.router)
app.include_router(admin.router)
app.include_router(stock.router)
app.include_router(stock_dashboard.router)
app.include_router(mrp.router)
app.include_router(inventory_router.router)
app.include_router(assistant.router)
app.include_router(rental.router)
app.include_router(purchase.router)
app.include_router(quality.router)
app.include_router(material.router)
app.include_router(production.router)
app.include_router(workflow_remnant.router)
app.include_router(workflow_dashboard.router)
app.include_router(workflow_history.router)
app.include_router(workflow_notification.router)

Base.metadata.create_all(
    bind=engine
)

ensure_workflow_schema(engine)
ensure_rental_schema(engine)

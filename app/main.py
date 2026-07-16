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
    rental_category
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

TEAM_WRITE_PREFIXES = {
    "purchase": ["/workflow/purchase"],
    "quality": ["/workflow/quality"],
    "material": ["/workflow/material", "/workflow/remnant"],
    "production": ["/workflow/production"],
}

TEAM_COMMON_WRITE_PREFIXES = [
    "/change-password",
    "/assistant",
    "/workflow/notification",
]

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

            return await call_next(
                request
            )

        user = request.session.get("user")

        if not user:
            return RedirectResponse("/login")

        last_activity = request.session.get(
            "last_activity",
            time.time()
        )

        if time.time() - last_activity > 7200:

            request.session.clear()

            return RedirectResponse(
                "/login?expired=1",
                status_code=302
            )

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
            return RedirectResponse("/login")

        team = (account.team or "").strip()
        role = account.role or "user"

        request.session["team"] = team
        request.session["role"] = role

        if role == "viewer":
            viewer_allowed_writes = (
                "/change-password",
                "/assistant",
            )

            is_allowed_viewer_write = any(
                path.startswith(prefix)
                for prefix in viewer_allowed_writes
            )

            if (
                request.method != "GET"
                and not is_allowed_viewer_write
            ):
                return RedirectResponse(
                    "/search?error=조회 전용 계정입니다.",
                    status_code=303,
                )

            lowered = path.lower()

            if request.method == "GET" and any(
                keyword in lowered
                for keyword in (
                    "download",
                    "export",
                    "backup",
                )
            ):
                return RedirectResponse(
                    "/search?error=다운로드 권한이 없습니다.",
                    status_code=303,
                )

        if team and role != "admin":
            allowed_writes = (
                TEAM_WRITE_PREFIXES.get(team, [])
                + TEAM_COMMON_WRITE_PREFIXES
            )

            is_allowed_write = any(
                path.startswith(prefix)
                for prefix in allowed_writes
            )

            if request.method != "GET" and not is_allowed_write:
                return RedirectResponse(
                    f"/workflow/{team}?error=조회 전용 계정입니다.",
                    status_code=303,
                )

            lowered = path.lower()

            if request.method == "GET" and any(
                keyword in lowered
                for keyword in ("download", "export", "backup")
            ) and not is_allowed_write:
                return RedirectResponse(
                    f"/workflow/{team}?error=다운로드 권한이 없습니다.",
                    status_code=303,
                )

        response = await call_next(request)

        response.headers["Cache-Control"] = (
            "no-store, no-cache, must-revalidate"
        )
        response.headers["Pragma"] = "no-cache"

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

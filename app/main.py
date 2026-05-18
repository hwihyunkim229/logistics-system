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

# =========================
# models
# =========================

from app.models import (
    inbound,
    outbound,
    item,
    movement,
    user,
    activity_log
)

from app.models.user import User

# =========================
# routers
# =========================

from app.routers import (
    scan,
    upload,
    auth,
    dashboard,
    admin
)

# =========================
# app
# =========================

app = FastAPI()

# =========================
# password context
# =========================

pwd_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto"
)

# =========================
# auth middleware
# =========================

class AuthMiddleware(BaseHTTPMiddleware):

    async def dispatch(
        self,
        request: Request,
        call_next
    ):

        path = request.url.path

        # 🔥 로그인 허용 경로
        if (
            path.startswith("/login")
            or path.startswith("/register")
            or path.startswith("/static")
            or path == "/favicon.ico"
        ):

            return await call_next(
                request
            )

        # 🔥 session 확인
        user = request.session.get(
            "user"
        )

        if not user:

            return RedirectResponse(
                "/login"
            )

        return await call_next(
            request
        )

# =========================
# middleware
# =========================

# ⚠️ Auth 먼저 등록
app.add_middleware(
    AuthMiddleware
)

# ⚠️ Session 나중 등록
app.add_middleware(
    SessionMiddleware,
    secret_key="your-secret-key"
)

# =========================
# static
# =========================

app.mount(
    "/static",
    StaticFiles(
        directory="app/static"
    ),
    name="static"
)

# =========================
# router
# =========================

app.include_router(scan.router)
app.include_router(upload.router)
app.include_router(auth.router)
app.include_router(dashboard.router)
app.include_router(admin.router)

# =========================
# DB create
# =========================

Base.metadata.create_all(
    bind=engine
)

# =========================
# 🔥 admin bootstrap
# =========================

db = SessionLocal()

admin_user = db.query(User).filter(
    User.username == "admin"
).first()

if not admin_user:

    admin = User(
        username="admin",
        password=pwd_context.hash(
            "1234"
        ),
        role="admin",
        must_change_password=False
    )

    db.add(admin)

    db.commit()

db.close()
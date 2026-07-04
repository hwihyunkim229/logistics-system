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
    item_master
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
    assistant
)
import time

app = FastAPI()

pwd_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto"
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

        return await call_next(request)

app.add_middleware(
    AuthMiddleware
)

app.add_middleware(
    SessionMiddleware,
    secret_key="your-secret-key"
)

app.mount(
    "/static",
    StaticFiles(
        directory="app/static"
    ),
    name="static"
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

Base.metadata.create_all(
    bind=engine
)

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
from fastapi import APIRouter, Request, Form, Depends
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.models.user import User
from fastapi.responses import JSONResponse
from passlib.context import CryptContext
from app.utils.logger import save_log

router = APIRouter()

templates = Jinja2Templates(
    directory="app/templates"
)

pwd_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto"
)

def get_db():
    db = SessionLocal()

    try:
        yield db

    finally:
        db.close()


# =========================
# 로그인 페이지
# =========================

@router.get("/login")
def login_page(request: Request):

    error = request.query_params.get("error")

    registered = request.query_params.get(
        "registered"
    )

    return templates.TemplateResponse(
        request=request,
        name="login.html",
        context={
            "error": error,
            "registered": registered
        }
    )


# =========================
# 로그인 처리
# =========================

@router.post("/login")
def login(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db)
):

    user = db.query(User).filter(
        User.username == username
    ).first()

    if not user:
        return JSONResponse({
            "success": False
        })

    if not pwd_context.verify(
        password,
        user.password
    ):
        return JSONResponse({
            "success": False
        })

    request.session["user"] = username

    request.session["role"] = user.role

    save_log(
        user=username,
        product="AUTH",
        action="LOGIN"
    )

    if user.must_change_password:

        return JSONResponse({
            "success": True,
            "force_change": True
        })

    return JSONResponse({
        "success": True,
        "force_change": False
    })

# =========================
# 로그아웃
# =========================

@router.get("/logout")
def logout(request: Request):

    username = request.session.get(
        "user",
        "unknown"
    )

    save_log(
        user=username,
        product="AUTH",
        action="LOGOUT"
    )

    request.session.clear()

    return RedirectResponse(
        "/login",
        status_code=302
    )

# =========================
# 회원가입 비활성화
# =========================

@router.get("/register")
def register_page():

    return RedirectResponse("/login")


@router.post("/register")
def register():

    return RedirectResponse("/login")


# =========================
# 비밀번호 변경 페이지
# =========================

@router.get("/change-password")
def change_password_page(request: Request):

    return templates.TemplateResponse(
        request=request,
        name="change_password.html",
        context={
            "error": None
        }
    )


# =========================
# 비밀번호 변경 처리
# =========================

@router.post("/change-password")
def change_password(
    request: Request,
    current_password: str = Form(...),
    new_password: str = Form(...),
    confirm_password: str = Form(...),
    db: Session = Depends(get_db)
):

    username = request.session.get("user")

    user = db.query(User).filter(
        User.username == username
    ).first()

    if not user:

        return RedirectResponse("/login")


    # 현재 비밀번호 검증
    if not pwd_context.verify(
        current_password,
        user.password
    ):

        return templates.TemplateResponse(
            request=request,
            name="change_password.html",
            context={
                "error": "현재 비밀번호가 일치하지 않습니다."
            }
        )


    # 새 비밀번호 확인
    if new_password != confirm_password:

        return templates.TemplateResponse(
            request=request,
            name="change_password.html",
            context={
                "error": "새 비밀번호가 일치하지 않습니다."
            }
        )


    # 비밀번호 암호화 저장
    user.password = pwd_context.hash(
        new_password
    )

    user.must_change_password = False

    save_log(
        user=username,
        product="AUTH",
        action="CHANGE_PASSWORD"
    )

    db.commit()

    return RedirectResponse(
        "/search",
        status_code=303
    )
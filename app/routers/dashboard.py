from fastapi import APIRouter, Request
from fastapi.templating import Jinja2Templates
from sqlalchemy import func
from datetime import date, timedelta, datetime
from fastapi.responses import RedirectResponse
from app.database import SessionLocal
from app.models.outbound import Outbound
from app.models.inbound import Inbound
from app.models.movement import Movement
from sqlalchemy import or_
from zoneinfo import ZoneInfo

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")

SERVICES = [
    "cart_bp_pro",
    "cart_bp",
    "cart_on",
    "hanbang",
    "cart_platform",
    "cart_ring",
    "cart_o2"
]

SERVICE_NAMES = {
    "cart_bp_pro": "CART BP pro",
    "cart_bp": "CART BP",
    "cart_on": "CART ON",
    "hanbang": "한방 병원",
    "cart_platform" : "CART PLATFORM",
    "cart_ring" : "CART RING",
    "cart_o2" : "CART O2"
}

def get_group_mode(
    start_date,
    end_date
):

    days = (
        end_date - start_date
    ).days

    if days <= 7:
        return "day"

    elif days <= 90:
        return "week"

    else:
        return "month"

@router.get("/dashboard")
def dashboard_root():
    return RedirectResponse("/dashboard/overview")

@router.get("/dashboard/overview")
def dashboard_overview(
    request: Request,
    start: str = None,
    end: str = None
):

    db = SessionLocal()

    today = datetime.now(
        ZoneInfo("Asia/Seoul")
    ).date()

    if not start:
        start_date = today - timedelta(days=6)
    else:
        start_date = datetime.strptime(
            start,
            "%Y-%m-%d"
        ).date()

    if not end:
        end_date = today
    else:
        end_date = datetime.strptime(
            end,
            "%Y-%m-%d"
        ).date()

    start_datetime = datetime.combine(
        start_date,
        datetime.min.time()
    )

    end_datetime = datetime.combine(
        end_date,
        datetime.max.time()
    )

    # =========================
    # KPI
    # =========================

    # 🔥 전체 누적 (기간 영향 X)

    total_out = db.query(Outbound).count()

    total_in = db.query(Inbound).count()


    # 🔥 선택 기간 기준

    period_out = db.query(Outbound).filter(
        Outbound.created_at >= start_datetime,
        Outbound.created_at <= end_datetime
    ).count()

    period_in = db.query(Inbound).filter(
        Inbound.created_at >= start_datetime,
        Inbound.created_at <= end_datetime
    ).count()


    # 🔥 기간 내 미입력

    missing = db.query(Outbound).filter(
        Outbound.created_at >= start_datetime,
        Outbound.created_at <= end_datetime,
        (
            (Outbound.category == None) |
            (Outbound.client == None)
        )
    ).count()

    # =========================
    # TREND CHART
    # =========================

    trend_labels = []
    trend_out = []
    trend_in = []

    group_mode = get_group_mode(
        start_date,
        end_date
    )

    # =========================
    # DAY
    # =========================

    if group_mode == "day":

        current = start_date

        while current <= end_date:

            next_day = current + timedelta(days=1)

            out_count = db.query(Outbound).filter(
                Outbound.created_at >= current,
                Outbound.created_at < next_day
            ).count()

            in_count = db.query(Inbound).filter(
                Inbound.created_at >= current,
                Inbound.created_at < next_day
            ).count()

            trend_labels.append(
                current.strftime("%m-%d")
            )

            trend_out.append(out_count)
            trend_in.append(in_count)

            current = next_day

    # =========================
    # WEEK
    # =========================

    elif group_mode == "week":

        current = start_date

        while current <= end_date:

            next_week = current + timedelta(days=7)

            out_count = db.query(Outbound).filter(
                Outbound.created_at >= current,
                Outbound.created_at < next_week
            ).count()

            in_count = db.query(Inbound).filter(
                Inbound.created_at >= current,
                Inbound.created_at < next_week
            ).count()

            trend_labels.append(
                f"{current.strftime('%m-%d')}"
            )

            trend_out.append(out_count)
            trend_in.append(in_count)

            current = next_week

    # =========================
    # MONTH
    # =========================

    else:

        current = date(
            start_date.year,
            start_date.month,
            1
        )

        while current <= end_date:

            if current.month == 12:

                next_month = date(
                    current.year + 1,
                    1,
                    1
                )

            else:

                next_month = date(
                    current.year,
                    current.month + 1,
                    1
                )

            out_count = db.query(Outbound).filter(
                Outbound.created_at >= current,
                Outbound.created_at < next_month
            ).count()

            in_count = db.query(Inbound).filter(
                Inbound.created_at >= current,
                Inbound.created_at < next_month
            ).count()

            trend_labels.append(
                current.strftime("%Y-%m")
            )

            trend_out.append(out_count)
            trend_in.append(in_count)

            current = next_month

    # =========================
    # SIZE CHART
    # =========================

    size_labels = ["7", "8", "9", "10", "11", "12", "13"]

    size_in = []
    size_out = []

    for s in ["7", "8", "9", "10", "11", "12", "13"]:

        in_count = db.query(Inbound).filter(
            Inbound.size == s,
            Inbound.created_at >= start_datetime,
            Inbound.created_at <= end_datetime
        ).count()

        out_count = db.query(Outbound).filter(
            Outbound.size == s,
            Outbound.created_at >= start_datetime,
            Outbound.created_at <= end_datetime
        ).count()

        size_in.append(in_count)
        size_out.append(out_count)

    db.close()

    return templates.TemplateResponse(
        request=request,
        name="dashboard/overview.html",
        context={

            "total_out": total_out,
            "total_in": total_in,

            "period_out": period_out,
            "period_in": period_in,

            "missing": missing,

            "trend_labels": trend_labels,
            "trend_out": trend_out,
            "trend_in": trend_in,

            "size_labels": size_labels,
            "size_in": size_in,
            "size_out": size_out,

            "group_mode": group_mode,

            "start": start_date.strftime("%Y-%m-%d"),
            "end": end_date.strftime("%Y-%m-%d")
        }
    )

@router.get("/dashboard/trend")
def dashboard_trend(
    request: Request,
    start: str = None,
    end: str = None
):

    db = SessionLocal()

    charts = []

    today = datetime.now(
        ZoneInfo("Asia/Seoul")
    ).date()

    # =========================
    # 날짜 처리
    # =========================

    if not start:

        start_date = (
            today - timedelta(days=6)
        )

    else:

        start_date = datetime.strptime(
            start,
            "%Y-%m-%d"
        ).date()

    if not end:

        end_date = today

    else:

        end_date = datetime.strptime(
            end,
            "%Y-%m-%d"
        ).date()

    group_mode = get_group_mode(
        start_date,
        end_date
    )

    # KPI
    start_datetime = datetime.combine(
        start_date,
        datetime.min.time()
    )

    end_datetime = datetime.combine(
        end_date,
        datetime.max.time()
    )

    total_out = db.query(Outbound).filter(
        Outbound.created_at >= start_datetime,
        Outbound.created_at <= end_datetime
    ).count()

    total_in = db.query(Outbound).filter(
        Inbound.created_at >= start_datetime,
        Inbound.created_at <= end_datetime
    ).count()

    for service in SERVICES:

        labels = []
        out_counts = []
        in_counts = []

        if group_mode == "day":

            current = start_date

            while current <= end_date:

                next_day = (
                    current + timedelta(days=1)
                )

                current_start = datetime.combine(
                    current,
                    datetime.min.time()
                )

                next_day_start = datetime.combine(
                    next_day,
                    datetime.min.time()
                )

                labels.append(
                    current.strftime("%m-%d")
                )

                out_count = db.query(Outbound).filter(
                    Outbound.product == service,
                    Outbound.created_at >= current_start,
                    Outbound.created_at < next_day_start
                ).count()

                in_count = db.query(Inbound).filter(
                    Inbound.product == service,
                    Inbound.created_at >= current_start,
                    Inbound.created_at < next_day_start
                ).count()

                out_counts.append(out_count)

                in_counts.append(in_count)

                current = next_day

        # =========================
        # WEEK
        # =========================

        elif group_mode == "week":

            current = start_date

            while current <= end_date:

                next_week = (
                    current + timedelta(days=7)
                )

                current_start = datetime.combine(
                    current,
                    datetime.min.time()
                )

                next_week_start = datetime.combine(
                    next_week,
                    datetime.min.time()
                )

                labels.append(
                    current.strftime("%m-%d")
                )

                out_count = db.query(Outbound).filter(
                    Outbound.product == service,
                    Outbound.created_at >= current_start,
                    Outbound.created_at < next_week_start
                ).count()

                in_count = db.query(Inbound).filter(
                    Inbound.product == service,
                    Inbound.created_at >= current_start,
                    Inbound.created_at < next_week_start
                ).count()

                out_counts.append(out_count)

                in_counts.append(in_count)

                current = next_week

        # =========================
        # MONTH
        # =========================

        else:
            current = date(
                start_date.year,
                start_date.month,
                1
            )

            while current <= end_date:

                if current.month == 12:

                    next_month = date(
                        current.year + 1,
                        1,
                        1
                    )

                else:

                    next_month = date(
                        current.year,
                        current.month + 1,
                        1
                    )

                month_start = datetime.combine(
                    current,
                    datetime.min.time()
                )

                next_month_start = datetime.combine(
                    next_month,
                    datetime.min.time()
                )

                labels.append(
                    current.strftime("%Y-%m")
                )

                out_count = db.query(Outbound).filter(
                    Outbound.product == service,
                    Outbound.created_at >= month_start,
                    Outbound.created_at < next_month_start
                ).count()

                in_count = db.query(Inbound).filter(
                    Inbound.product == service,
                    Inbound.created_at >= month_start,
                    Inbound.created_at < next_month_start
                ).count()

                out_counts.append(out_count)

                in_counts.append(in_count)

                current = next_month

        charts.append({

            "service": service,

            "display_name":
                SERVICE_NAMES[service],

            "labels": labels,

            "out_counts": out_counts,

            "in_counts": in_counts,

            "total_out": sum(out_counts),

            "total_in": sum(in_counts)
        })

    db.close()

    return templates.TemplateResponse(
        request=request,
        name="dashboard/trend.html",
        context={
            "charts": charts,
            "total_out": total_out,
            "total_in": total_in,
            "start": start_date.strftime("%Y-%m-%d"),
            "end": end_date.strftime("%Y-%m-%d"),
            "group_mode": group_mode
        }
    )

@router.get("/dashboard/size")
def dashboard_size(request: Request):

    db = SessionLocal()

    charts = []

    for service in SERVICES:

        labels = ["7", "8", "9", "10", "11", "12", "13"]

        in_counts = []
        out_counts = []

        for s in ["7","8","9","10","11","12","13"]:

            in_count = db.query(Inbound).filter(
                Inbound.product == service,
                Inbound.size == s
            ).count()

            out_count = db.query(Outbound).filter(
                Outbound.product == service,
                Outbound.size == s
            ).count()

            in_counts.append(in_count)
            out_counts.append(out_count)

        # 🔥 TOP 사이즈 계산
        if max(out_counts) == 0:
            top_out_size = "-"
        else:
            top_out_index = out_counts.index(max(out_counts))
            top_out_size = labels[top_out_index]

        # 🔥 입고 TOP
        if max(in_counts) == 0:
            top_in_size = "-"
        else:
            top_in_index = in_counts.index(max(in_counts))
            top_in_size = labels[top_in_index]

        charts.append({
            "service": service,

            "display_name": SERVICE_NAMES[service],

            "labels": labels,

            "in_counts": in_counts,
            "out_counts": out_counts,

            "top_out_size": top_out_size,
            "top_in_size": top_in_size
        })

    db.close()

    return templates.TemplateResponse(
        request=request,
        name="dashboard/size.html",
        context={
            "charts": charts
        }
    )

@router.get("/dashboard/activity")
def dashboard_activity(
    request: Request,
    start: str = None,
    end: str = None
):

    db = SessionLocal()

    # =========================
    # 날짜 범위 처리
    # =========================

    today = datetime.now(
        ZoneInfo("Asia/Seoul")
    ).date()

    if not start:
        start_date = today
    else:
        start_date = datetime.strptime(
            start,
            "%Y-%m-%d"
        ).date()

    if not end:
        end_date = today
    else:
        end_date = datetime.strptime(
            end,
            "%Y-%m-%d"
        ).date()

    start_datetime = datetime.combine(
        start_date,
        datetime.min.time()
    )

    end_datetime = datetime.combine(
        end_date,
        datetime.max.time()
    )

    # =========================
    # 최근 로그
    # =========================

    records = db.query(Movement).filter(
        Movement.created_at >= start_datetime,
        Movement.created_at <= end_datetime
    ).order_by(
        Movement.created_at.asc()
    ).all()

    # =========================
    # KPI
    # =========================

    total_logs = db.query(Movement).filter(
        Movement.created_at >= start_datetime,
        Movement.created_at <= end_datetime
    ).count()

    today_in = db.query(Movement).filter(
        Movement.created_at >= start_datetime,
        Movement.created_at <= end_datetime,
        Movement.type == "IN"
    ).count()

    today_out = db.query(Movement).filter(
        Movement.created_at >= start_datetime,
        Movement.created_at <= end_datetime,
        Movement.type == "OUT"
    ).count()

    missing_client = db.query(Movement).filter(
        Movement.created_at >= start_datetime,
        Movement.created_at <= end_datetime,
        Movement.type == "OUT",
        or_(
            Movement.client == None,
            Movement.client == ""
        )
    ).count()

    recent_hour = db.query(Movement).filter(
        Movement.created_at >= (
            datetime.now(
                ZoneInfo("Asia/Seoul")
            ) - timedelta(hours=1)
        )
    ).count()

    # =========================
    # 서비스별 처리량
    # =========================

    service_stats = []

    for service in SERVICES:

        count = db.query(Movement).filter(
            Movement.product == service,
            Movement.created_at >= start_datetime,
            Movement.created_at <= end_datetime
        ).count()

        service_stats.append({
            "name": SERVICE_NAMES[service],
            "count": count
        })

    # =========================
    # 활동량 차트
    # product별 데이터 분리
    # =========================

    labels = []

    activity_cart_bp_pro = []
    activity_cart_bp = []
    activity_cart_on = []
    activity_hanbang = []
    activity_cart_platform = []
    activity_cart_ring = []
    activity_cart_o2 = []

    current = start_date

    while current <= end_date:

        next_day = current + timedelta(days=1)

        current_start = datetime.combine(
            current,
            datetime.min.time()
        )

        next_day_start = datetime.combine(
            next_day,
            datetime.min.time()
        )

        labels.append(current.strftime("%m-%d"))

        # CART BP Pro
        cart_bp_pro_count = db.query(Movement).filter(
            Movement.product == "cart_bp_pro",
            Movement.created_at >= current_start,
            Movement.created_at < next_day_start
        ).count()

        activity_cart_bp_pro.append(
            cart_bp_pro_count
        )

        # CART BP
        cart_bp_count = db.query(Movement).filter(
            Movement.product == "cart_bp",
            Movement.created_at >= current_start,
            Movement.created_at < next_day_start
        ).count()

        activity_cart_bp.append(
            cart_bp_count
        )

        # CART ON
        cart_on_count = db.query(Movement).filter(
            Movement.product == "cart_on",
            Movement.created_at >= current_start,
            Movement.created_at < next_day_start
        ).count()

        activity_cart_on.append(
            cart_on_count
        )

        # 한방 병원
        hanbang_count = db.query(Movement).filter(
            Movement.product == "hanbang",
            Movement.created_at >= current_start,
            Movement.created_at < next_day_start
        ).count()

        activity_hanbang.append(
            hanbang_count
        )

        cart_platform_count = db.query(Movement).filter(
            Movement.product == "cart_platform",
            Movement.created_at >= current_start,
            Movement.created_at < next_day_start
        ).count()

        activity_cart_platform.append(
            cart_platform_count
        )

        cart_ring_count = db.query(Movement).filter(
            Movement.product == "cart_ring",
            Movement.created_at >= current_start,
            Movement.created_at < next_day_start
        ).count()

        activity_cart_ring.append(
            cart_ring_count
        )

        cart_o2_count = db.query(Movement).filter(
            Movement.product == "cart_o2",
            Movement.created_at >= current_start,
            Movement.created_at < next_day_start
        ).count()

        activity_cart_o2.append(
            cart_o2_count
        )

        current = next_day

    db.close()

    return templates.TemplateResponse(
        request=request,
        name="dashboard/activity.html",
        context={
            "records": records,
            "total_logs": total_logs,
            "today_in": today_in,
            "today_out": today_out,
            "missing_client": missing_client,
            "recent_hour": recent_hour,
            "service_stats": service_stats,
            "activity_labels": labels,
            "activity_cart_bp_pro": activity_cart_bp_pro,
            "activity_cart_bp": activity_cart_bp,
            "activity_cart_on": activity_cart_on,
            "activity_hanbang": activity_hanbang,
            "activity_cart_platform" : activity_cart_platform,
            "activity_cart_ring" : activity_cart_ring,
            "activity_cart_o2" : activity_cart_o2,
            "start": start_date.strftime("%Y-%m-%d"),
            "end": end_date.strftime("%Y-%m-%d"),
            "SERVICES": SERVICES,
            "SERVICE_NAMES": SERVICE_NAMES
        }
    )
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

def get_earliest_date(db, today):
    """가장 오래된 입/출고 기록 날짜 - 기간 미지정 시 누적(전체) 보기의
    시작일로 쓴다. 기록이 없으면 오늘로 대체한다.
    """

    earliest_out = db.query(
        func.min(Outbound.created_at)
    ).scalar()

    earliest_in = db.query(
        func.min(Inbound.created_at)
    ).scalar()

    candidates = [
        d.date() for d in (earliest_out, earliest_in) if d
    ]

    return min(candidates) if candidates else today

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

    # 기간을 지정하지 않으면(첫 진입) 최초 기록일부터 오늘까지 전체
    # 누적을 기본으로 보여주고, 기간을 선택하면 그 기간만 반영한다.
    is_cumulative = not start and not end

    if not start:
        start_date = get_earliest_date(db, today)
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

    total_out = db.query(Outbound).count()

    total_in = db.query(Inbound).count()

    period_out = db.query(Outbound).filter(
        Outbound.created_at >= start_datetime,
        Outbound.created_at <= end_datetime
    ).count()

    period_in = db.query(Inbound).filter(
        Inbound.created_at >= start_datetime,
        Inbound.created_at <= end_datetime
    ).count()

    missing = db.query(Outbound).filter(
        Outbound.created_at >= start_datetime,
        Outbound.created_at <= end_datetime,
        (
            (Outbound.category == None) |
            (Outbound.client == None)
        )
    ).count()

    trend_labels = []
    trend_out = []
    trend_in = []

    group_mode = get_group_mode(
        start_date,
        end_date
    )

    # 구간(day/week/month)마다 Outbound/Inbound를 따로 조회하던 것을,
    # 전체 기간 생성일시를 한 번만 가져와 Python에서 구간별로 나누는
    # 방식으로 바꿨다 - 결과(구간별 건수)는 동일하고 DB 왕복만 줄어든다.
    out_all_dates = [
        row[0] for row in db.query(Outbound.created_at).filter(
            Outbound.created_at >= start_datetime,
            Outbound.created_at <= end_datetime
        ).all()
    ]

    in_all_dates = [
        row[0] for row in db.query(Inbound.created_at).filter(
            Inbound.created_at >= start_datetime,
            Inbound.created_at <= end_datetime
        ).all()
    ]

    def _count_in_range(dates, range_start, range_end):
        return sum(
            1 for d in dates
            if range_start <= _naive(d) < range_end
        )

    def _naive(d):
        return d.replace(tzinfo=None) if d.tzinfo else d

    if group_mode == "day":

        current = start_date

        while current <= end_date:

            next_day = current + timedelta(days=1)

            bucket_start = datetime.combine(current, datetime.min.time())
            bucket_end = datetime.combine(next_day, datetime.min.time())

            out_count = _count_in_range(out_all_dates, bucket_start, bucket_end)
            in_count = _count_in_range(in_all_dates, bucket_start, bucket_end)

            trend_labels.append(
                current.strftime("%m-%d")
            )

            trend_out.append(out_count)
            trend_in.append(in_count)

            current = next_day

    elif group_mode == "week":

        current = start_date

        while current <= end_date:

            next_week = current + timedelta(days=7)

            bucket_start = datetime.combine(current, datetime.min.time())
            bucket_end = datetime.combine(next_week, datetime.min.time())

            out_count = _count_in_range(out_all_dates, bucket_start, bucket_end)
            in_count = _count_in_range(in_all_dates, bucket_start, bucket_end)

            trend_labels.append(
                f"{current.strftime('%m-%d')}"
            )

            trend_out.append(out_count)
            trend_in.append(in_count)

            current = next_week

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

            bucket_start = datetime.combine(current, datetime.min.time())
            bucket_end = datetime.combine(next_month, datetime.min.time())

            out_count = _count_in_range(out_all_dates, bucket_start, bucket_end)
            in_count = _count_in_range(in_all_dates, bucket_start, bucket_end)

            trend_labels.append(
                current.strftime("%Y-%m")
            )

            trend_out.append(out_count)
            trend_in.append(in_count)

            current = next_month

    size_labels = ["7", "8", "9", "10", "11", "12", "13"]

    # 사이즈별 반복 조회(사이즈 수 x 2쿼리) 대신 GROUP BY 한 번으로 집계.
    in_size_counts = dict(
        db.query(Inbound.size, func.count(Inbound.id))
        .filter(
            Inbound.created_at >= start_datetime,
            Inbound.created_at <= end_datetime
        )
        .group_by(Inbound.size)
        .all()
    )

    out_size_counts = dict(
        db.query(Outbound.size, func.count(Outbound.id))
        .filter(
            Outbound.created_at >= start_datetime,
            Outbound.created_at <= end_datetime
        )
        .group_by(Outbound.size)
        .all()
    )

    size_in = [in_size_counts.get(s, 0) for s in size_labels]
    size_out = [out_size_counts.get(s, 0) for s in size_labels]

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

            "is_cumulative": is_cumulative,

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

    # 기간을 지정하지 않으면(첫 진입) 최초 기록일부터 오늘까지 전체
    # 누적을 기본으로 보여주고, 기간을 선택하면 그 기간만 반영한다.
    is_cumulative = not start and not end

    if not start:

        start_date = get_earliest_date(db, today)

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

    total_in = db.query(Inbound).filter(
        Inbound.created_at >= start_datetime,
        Inbound.created_at <= end_datetime
    ).count()

    # 서비스(7개) x 구간마다 따로 조회하던 것을, (product, created_at)만
    # 한 번씩 가져와 Python에서 서비스/구간별로 나누는 방식으로 대체 -
    # 구간별 건수 결과는 동일하고 DB 왕복만 크게 줄어든다.
    out_rows = db.query(
        Outbound.product, Outbound.created_at
    ).filter(
        Outbound.created_at >= start_datetime,
        Outbound.created_at <= end_datetime
    ).all()

    in_rows = db.query(
        Inbound.product, Inbound.created_at
    ).filter(
        Inbound.created_at >= start_datetime,
        Inbound.created_at <= end_datetime
    ).all()

    def _naive(d):
        return d.replace(tzinfo=None) if d.tzinfo else d

    def _count_in_range(rows, service, range_start, range_end):
        return sum(
            1 for product, created_at in rows
            if product == service and range_start <= _naive(created_at) < range_end
        )

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

                out_counts.append(
                    _count_in_range(out_rows, service, current_start, next_day_start)
                )

                in_counts.append(
                    _count_in_range(in_rows, service, current_start, next_day_start)
                )

                current = next_day

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

                out_counts.append(
                    _count_in_range(out_rows, service, current_start, next_week_start)
                )

                in_counts.append(
                    _count_in_range(in_rows, service, current_start, next_week_start)
                )

                current = next_week

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

                out_counts.append(
                    _count_in_range(out_rows, service, month_start, next_month_start)
                )

                in_counts.append(
                    _count_in_range(in_rows, service, month_start, next_month_start)
                )

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
            "group_mode": group_mode,
            "is_cumulative": is_cumulative
        }
    )

@router.get("/dashboard/size")
def dashboard_size(request: Request):

    db = SessionLocal()

    charts = []

    # 서비스 x 사이즈(7x7)만큼 반복 조회하던 것을, (product, size)별
    # GROUP BY 집계 2번(입고/출고)으로 대체 - 결과는 동일.
    in_size_totals = {
        (product, size): count
        for product, size, count in db.query(
            Inbound.product, Inbound.size, func.count(Inbound.id)
        ).group_by(Inbound.product, Inbound.size).all()
    }

    out_size_totals = {
        (product, size): count
        for product, size, count in db.query(
            Outbound.product, Outbound.size, func.count(Outbound.id)
        ).group_by(Outbound.product, Outbound.size).all()
    }

    for service in SERVICES:

        labels = ["7", "8", "9", "10", "11", "12", "13"]

        in_counts = [
            in_size_totals.get((service, s), 0) for s in labels
        ]
        out_counts = [
            out_size_totals.get((service, s), 0) for s in labels
        ]

        if max(out_counts) == 0:
            top_out_size = "-"
        else:
            top_out_index = out_counts.index(max(out_counts))
            top_out_size = labels[top_out_index]

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

    records = db.query(Movement).filter(
        Movement.created_at >= start_datetime,
        Movement.created_at <= end_datetime
    ).order_by(
        Movement.created_at.asc()
    ).all()

    # total_logs는 records와 완전히 동일한 조건이라 다시 조회할 필요가
    # 없다 - 이미 불러온 records 길이를 그대로 쓴다.
    total_logs = len(records)

    # today_in/today_out/missing_client/service_stats/일별 서비스별
    # 집계가 전부 "같은 기간의 Movement"를 서로 다른 각도로 세던 것이라,
    # (type, product, client, created_at)만 한 번 가져와 Python에서
    # 전부 계산한다 - 결과는 기존과 동일하고 반복 조회만 없앤다.
    period_rows = db.query(
        Movement.type, Movement.product, Movement.client, Movement.created_at
    ).filter(
        Movement.created_at >= start_datetime,
        Movement.created_at <= end_datetime
    ).all()

    today_in = sum(1 for t, p, c, d in period_rows if t == "IN")

    today_out = sum(1 for t, p, c, d in period_rows if t == "OUT")

    missing_client = sum(
        1 for t, p, c, d in period_rows
        if t == "OUT" and (c is None or c == "")
    )

    recent_hour = db.query(Movement).filter(
        Movement.created_at >= (
            datetime.now(
                ZoneInfo("Asia/Seoul")
            ) - timedelta(hours=1)
        )
    ).count()

    service_stats = [
        {
            "name": SERVICE_NAMES[service],
            "count": sum(1 for t, p, c, d in period_rows if p == service)
        }
        for service in SERVICES
    ]

    def _naive(d):
        return d.replace(tzinfo=None) if d.tzinfo else d

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

        day_rows = [
            (t, p) for t, p, c, d in period_rows
            if current_start <= _naive(d) < next_day_start
        ]

        activity_cart_bp_pro.append(
            sum(1 for t, p in day_rows if p == "cart_bp_pro")
        )

        activity_cart_bp.append(
            sum(1 for t, p in day_rows if p == "cart_bp")
        )

        activity_cart_on.append(
            sum(1 for t, p in day_rows if p == "cart_on")
        )

        activity_hanbang.append(
            sum(1 for t, p in day_rows if p == "hanbang")
        )

        activity_cart_platform.append(
            sum(1 for t, p in day_rows if p == "cart_platform")
        )

        activity_cart_ring.append(
            sum(1 for t, p in day_rows if p == "cart_ring")
        )

        activity_cart_o2.append(
            sum(1 for t, p in day_rows if p == "cart_o2")
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
from app.services.product_categories import dashboard_product_names
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
    service_names = dashboard_product_names(db)
    services = list(service_names)

    charts = []

    today = datetime.now(
        ZoneInfo("Asia/Seoul")
    ).date()

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

    for service in services:

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
                service_names[service],
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
    service_names = dashboard_product_names(db)
    services = list(service_names)

    charts = []

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

    for service in services:

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

            "display_name": service_names[service],

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
    service_names = dashboard_product_names(db)
    services = list(service_names)

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

    total_logs = len(records)

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
            "name": service_names[service],
            "count": sum(1 for t, p, c, d in period_rows if p == service)
        }
        for service in services
    ]

    def _naive(d):
        return d.replace(tzinfo=None) if d.tzinfo else d

    labels = []

    activity_counts = {service: [] for service in services}

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

        for service in services:
            activity_counts[service].append(
                sum(1 for _, product in day_rows if product == service)
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
            "activity_series": [
                {"code": service, "name": service_names[service], "counts": activity_counts[service]}
                for service in services
            ],
            "start": start_date.strftime("%Y-%m-%d"),
            "end": end_date.strftime("%Y-%m-%d"),
            "SERVICES": services,
            "SERVICE_NAMES": service_names
        }
    )
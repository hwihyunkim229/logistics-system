from collections import Counter, defaultdict
from datetime import date, datetime, timedelta
from types import SimpleNamespace
from urllib.parse import quote
from zoneinfo import ZoneInfo
from app.routers.mrp import calculate_mrp
from sqlalchemy import distinct, func, or_

from app.assistant.registry import tool
from app.models.activity_log import ActivityLog
from app.models.bom import BOM
from app.models.inbound import Inbound
from app.models.inventory import Inventory
from app.models.inventory_movement import InventoryMovement
from app.models.item import Item
from app.models.item_master import ItemMaster
from app.models.item_master_history import ItemMasterHistory
from app.models.material_master import MaterialMaster
from app.models.material_note import MaterialNote
from app.models.movement import Movement
from app.models.outbound import Outbound
from app.models.production_plan import ProductionPlan
from app.models.stock import Stock
from app.models.stock_movement import StockMovement
from app.models.user import User


MAX_ROWS = 15

SERVICE_NAMES = {
    "cart_bp_pro": "CART BP pro",
    "cart_bp": "CART BP",
    "cart_on": "CART ON",
    "hanbang": "한방 병원",
    "cart_platform": "CART PLATFORM",
    "cart_ring": "CART RING",
    "cart_o2": "CART O2",
}


def _keyword(value):
    return (value or "").strip()


def _like(value):
    return f"%{value.lower()}%"


def _fmt_dt(value):
    if not value:
        return ""
    return value.strftime("%Y-%m-%d %H:%M")


def _fmt_date(value):
    if not value:
        return ""
    return value.strftime("%Y-%m-%d")


def _safe_user(row):
    return {
        "username": row.username,
        "role": row.role,
        "must_change_password": bool(row.must_change_password),
    }


def _period_range(period):
    today = datetime.now(ZoneInfo("Asia/Seoul")).date()

    if period == "today":
        start = today
        end = today + timedelta(days=1)
    elif period == "yesterday":
        start = today - timedelta(days=1)
        end = today
    elif period == "this_week":
        start = today - timedelta(days=today.weekday())
        end = today + timedelta(days=1)
    elif period == "this_month":
        start = date(today.year, today.month, 1)
        end = today + timedelta(days=1)
    else:
        return None, None

    return (
        datetime.combine(start, datetime.min.time()),
        datetime.combine(end, datetime.min.time()),
    )


def _apply_flow_filters(query, model, product="", period="all", keyword=""):
    if product:
        query = query.filter(model.product == product)

    start, end = _period_range(period)

    if start and end:
        query = query.filter(
            model.created_at >= start,
            model.created_at < end,
        )

    keyword = _keyword(keyword)

    if keyword:
        pattern = _like(keyword)
        query = query.filter(
            or_(
                func.lower(model.serial).like(pattern),
                func.lower(model.product).like(pattern),
                func.lower(model.size).like(pattern),
                func.lower(model.category).like(pattern),
                func.lower(model.client).like(pattern),
                func.lower(model.note).like(pattern),
            )
        )

    return query


def _flow_rows(query, model):
    return [
        {
            "created_at": _fmt_dt(row.created_at),
            "serial": row.serial,
            "product": row.product,
            "product_name": SERVICE_NAMES.get(row.product, row.product),
            "size": row.size,
            "category": row.category,
            "client": row.client,
        }
        for row in query.order_by(model.created_at.desc()).limit(5).all()
    ]


def _encoded(value):
    return quote(value or "", safe="")


def _contains_filter(model, fields, value):
    pattern = _like(value)
    return or_(*[
        func.lower(getattr(model, field)).like(pattern)
        for field in fields
    ])


def _find_page_matches(db, target):
    """Find every module that has a row matching `target`, not just the
    first one. An item code is not unique across modules (a component
    can appear in Stock, BOM, MaterialMaster, ItemMaster all at once),
    so stopping at the first hit silently sends everyone to whichever
    table happens to be checked first (Stock) even when that is not
    what they meant.
    """

    target = _keyword(target)

    if not target:
        return []

    matches = []

    stock = (
        db.query(Stock)
        .filter(_contains_filter(Stock, ["item_code", "item_name", "category"], target))
        .first()
    )

    if stock:
        matches.append({
            "page": "stock",
            "url": (
                f"/stock?category={_encoded(stock.category)}"
                f"&keyword={_encoded(target)}&highlight={_encoded(target)}"
            ),
            "label": "가계상 재고",
        })

    inventory = (
        db.query(Inventory)
        .filter(_contains_filter(Inventory, ["item_code", "item_name", "warehouse_type"], target))
        .first()
    )

    if inventory:
        matches.append({
            "page": "inventory",
            "url": f"/inventory?highlight={_encoded(target)}",
            "label": "수불 재고",
        })

    bom = (
        db.query(BOM)
        .filter(_contains_filter(BOM, ["product_name", "component_code", "component_name"], target))
        .first()
    )

    if bom:
        matches.append({
            "page": "bom",
            "url": f"/mrp/bom?highlight={_encoded(target)}",
            "label": "BOM",
        })

    material = (
        db.query(MaterialMaster)
        .filter(_contains_filter(MaterialMaster, ["item_code", "item_name", "supplier"], target))
        .first()
    )

    if material:
        matches.append({
            "page": "material_master",
            "url": f"/mrp/material-master?highlight={_encoded(target)}",
            "label": "자재 기준정보",
        })

    item = (
        db.query(ItemMaster)
        .filter(_contains_filter(ItemMaster, ["item_code", "item_name", "rev"], target))
        .first()
    )

    if item:
        matches.append({
            "page": "item_master",
            "url": f"/stock/item-master/manage?highlight={_encoded(target)}",
            "label": "품목 기준정보",
        })

    inbound = (
        db.query(Inbound)
        .filter(_contains_filter(Inbound, ["serial", "product", "size", "category", "client"], target))
        .first()
    )

    if inbound:
        matches.append({
            "page": "inbound",
            "url": f"/search?highlight={_encoded(target)}",
            "label": "제품 물류 입고",
        })

    outbound = (
        db.query(Outbound)
        .filter(_contains_filter(Outbound, ["serial", "product", "size", "category", "client"], target))
        .first()
    )

    if outbound:
        matches.append({
            "page": "outbound",
            "url": f"/search?highlight={_encoded(target)}",
            "label": "제품 물류 출고",
        })

    return matches


@tool("general.chat")
def general_chat(db, question: str):
    return {
        "status": "general",
        "question": question,
        "message": (
            "Logistics 시스템의 재고, 입출고, BOM, 생산계획, MRP, "
            "품목/자재 기준정보, 사용자/활동 로그에 대해 질문할 수 있습니다."
        )
    }


@tool("security.block")
def security_block(db, question: str = ""):
    return {
        "status": "blocked",
        "message": (
            "비밀번호와 패스워드는 보안상 조회하거나 제공할 수 없습니다. "
            "필요하면 관리자 화면에서 비밀번호 초기화 또는 변경 절차를 사용해 주세요."
        )
    }


@tool("knowledge.answer")
def knowledge_answer(db, question: str = "", topic: str = ""):
    return {
        "status": "knowledge",
        "question": question,
        "topic": topic,
        "facts": {
            "가계상 재고": (
                "가계상 재고는 이 시스템의 Stock 테이블 기준 장부상 재고입니다. "
                "품목코드, 품목명, 등급(A/B/F), Rev, 구분(반제품/제품/원자재), 수량으로 관리됩니다."
            ),
            "수불 재고": (
                "수불 재고(구 계상 재고)는 창고구분(창고재고/제공재고/외주재고)별로 관리되는 재고입니다. "
                "창고재고만 구분(반제품/제품/원자재)과 등급(A/B/F)으로 다시 나뉘고, "
                "품목코드+창고구분+LOT+등급 조합으로 관리됩니다. "
                "LOT은 제품/반제품에만 있는 개념이며(원자재는 LOT이 없습니다), "
                "F25처럼 있는 그대로의 문자열로 취급됩니다. "
                "MRP 계산은 이 수불 재고를 사용합니다."
            ),
            "계상 재고": (
                "계상 재고는 수불 재고의 이전 명칭입니다. 창고구분(창고재고/제공재고/외주재고)별로 "
                "관리되는 재고이며, 창고재고만 구분(반제품/제품/원자재)과 등급(A/B/F)으로 다시 나뉘고, "
                "품목코드+창고구분+LOT+등급 조합으로 관리됩니다. MRP 계산은 이 재고를 사용합니다."
            ),
            "제품 물류": (
                "제품 물류는 시리얼 단위 입고/출고 흐름입니다. "
                "Inbound, Outbound, Movement 테이블을 기준으로 제품, 시리얼, 사이즈, 고객, 일시를 추적합니다."
            ),
            "MRP 결과": (
                "MRP 결과는 품목별 소요량, 가용재고, 부족수량, 권장발주수량, 발주 필요일을 계산해 보여주는 "
                "화면입니다. 부족수량이 0보다 크면 상태가 SHORT로 표시됩니다."
            ),
            "MRP": (
                "MRP는 생산계획과 BOM, 수불 재고, 자재 기준정보를 조합해 필요 수량, 부족 수량, "
                "발주 필요일, 권장 발주 수량을 계산하는 영역입니다."
            ),
            "BOM": (
                "BOM은 제품을 만들기 위해 필요한 구성품 목록입니다. "
                "제품명, 구성품 코드, 구성품명, 소요 수량으로 관리됩니다."
            ),
            "LOT": (
                "LOT은 수불 재고의 로트 표기이며 제품/반제품에만 있는 개념입니다(원자재는 LOT이 없습니다). "
                "F25, G23처럼 있는 그대로의 문자열로 취급되며 별도로 해석하거나 변환하지 않습니다."
            ),
            "창고재고": (
                "창고재고는 수불 재고 중 자사 창고 보관분입니다. "
                "구분(반제품/제품/원자재)과 등급(A/B/F)으로 나뉘고, LOT은 제품/반제품에만 있습니다."
            ),
            "제공재고": (
                "제공재고는 수불 재고 중 외부(고객/협력사)에 제공되어 보관 중인 재고입니다. "
                "창고재고와 달리 구분/등급 개념이 없습니다."
            ),
            "외주재고": (
                "외주재고는 수불 재고 중 외주 업체에 보내 가공 중인 재고입니다. "
                "창고재고와 달리 구분/등급 개념이 없습니다."
            ),
            "품목 관리": (
                "품목 관리(Item Master)는 품목코드, 품목명, Revision을 관리하는 기준정보입니다. "
                "SL-H-AS-00010처럼 표기되는 코드를 사용하며, 코드/명칭/Rev가 바뀌면 변경 이력이 남습니다."
            ),
            "자재 기준정보": (
                "자재 기준정보(Material Master)는 원자재별 공급사, MOQ(최소발주수량), Lead Time을 관리합니다. "
                "MRP가 발주 필요일과 권장 발주 수량을 계산할 때 이 정보를 사용합니다."
            ),
            "생산계획": (
                "생산계획(Production Plan)은 날짜별로 어떤 제품을 얼마나 생산할지 정한 계획입니다. "
                "MRP는 이 생산계획과 BOM을 곱해 자재 소요량을 계산합니다."
            ),
            "활동 로그": (
                "활동 로그는 로그인/등록/수정/삭제/업로드/다운로드 등 시스템에서 발생한 모든 작업 이력입니다. "
                "관리자만 조회할 수 있습니다."
            ),
            "계정 관리": (
                "계정 관리는 사용자 계정 생성/삭제/비밀번호 초기화를 처리하는 관리자 전용 화면입니다."
            ),
            "대시보드": (
                "대시보드는 각 모듈(제품 물류/수불 재고/가계상 재고/MRP)의 현재 상태를 요약해서 보여주는 화면입니다. "
                "누적 수량, 기간별 입출고, 부족 현황 등을 한눈에 볼 수 있습니다."
            ),
            "등급": (
                "등급(Grade)은 창고재고에만 있는 A/B/F 3단계 분류입니다. "
                "품목코드+LOT 조합마다 A/B/F 세 등급이 항상 함께 존재합니다."
            ),
            "Rev": (
                "Rev(Revision)는 품목의 설계/사양 버전입니다. 품목 기준정보와 재고 조회 모두에서 "
                "같은 품목코드라도 Rev가 다르면 별도 행으로 관리됩니다."
            ),
            "이동 이력": (
                "이동 이력은 시리얼 단위 이동(Movement)과 재고 입출고(가계상/수불 재고 각각의 Movement 테이블)를 "
                "함께 아우르는 용어입니다. 어느 재고인지에 따라 조회되는 테이블이 다릅니다."
            ),
        }
    }


@tool("knowledge.out_of_scope")
def knowledge_out_of_scope(db, question: str = ""):
    return {
        "status": "out_of_scope",
        "message": (
            "저는 현재 Logistics 시스템 데이터와 업무 용어를 기준으로 답변합니다. "
            "날씨, 뉴스, 주가처럼 외부 실시간 정보는 이 assistant에서 조회하지 않습니다."
        )
    }


@tool("admin.account_action")
def admin_account_action(db, action: str = ""):
    return {
        "status": "account_action",
        "action": action,
        "type": "move",
        "url": "/admin/users",
        "message": (
            "계정 생성은 보안상 AI 채팅에서 직접 처리하지 않습니다. "
            "관리자 계정 관리 화면에서 사용자명, 초기 비밀번호, 권한을 입력해 생성해 주세요."
        )
    }


@tool("activity.login_summary")
def activity_login_summary(db, period: str = "all", keyword: str = ""):
    query = db.query(ActivityLog).filter(ActivityLog.action == "LOGIN")

    start, end = _period_range(period)

    if start and end:
        query = query.filter(
            ActivityLog.created_at >= start,
            ActivityLog.created_at < end,
        )

    keyword = _keyword(keyword)

    if keyword:
        pattern = _like(keyword)
        query = query.filter(
            or_(
                func.lower(ActivityLog.user).like(pattern),
                func.lower(ActivityLog.serial).like(pattern),
                func.lower(ActivityLog.detail).like(pattern),
            )
        )

    rows = query.order_by(ActivityLog.id.desc()).limit(MAX_ROWS + 1).all()
    users = sorted({row.user for row in rows if row.user})

    return {
        "status": "login_summary",
        "period": period,
        "keyword": keyword,
        "count": query.count(),
        "users": users,
        "truncated": len(rows) > MAX_ROWS,
        "rows": [
            {
                "created_at": _fmt_dt(row.created_at),
                "user": row.user,
                "detail": row.detail,
            }
            for row in rows[:MAX_ROWS]
        ],
    }


@tool("logistics.flow_count")
def logistics_flow_count(
    db,
    flow_type: str = "both",
    product: str = "",
    period: str = "all",
    keyword: str = "",
):
    inbound_query = _apply_flow_filters(
        db.query(Inbound),
        Inbound,
        product=product,
        period=period,
        keyword=keyword,
    )

    outbound_query = _apply_flow_filters(
        db.query(Outbound),
        Outbound,
        product=product,
        period=period,
        keyword=keyword,
    )

    inbound_count = inbound_query.count() if flow_type in ("both", "inbound") else 0
    outbound_count = outbound_query.count() if flow_type in ("both", "outbound") else 0

    return {
        "status": "flow_count",
        "flow_type": flow_type,
        "product": product,
        "product_name": SERVICE_NAMES.get(product, product) if product else "",
        "period": period,
        "keyword": keyword,
        "inbound_count": inbound_count,
        "outbound_count": outbound_count,
        "inbound_rows": (
            _flow_rows(inbound_query, Inbound)
            if flow_type in ("both", "inbound")
            else []
        ),
        "outbound_rows": (
            _flow_rows(outbound_query, Outbound)
            if flow_type in ("both", "outbound")
            else []
        ),
    }


@tool("logistics.dashboard")
def logistics_dashboard(db, period: str = "all"):
    total_in = db.query(Inbound).count()
    total_out = db.query(Outbound).count()

    query_in = db.query(Inbound)
    query_out = db.query(Outbound)

    start, end = _period_range(period)

    if start and end:
        query_in = query_in.filter(
            Inbound.created_at >= start,
            Inbound.created_at < end,
        )
        query_out = query_out.filter(
            Outbound.created_at >= start,
            Outbound.created_at < end,
        )

    period_in = query_in.count()
    period_out = query_out.count()

    missing = query_out.filter(
        or_(Outbound.category.is_(None), Outbound.client.is_(None))
    ).count()

    return {
        "status": "logistics_dashboard",
        "period": period,
        "total_in": total_in,
        "total_out": total_out,
        "period_in": period_in,
        "period_out": period_out,
        "missing": missing,
    }


@tool("stock.summary")
def stock_summary(
    db,
    category: str = "",
    item: str = "",
    sort: str = "",
    order: str = "asc",
    limit: int = MAX_ROWS,
):
    keyword = _keyword(item)

    def apply_scope(q):
        if category:
            q = q.filter(Stock.category == category)

        if keyword:
            pattern = _like(keyword)
            q = q.filter(
                or_(
                    func.lower(Stock.item_code).like(pattern),
                    func.lower(Stock.item_name).like(pattern),
                    func.lower(Stock.category).like(pattern),
                )
            )

        return q

    if sort == "qty":

        # 창고재고와 같은 방식으로 품목코드마다 A/B/F 등급이 항상 세
        # 행으로 나뉘어 저장돼 있다. 개별 행을 qty로 정렬하면 "가장
        # 많은 품목"이 실제로는 어느 한 등급 한 행일 뿐이라 다른
        # 등급을 합친 진짜 총 재고량과 다른 값이 나온다 - 품목코드
        # 단위로 등급을 합산한 뒤 정렬해야 한다.
        grouped = apply_scope(
            db.query(
                Stock.item_code,
                Stock.item_name,
                Stock.category,
                Stock.rev,
                func.sum(Stock.qty).label("qty"),
            ).group_by(
                Stock.item_code,
                Stock.item_name,
                Stock.category,
                Stock.rev,
            )
        )

        grouped = grouped.order_by(
            func.sum(Stock.qty).desc() if order == "desc" else func.sum(Stock.qty).asc()
        )

        grouped_rows = grouped.limit(limit + 1).all()
        total_rows = apply_scope(
            db.query(Stock.item_code).distinct()
        ).count()

        rows = [
            SimpleNamespace(
                item_code=row.item_code,
                item_name=row.item_name,
                category=row.category,
                # grade는 A/B/F 등급을 합산한 값이라 특정 등급 하나로
                # 표시할 수 없다 - null이 아니라 빈 문자열로 둬서(다른
                # tool들의 "해당 없음" 관례와 동일하게) 응답 생성 AI가
                # null을 보고 "데이터 없음"으로 오해해 답변을 얼버무리는
                # 것을 방지한다.
                grade="",
                rev=row.rev,
                qty=row.qty or 0,
            )
            for row in grouped_rows
        ]

        total_qty = apply_scope(
            db.query(func.coalesce(func.sum(Stock.qty), 0))
        ).scalar() or 0

    else:

        query = apply_scope(db.query(Stock))

        if sort == "item_name":

            if order == "desc":
                query = query.order_by(Stock.item_name.desc())

            else:
                query = query.order_by(Stock.item_name.asc())

        else:

            query = query.order_by(
                Stock.category,
                Stock.item_name,
                Stock.item_code,
            )

        rows = query.limit(limit + 1).all()
        total_rows = query.count()

        # order_by() must be cleared before collapsing to a bare aggregate -
        # Postgres rejects ORDER BY columns that aren't grouped/aggregated
        # when the SELECT list is aggregate-only (SQLite silently allows it,
        # which is why this only surfaced against the Postgres/Neon DB).
        total_qty = (
            query.order_by(None)
            .with_entities(func.coalesce(func.sum(Stock.qty), 0))
            .scalar()
            or 0
        )

    category_rows = (
        db.query(
            Stock.category,
            func.count(Stock.id),
            func.coalesce(func.sum(Stock.qty), 0),
        )
        .group_by(Stock.category)
        .order_by(Stock.category)
        .all()
    )

    return {
        "status": "stock_summary",
        "stock_type": "book_stock",
        "stock_name": "가계상 재고",
        "sort": sort,
        "order": order,
        "limit": limit,
        "category": category,
        "keyword": keyword,
        "total_rows": total_rows,
        "total_qty": int(total_qty),
        "is_top_result": (
            sort == "qty"
            and limit == 1
        ),
        "category_summary": [
            {
                "category": row[0],
                "row_count": row[1],
                "qty": int(row[2] or 0),
            }
            for row in category_rows
        ],
        "truncated": len(rows) > limit,
        "rows": [
            {
                "item_code": row.item_code,
                "item_name": row.item_name,
                "category": row.category,
                "grade": row.grade,
                "rev": row.rev,
                "qty": row.qty or 0,
            }
            for row in rows[:limit]
        ],
    }


@tool("stock.dashboard")
def stock_dashboard_summary(db):
    total_items = db.query(
        func.count(distinct(Stock.item_code))
    ).scalar() or 0

    total_qty = db.query(
        func.coalesce(func.sum(Stock.qty), 0)
    ).scalar() or 0

    today_in = db.query(
        func.coalesce(func.sum(StockMovement.qty), 0)
    ).filter(StockMovement.movement_type == "IN").scalar() or 0

    today_out = db.query(
        func.coalesce(func.sum(StockMovement.qty), 0)
    ).filter(StockMovement.movement_type == "OUT").scalar() or 0

    category_summary = []

    for category in ("반제품", "제품", "원자재"):
        qty = db.query(
            func.coalesce(func.sum(Stock.qty), 0)
        ).filter(Stock.category == category).scalar() or 0

        category_summary.append({"category": category, "qty": int(qty)})

    return {
        "status": "stock_dashboard",
        "total_items": int(total_items),
        "total_qty": int(total_qty),
        "today_in": int(today_in),
        "today_out": int(today_out),
        "category_summary": category_summary,
    }


@tool("stock.movement_search")
def stock_movement_search(
    db,
    item: str = "",
    movement_type: str = "",
    period: str = "all",
):
    keyword = _keyword(item)
    query = db.query(StockMovement)

    if keyword:
        pattern = _like(keyword)
        query = query.filter(
            or_(
                func.lower(StockMovement.item_code).like(pattern),
                func.lower(StockMovement.item_name).like(pattern),
            )
        )

    if movement_type in ("IN", "OUT"):
        query = query.filter(StockMovement.movement_type == movement_type)

    start, end = _period_range(period)

    if start and end:
        query = query.filter(
            StockMovement.created_at >= start,
            StockMovement.created_at < end,
        )

    rows = query.order_by(StockMovement.id.desc()).limit(MAX_ROWS + 1).all()

    return {
        "status": "rows",
        "domain": "stock_movement",
        "keyword": keyword,
        "truncated": len(rows) > MAX_ROWS,
        "rows": [
            {
                "created_at": _fmt_dt(row.created_at),
                "item_code": row.item_code,
                "item_name": row.item_name,
                "movement_type": row.movement_type,
                "qty": row.qty or 0,
                "user": row.user,
            }
            for row in rows[:MAX_ROWS]
        ],
    }


@tool("system.summary")
def system_summary(db, question: str = ""):
    inbound_count = db.query(Inbound).count()
    outbound_count = db.query(Outbound).count()
    stock_qty = db.query(func.coalesce(func.sum(Stock.qty), 0)).scalar() or 0
    inventory_qty = db.query(func.coalesce(func.sum(Inventory.qty), 0)).scalar() or 0
    plan_qty = db.query(func.coalesce(func.sum(ProductionPlan.plan_qty), 0)).scalar() or 0

    return {
        "status": "summary",
        "available_stock_types":[
            "가계상 재고",
            "수불 재고"
        ],
        "counts": {
            "items": db.query(Item).count(),
            "inbound": inbound_count,
            "outbound": outbound_count,
            "movements": db.query(Movement).count(),
            "book_stock_rows": db.query(Stock).count(),
            "book_stock_qty": int(stock_qty),
            "inventory_rows": db.query(Inventory).count(),
            "inventory_qty": int(inventory_qty),
            "bom_rows": db.query(BOM).count(),
            "production_plan_rows": db.query(ProductionPlan).count(),
            "production_plan_qty": int(plan_qty),
            "material_master_rows": db.query(MaterialMaster).count(),
            "item_master_rows": db.query(ItemMaster).count(),
            "users": db.query(User).count(),
            "activity_logs": db.query(ActivityLog).count(),
        }
    }


@tool("stock.book")
def stock_book(db, item: str = ""):
    keyword = _keyword(item)
    query = db.query(Stock)

    if keyword:
        pattern = _like(keyword)
        query = query.filter(
            or_(
                func.lower(Stock.item_code).like(pattern),
                func.lower(Stock.item_name).like(pattern),
                func.lower(Stock.category).like(pattern),
            )
        )

    rows = query.order_by(Stock.item_name, Stock.item_code).limit(MAX_ROWS + 1).all()

    return {
        "status": "rows",
        "domain": "book_stock",
        "keyword": keyword,
        "truncated": len(rows) > MAX_ROWS,
        "rows": [
            {
                "item_code": row.item_code,
                "item_name": row.item_name,
                "category": row.category,
                "grade": row.grade,
                "rev": row.rev,
                "qty": row.qty or 0,
            }
            for row in rows[:MAX_ROWS]
        ],
    }

@tool("stock.select")
def stock_select(db):

    return {

        "status":"need_stock_type",

        "choices":[
            "가계상 재고",
            "수불 재고"
        ]

    }

@tool("inventory.search")
def inventory_search(
    db,
    item: str = "",
    warehouse_type: str = "",
    category: str = "",
    grade: str = "",
    lot: str = "",
):
    keyword = _keyword(item)
    query = db.query(Inventory)

    if keyword:
        pattern = _like(keyword)
        query = query.filter(
            or_(
                func.lower(Inventory.item_code).like(pattern),
                func.lower(Inventory.item_name).like(pattern),
                func.lower(Inventory.warehouse_type).like(pattern),
            )
        )

    if warehouse_type in ("창고재고", "제공재고", "외주재고"):
        query = query.filter(Inventory.warehouse_type == warehouse_type)

    if category in ("반제품", "제품", "원자재"):
        query = query.filter(Inventory.category == category)

    if grade in ("A", "B", "F"):
        query = query.filter(Inventory.grade == grade)

    rows = query.order_by(Inventory.item_code, Inventory.warehouse_type).all()

    # LOT은 있는 그대로의 문자열이다 - 파싱/변환 없이 대소문자 무시 정확
    # 일치로만 비교한다.
    lot = (lot or "").strip()

    if lot:
        rows = [row for row in rows if (row.lot or "").strip().lower() == lot.lower()]

    total_qty = sum(row.qty or 0 for row in rows)

    return {
        "status": "rows",
        "domain": "inventory",
        "keyword": keyword,
        "warehouse_type": warehouse_type,
        "category": category,
        "grade": grade,
        "lot": lot,
        "total_rows": len(rows),
        "total_qty": total_qty,
        "truncated": len(rows) > MAX_ROWS,
        "rows": [
            {
                "item_code": row.item_code,
                "item_name": row.item_name,
                "category": row.category,
                "warehouse_type": row.warehouse_type,
                "lot": row.lot,
                "grade": row.grade,
                "rev": row.rev,
                "note": row.note,
                "qty": row.qty or 0,
            }
            for row in rows[:MAX_ROWS]
        ],
    }


@tool("inventory.dashboard")
def inventory_dashboard_summary(db):
    warehouse_filter = Inventory.warehouse_type == "창고재고"

    total_items = db.query(
        func.count(distinct(Inventory.item_code))
    ).filter(warehouse_filter).scalar() or 0

    total_qty = db.query(
        func.coalesce(func.sum(Inventory.qty), 0)
    ).filter(warehouse_filter).scalar() or 0

    today_in = db.query(
        func.coalesce(func.sum(InventoryMovement.qty), 0)
    ).filter(
        InventoryMovement.movement_type == "IN",
        InventoryMovement.warehouse_type == "창고재고",
    ).scalar() or 0

    today_out = db.query(
        func.coalesce(func.sum(InventoryMovement.qty), 0)
    ).filter(
        InventoryMovement.movement_type == "OUT",
        InventoryMovement.warehouse_type == "창고재고",
    ).scalar() or 0

    category_summary = []

    for category in ("반제품", "제품", "원자재"):
        qty = db.query(
            func.coalesce(func.sum(Inventory.qty), 0)
        ).filter(warehouse_filter, Inventory.category == category).scalar() or 0

        category_summary.append({"category": category, "qty": int(qty)})

    return {
        "status": "inventory_dashboard",
        "total_items": int(total_items),
        "total_qty": int(total_qty),
        "today_in": int(today_in),
        "today_out": int(today_out),
        "category_summary": category_summary,
    }


@tool("inventory.movement_search")
def inventory_movement_search(
    db,
    item: str = "",
    warehouse_type: str = "",
    movement_type: str = "",
    period: str = "all",
):
    keyword = _keyword(item)
    query = db.query(InventoryMovement)

    if keyword:
        pattern = _like(keyword)
        query = query.filter(
            or_(
                func.lower(InventoryMovement.item_code).like(pattern),
                func.lower(InventoryMovement.item_name).like(pattern),
            )
        )

    if warehouse_type in ("창고재고", "제공재고", "외주재고"):
        query = query.filter(InventoryMovement.warehouse_type == warehouse_type)

    if movement_type in ("IN", "OUT"):
        query = query.filter(InventoryMovement.movement_type == movement_type)

    start, end = _period_range(period)

    if start and end:
        query = query.filter(
            InventoryMovement.created_at >= start,
            InventoryMovement.created_at < end,
        )

    rows = query.order_by(InventoryMovement.id.desc()).limit(MAX_ROWS + 1).all()

    return {
        "status": "rows",
        "domain": "inventory_movement",
        "keyword": keyword,
        "truncated": len(rows) > MAX_ROWS,
        "rows": [
            {
                "created_at": _fmt_dt(row.created_at),
                "item_code": row.item_code,
                "item_name": row.item_name,
                "warehouse_type": row.warehouse_type,
                "movement_type": row.movement_type,
                "qty": row.qty or 0,
                "user": row.user,
            }
            for row in rows[:MAX_ROWS]
        ],
    }


@tool("bom.detail")
def bom_detail(db, item: str = ""):
    keyword = _keyword(item)
    query = db.query(BOM)

    if keyword:
        pattern = _like(keyword)
        query = query.filter(
            or_(
                func.lower(BOM.product_name).like(pattern),
                func.lower(BOM.component_code).like(pattern),
                func.lower(BOM.component_name).like(pattern),
            )
        )

    rows = query.order_by(BOM.product_name, BOM.component_code).limit(MAX_ROWS + 1).all()

    return {
        "status": "rows",
        "domain": "bom",
        "keyword": keyword,
        "truncated": len(rows) > MAX_ROWS,
        "rows": [
            {
                "product_name": row.product_name,
                "component_code": row.component_code,
                "component_name": row.component_name,
                "qty": row.qty or 0,
            }
            for row in rows[:MAX_ROWS]
        ],
    }


@tool("production.plan")
def production_plan(
    db,
    item: str = "",
    period: str = "all",
    sort: str = "",
    order: str = "asc",
    limit: int = MAX_ROWS,
):
    keyword = _keyword(item)
    query = db.query(ProductionPlan)

    if keyword:
        pattern = _like(keyword)
        query = query.filter(func.lower(ProductionPlan.product_name).like(pattern))

    start, end = _period_range(period)

    if start and end:
        query = query.filter(
            ProductionPlan.plan_date >= start.date(),
            ProductionPlan.plan_date < end.date(),
        )

    try:
        limit = max(1, min(int(limit), MAX_ROWS))
    except (TypeError, ValueError):
        limit = MAX_ROWS

    if sort == "qty":
        query = query.order_by(
            ProductionPlan.plan_qty.desc() if order == "desc" else ProductionPlan.plan_qty.asc()
        )
    else:
        query = query.order_by(ProductionPlan.plan_date, ProductionPlan.product_name)

    rows = query.limit(limit + 1).all()

    return {
        "status": "rows",
        "domain": "production_plan",
        "keyword": keyword,
        "period": period,
        "truncated": len(rows) > limit,
        "rows": [
            {
                "plan_date": _fmt_date(row.plan_date),
                "product_name": row.product_name,
                "plan_qty": row.plan_qty or 0,
            }
            for row in rows[:limit]
        ],
    }


@tool("material.master")
def material_master(
    db,
    item: str = "",
    sort: str = "",
    order: str = "desc",
    limit: int = MAX_ROWS,
):
    keyword = _keyword(item)
    query = db.query(MaterialMaster)

    if keyword:
        pattern = _like(keyword)
        query = query.filter(
            or_(
                func.lower(MaterialMaster.item_code).like(pattern),
                func.lower(MaterialMaster.item_name).like(pattern),
                func.lower(MaterialMaster.supplier).like(pattern),
            )
        )

    try:
        limit = max(1, min(int(limit), MAX_ROWS))
    except (TypeError, ValueError):
        limit = MAX_ROWS

    if sort == "lead_time":
        query = query.order_by(
            MaterialMaster.lead_time_week.desc() if order == "desc" else MaterialMaster.lead_time_week.asc()
        )
    elif sort == "moq":
        query = query.order_by(
            MaterialMaster.moq.desc() if order == "desc" else MaterialMaster.moq.asc()
        )
    else:
        query = query.order_by(MaterialMaster.item_code)

    rows = query.limit(limit + 1).all()
    notes = {
        note.item_code: note.note
        for note in db.query(MaterialNote).filter(
            MaterialNote.item_code.in_([row.item_code for row in rows[:limit]])
        ).all()
    } if rows else {}

    return {
        "status": "rows",
        "domain": "material_master",
        "keyword": keyword,
        "truncated": len(rows) > limit,
        "rows": [
            {
                "item_code": row.item_code,
                "item_name": row.item_name,
                "supplier": row.supplier,
                "lead_time_week": row.lead_time_week or 0,
                "moq": row.moq or 0,
                "note": notes.get(row.item_code, ""),
            }
            for row in rows[:limit]
        ],
    }


@tool("item.master")
def item_master(db, item: str = ""):
    keyword = _keyword(item)
    query = db.query(ItemMaster)

    if keyword:
        pattern = _like(keyword)
        query = query.filter(
            or_(
                func.lower(ItemMaster.item_code).like(pattern),
                func.lower(ItemMaster.item_name).like(pattern),
                func.lower(ItemMaster.rev).like(pattern),
            )
        )

    rows = query.order_by(ItemMaster.item_code).limit(MAX_ROWS + 1).all()

    return {
        "status": "rows",
        "domain": "item_master",
        "keyword": keyword,
        "truncated": len(rows) > MAX_ROWS,
        "rows": [
            {
                "item_code": row.item_code,
                "item_name": row.item_name,
                "rev": row.rev,
            }
            for row in rows[:MAX_ROWS]
        ],
    }


@tool("item.master_history")
def item_master_history(db, item: str = ""):
    keyword = _keyword(item)
    query = db.query(ItemMasterHistory)

    if keyword:
        pattern = _like(keyword)
        query = query.filter(
            or_(
                func.lower(ItemMasterHistory.old_code).like(pattern),
                func.lower(ItemMasterHistory.new_code).like(pattern),
                func.lower(ItemMasterHistory.old_name).like(pattern),
                func.lower(ItemMasterHistory.new_name).like(pattern),
            )
        )

    rows = query.order_by(ItemMasterHistory.id.desc()).limit(MAX_ROWS + 1).all()

    return {
        "status": "rows",
        "domain": "item_master_history",
        "keyword": keyword,
        "truncated": len(rows) > MAX_ROWS,
        "rows": [
            {
                "created_at": _fmt_dt(row.created_at),
                "old_code": row.old_code,
                "new_code": row.new_code,
                "old_name": row.old_name,
                "new_name": row.new_name,
                "old_rev": row.old_rev,
                "new_rev": row.new_rev,
                "user": row.user,
            }
            for row in rows[:MAX_ROWS]
        ],
    }


@tool("movement.search")
def movement_search(db, item: str = ""):
    keyword = _keyword(item)
    pattern = _like(keyword) if keyword else None

    logistics_query = db.query(Movement)
    stock_query = db.query(StockMovement)

    if pattern:
        logistics_query = logistics_query.filter(
            or_(
                func.lower(Movement.serial).like(pattern),
                func.lower(Movement.product).like(pattern),
                func.lower(Movement.type).like(pattern),
                func.lower(Movement.client).like(pattern),
                func.lower(Movement.user).like(pattern),
            )
        )
        stock_query = stock_query.filter(
            or_(
                func.lower(StockMovement.item_code).like(pattern),
                func.lower(StockMovement.item_name).like(pattern),
                func.lower(StockMovement.movement_type).like(pattern),
                func.lower(StockMovement.user).like(pattern),
            )
        )

    movements = logistics_query.order_by(Movement.id.desc()).limit(8).all()
    stock_movements = stock_query.order_by(StockMovement.id.desc()).limit(8).all()

    return {
        "status": "rows",
        "domain": "movement",
        "keyword": keyword,
        "rows": {
            "serial_movements": [
                {
                    "created_at": _fmt_dt(row.created_at),
                    "serial": row.serial,
                    "product": row.product,
                    "type": row.type,
                    "client": row.client,
                    "category": row.category,
                    "user": row.user,
                }
                for row in movements
            ],
            "stock_movements": [
                {
                    "created_at": _fmt_dt(row.created_at),
                    "item_code": row.item_code,
                    "item_name": row.item_name,
                    "category": row.category,
                    "movement_type": row.movement_type,
                    "qty": row.qty or 0,
                    "user": row.user,
                    "source": row.source,
                }
                for row in stock_movements
            ],
        },
    }


@tool("activity.search")
def activity_search(db, item: str = ""):
    keyword = _keyword(item)
    query = db.query(ActivityLog)

    if keyword:
        pattern = _like(keyword)
        query = query.filter(
            or_(
                func.lower(ActivityLog.user).like(pattern),
                func.lower(ActivityLog.product).like(pattern),
                func.lower(ActivityLog.action).like(pattern),
                func.lower(ActivityLog.serial).like(pattern),
                func.lower(ActivityLog.detail).like(pattern),
            )
        )

    rows = query.order_by(ActivityLog.id.desc()).limit(MAX_ROWS + 1).all()

    return {
        "status": "rows",
        "domain": "activity",
        "keyword": keyword,
        "truncated": len(rows) > MAX_ROWS,
        "rows": [
            {
                "created_at": _fmt_dt(row.created_at),
                "user": row.user,
                "product": row.product,
                "action": row.action,
                "serial": row.serial,
                "detail": row.detail,
            }
            for row in rows[:MAX_ROWS]
        ],
    }


@tool("admin.user_summary")
def admin_user_summary(db, item: str = ""):
    keyword = _keyword(item)
    query = db.query(User)

    if keyword:
        pattern = _like(keyword)
        query = query.filter(
            or_(
                func.lower(User.username).like(pattern),
                func.lower(User.role).like(pattern),
            )
        )

    rows = query.order_by(User.username).limit(MAX_ROWS + 1).all()
    role_counts = Counter(row.role for row in db.query(User).all())

    return {
        "status": "users",
        "keyword": keyword,
        "role_counts": dict(role_counts),
        "must_change_password_count": db.query(User).filter(User.must_change_password.is_(True)).count(),
        "truncated": len(rows) > MAX_ROWS,
        "rows": [_safe_user(row) for row in rows[:MAX_ROWS]],
    }


@tool("page.move")
def page_move(db, page: str):
    pages = {
        "dashboard": ("/dashboard/overview", "전체 Dashboard로 이동합니다."),
        "stock": ("/stock", "가계상 재고 현황으로 이동합니다."),
        "stock_history": ("/stock/history", "재고 입출고 현황으로 이동합니다."),
        "stock_dashboard": ("/stock/dashboard", "재고 Dashboard로 이동합니다."),
        "mrp": ("/mrp", "MRP Dashboard로 이동합니다."),
        "mrp_result": ("/mrp/result", "MRP Result로 이동합니다."),
        "bom": ("/mrp/bom", "BOM 화면으로 이동합니다."),
        "production_plan": ("/mrp/production-plan", "생산 계획 화면으로 이동합니다."),
        "inventory": ("/inventory", "수불 재고 현황으로 이동합니다."),
        "inventory_history": ("/inventory/history", "수불 재고 입출고 현황으로 이동합니다."),
        "inventory_dashboard": ("/inventory/dashboard", "수불 재고 Dashboard로 이동합니다."),
        "material_master": ("/mrp/material-master", "자재 기준정보로 이동합니다."),
        "item_master": ("/stock/item-master/manage", "품목 관리로 이동합니다."),
        "users": ("/admin/users", "계정 관리로 이동합니다."),
        "activity": ("/admin/activity", "활동 로그로 이동합니다."),
        "search": ("/search", "전체 조회로 이동합니다."),
    }

    url, message = pages.get(page, pages["dashboard"])

    return {
        "status": "move",
        "type": "move",
        "url": url,
        "message": message,
    }


@tool("page.find")
def page_find(db, page: str = "", target: str = ""):
    target = _keyword(target)
    encoded = _encoded(target)

    if page == "mrp_result":
        return {
            "status": "move",
            "type": "move",
            "url": f"/mrp/result?highlight={encoded}",
            "message": f"MRP Result 전체 목록에서 '{target}' 행을 표시합니다.",
        }

    if page == "stock":
        # The /stock route always filters to one category (defaults to
        # 반제품 if none is given - there is no "all categories" view),
        # so the right category has to be resolved before navigating or
        # the target row may not even be in the rendered table.
        #
        # A bare number ("수량이 100인 행으로 이동") means a quantity
        # value, not an item code/name - look it up by qty, not by a
        # substring match against item_code/item_name/category, which
        # would land on the category of an unrelated item whose code
        # happens to contain that number.
        if target.isdigit():
            stock = (
                db.query(Stock)
                .filter(Stock.qty == int(target))
                .first()
            )
        else:
            stock = (
                db.query(Stock)
                .filter(_contains_filter(Stock, ["item_code", "item_name", "category"], target))
                .first()
            )

        category = stock.category if stock else ""
        url = f"/stock?highlight={encoded}"
        if category:
            url = f"/stock?category={_encoded(category)}&highlight={encoded}"

        return {
            "status": "move",
            "type": "move",
            "url": url,
            "message": f"가계상 재고에서 '{target}' 위치로 이동합니다.",
        }

    if page == "stock_history":
        return {
            "status": "move",
            "type": "move",
            "url": f"/stock/history?highlight={encoded}",
            "message": f"재고 입출고 이력 전체 목록에서 '{target}' 행을 표시합니다.",
        }

    if page == "bom":
        return {
            "status": "move",
            "type": "move",
            "url": f"/mrp/bom?highlight={encoded}",
            "message": f"BOM 화면에서 '{target}' 위치로 이동합니다.",
        }

    if page == "material_master":
        return {
            "status": "move",
            "type": "move",
            "url": f"/mrp/material-master?highlight={encoded}",
            "message": f"자재 기준정보에서 '{target}' 위치로 이동합니다.",
        }

    if page == "item_master":
        return {
            "status": "move",
            "type": "move",
            "url": f"/stock/item-master/manage?highlight={encoded}",
            "message": f"품목 기준정보에서 '{target}' 위치로 이동합니다.",
        }

    matches = _find_page_matches(db, target)

    if len(matches) == 1:
        match = matches[0]
        return {
            "status": "move",
            "type": "move",
            "url": match["url"],
            "message": f"{match['label']}에서 '{target}' 위치로 이동합니다.",
        }

    if len(matches) > 1:
        # Same item code exists in more than one module - ask instead
        # of silently guessing (guessing always picked Stock, since it
        # was the first table checked, regardless of what the user
        # actually meant).
        return {
            "status": "need_page_choice",
            "target": target,
            "choices": matches,
            "message": f"'{target}'이(가) 여러 화면에 있습니다. 어디로 이동할까요?",
        }

    return {
        "status": "move",
        "type": "move",
        "url": f"/search?highlight={encoded}",
        "message": f"'{target}'를 전체 조회 화면에서 확인해 주세요.",
    }


@tool("page.choice")
def page_choice(db, url: str = "", message: str = ""):
    """Resolves a pending "which page did you mean" follow-up.

    Only ever invoked internally by AssistantAgent's follow-up resolver
    once the user has picked one of the offered options - never exposed
    to the AI planner or keyword router, since `url` is trusted/
    pre-built rather than user- or model-controlled input.
    """
    return {
        "status": "move",
        "type": "move",
        "url": url,
        "message": message or "요청한 위치로 이동합니다.",
    }


@tool("global.search")
def global_search(db, item: str = ""):
    keyword = _keyword(item)

    if not keyword:
        return system_summary(db)

    return {
        "status": "global_search",
        "keyword": keyword,
        "book_stock": stock_book(db, keyword)["rows"][:5],
        "inventory": inventory_search(db, keyword)["rows"][:5],
        "bom": bom_detail(db, keyword)["rows"][:5],
        "production_plan": production_plan(db, keyword)["rows"][:5],
        "material_master": material_master(db, keyword)["rows"][:5],
        "item_master": item_master(db, keyword)["rows"][:5],
    }

@tool("mrp.shortage_max")
def mrp_shortage_max(db):

    _, results, _, _ = calculate_mrp(db)

    if not results:
        return {
            "status": "none",
            "message": "MRP 결과가 없습니다."
        }

    row = max(
        results,
        key=lambda r: r.get("shortage_qty", 0)
    )

    return {
        "type": "move",
        "status": "success",
        # highlight (not q) so the full table renders and base.html's
        # global highlightAssistantTarget() finds and scrolls to the
        # row - q instead filters the table down to just this row,
        # which leaves nothing for the highlight effect to apply to.
        "url": f"/mrp/result?highlight={_encoded(row['item_code'])}",
        "message": (
            f"부족 수량이 가장 많은 품목은 "
            f"{row['item_code']} ({row['item_name']}) 입니다."
        )
    }


@tool("mrp.shortage_min")
def mrp_shortage_min(db):

    _, results, _, _ = calculate_mrp(db)

    if not results:
        return {
            "status": "none",
            "message": "MRP 결과가 없습니다."
        }

    row = min(
        results,
        key=lambda r: r.get("shortage_qty", 0)
    )

    if row.get("shortage_qty", 0) <= 0:
        message = (
            f"부족 수량이 없는 품목의 예시는 "
            f"{row['item_code']} ({row['item_name']}) 입니다."
        )
    else:
        message = (
            f"부족 수량이 가장 적은 품목은 "
            f"{row['item_code']} ({row['item_name']})이며, "
            f"부족 수량은 {row['shortage_qty']}입니다."
        )

    return {
        "type": "move",
        "status": "success",
        "url": f"/mrp/result?highlight={_encoded(row['item_code'])}",
        "message": message,
    }


@tool("mrp.shortage_search")
def mrp_shortage_search(db, sort: str = "desc", limit: int = 5):

    _, results, _, _ = calculate_mrp(db)

    if not results:
        return {
            "status": "none",
            "message": "MRP 결과가 없습니다."
        }

    try:
        limit = max(1, min(int(limit), MAX_ROWS))
    except (TypeError, ValueError):
        limit = 5

    ordered = sorted(
        results,
        key=lambda r: r.get("shortage_qty", 0),
        reverse=(sort != "asc"),
    )

    return {
        "status": "rows",
        "domain": "mrp_result",
        "truncated": len(ordered) > limit,
        "rows": [
            {
                "item_code": row["item_code"],
                "item_name": row["item_name"],
                "shortage_qty": row.get("shortage_qty", 0),
                "recommended_order_qty": row.get("recommended_order_qty", 0),
                "need_date": _fmt_date(row.get("need_date")),
                "supplier": row.get("supplier") or "",
            }
            for row in ordered[:limit]
        ],
    }


@tool("mrp.dashboard")
def mrp_dashboard_summary(db):

    _, results, shortage_count, _ = calculate_mrp(db)

    if not results:
        return {
            "status": "none",
            "message": "MRP 결과가 없습니다."
        }

    total_required = sum(row.get("required_qty", 0) for row in results)
    total_stock = sum(row.get("stock_qty", 0) for row in results)
    total_shortage = sum(row.get("shortage_qty", 0) for row in results)

    shortage_rate = (
        round(total_shortage / total_required * 100, 1)
        if total_required
        else 0
    )

    top_shortages = sorted(
        (row for row in results if row.get("shortage_qty", 0) > 0),
        key=lambda r: r["shortage_qty"],
        reverse=True,
    )[:5]

    return {
        "status": "mrp_dashboard",
        "total_items": len(results),
        "shortage_count": shortage_count,
        "total_required": total_required,
        "total_stock": total_stock,
        "total_shortage": total_shortage,
        "shortage_rate": shortage_rate,
        "top_shortages": [
            {
                "item_code": row["item_code"],
                "item_name": row["item_name"],
                "shortage_qty": row["shortage_qty"],
            }
            for row in top_shortages
        ],
    }
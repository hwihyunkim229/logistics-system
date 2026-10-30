from app.models.user_permission import UserPermission


PERMISSION_ACTIONS = (
    ("view", "조회"),
    ("edit", "수정"),
    ("download", "다운로드"),
)

PERMISSION_GROUPS = (
    ("공통", (("common_search", "통합 검색"),)),
    ("제품 물류", (("logistics_outbound", "출고 관리"), ("logistics_inbound", "입고 관리"), ("logistics_dashboard", "Dashboard"))),
    ("수불 재고", (("inventory_stock", "재고 현황"), ("inventory_history", "입출고 현황"), ("inventory_dashboard", "Dashboard"))),
    ("가계상 재고", (("stock_stock", "재고 현황"), ("stock_history", "입출고 현황"), ("stock_dashboard", "Dashboard"))),
    ("대여 관리", (("rental_stock", "재고 현황"), ("rental_history", "입출고 현황"))),
    ("CART PLATFORM IEM", (("workflow_overview", "Dashboard"), ("workflow_purchase", "구매 관리"), ("workflow_quality", "품질 관리"), ("workflow_material", "자재 관리"), ("workflow_production", "생산 관리"))),
    ("MRP", (("mrp_result", "MRP Result"), ("mrp_bom", "BOM"), ("mrp_plan", "생산 계획"), ("mrp_material", "자재 기준 정보"), ("mrp_dashboard", "Dashboard"))),
    ("기준 정보", (("master_items", "품목 관리"),)),
)

PERMISSION_FEATURES = tuple(
    feature
    for _, features in PERMISSION_GROUPS
    for feature in features
)

FEATURE_KEYS = {key for key, _ in PERMISSION_FEATURES}
ACTION_KEYS = {key for key, _ in PERMISSION_ACTIONS}

LEGACY_TEAM_FEATURE = {
    "purchase": "workflow_purchase",
    "quality": "workflow_quality",
    "material": "workflow_material",
    "production": "workflow_production",
    "vsp": "rental_stock",
}

ALWAYS_ALLOWED_PREFIXES = (
    "/logout",
    "/change-password",
    "/assistant",
    "/guide",
    "/workflow/notification",
)

FEATURE_HOME_PATHS = {
    "common_search": "/search",
    "logistics_outbound": "/product/cart_bp_pro/outbound",
    "logistics_inbound": "/product/cart_bp_pro/inbound",
    "logistics_dashboard": "/dashboard/overview",
    "inventory_stock": "/inventory",
    "inventory_history": "/inventory/history",
    "inventory_dashboard": "/inventory/dashboard",
    "stock_stock": "/stock",
    "stock_history": "/stock/history",
    "stock_dashboard": "/stock/dashboard",
    "rental_stock": "/rental",
    "rental_history": "/rental/history",
    "workflow_overview": "/workflow/dashboard",
    "workflow_purchase": "/workflow/purchase",
    "workflow_quality": "/workflow/quality",
    "workflow_material": "/workflow/material",
    "workflow_production": "/workflow/production",
    "mrp_result": "/mrp/result",
    "mrp_bom": "/mrp/bom",
    "mrp_plan": "/mrp/production-plan",
    "mrp_material": "/mrp/material-master",
    "mrp_dashboard": "/mrp",
    "master_items": "/stock/item-master/manage",
}

LEGACY_FEATURE_CHILDREN = {
    "logistics": ("common_search", "logistics_outbound", "logistics_inbound", "logistics_dashboard"),
    "inventory": ("inventory_stock", "inventory_history", "inventory_dashboard"),
    "stock": ("stock_stock", "stock_history", "stock_dashboard", "master_items"),
    "rental": ("rental_stock", "rental_history"),
    "mrp": ("mrp_result", "mrp_bom", "mrp_plan", "mrp_material", "mrp_dashboard"),
}


def feature_for_path(path):
    if path.startswith("/admin"):
        return "admin"
    if path.startswith("/search") or path.startswith("/history-api"):
        return "common_search"
    if path.startswith("/workflow/purchase"):
        return "workflow_purchase"
    if path.startswith("/workflow/quality"):
        return "workflow_quality"
    if (
        path.startswith("/workflow/material")
        or path.startswith("/workflow/remnant")
    ):
        return "workflow_material"
    if path.startswith("/workflow/production"):
        return "workflow_production"
    if (
        path.startswith("/workflow/dashboard")
        or path.startswith("/workflow/history")
    ):
        return "workflow_overview"
    if path.startswith("/stock/item-master"):
        return "master_items"
    if path.startswith("/stock/history"):
        return "stock_history"
    if path.startswith("/stock/dashboard"):
        return "stock_dashboard"
    if path.startswith("/stock"):
        return "stock_stock"
    if path.startswith("/inventory/history"):
        return "inventory_history"
    if path.startswith("/inventory/dashboard"):
        return "inventory_dashboard"
    if path.startswith("/inventory"):
        return "inventory_stock"
    if path.startswith("/mrp/result"):
        return "mrp_result"
    if path.startswith("/mrp/bom"):
        return "mrp_bom"
    if path.startswith("/mrp/production-plan"):
        return "mrp_plan"
    if path.startswith("/mrp/material-master"):
        return "mrp_material"
    if path == "/mrp" or path.startswith("/mrp/dashboard"):
        return "mrp_dashboard"
    if path.startswith("/mrp"):
        return "mrp_dashboard"
    if path.startswith("/rental/history"):
        return "rental_history"
    if path.startswith("/rental"):
        return "rental_stock"
    if path.startswith("/product") and "/outbound" in path:
        return "logistics_outbound"
    if path.startswith("/product") and "/inbound" in path:
        return "logistics_inbound"
    if path.startswith("/dashboard"):
        return "logistics_dashboard"
    return "logistics_dashboard"


def action_for_request(method, path):
    if method not in {"GET", "HEAD"}:
        return "edit"

    lowered = path.lower()
    if any(
        marker in lowered
        for marker in ("download", "export", "backup", "attachment")
    ) or lowered.endswith("/template"):
        return "download"

    return "view"


def first_allowed_home(permissions, preferred_feature=None):
    if (
        preferred_feature in FEATURE_HOME_PATHS
        and permissions.get((preferred_feature, "view"), False)
    ):
        return FEATURE_HOME_PATHS[preferred_feature]

    for feature, _ in PERMISSION_FEATURES:
        if permissions.get((feature, "view"), False):
            return FEATURE_HOME_PATHS[feature]

    return None


def legacy_permissions(user):
    permissions = {
        (feature, action): False
        for feature in FEATURE_KEYS
        for action in ACTION_KEYS
    }

    if user.role == "admin":
        return {
            key: True
            for key in permissions
        }

    for feature in FEATURE_KEYS:
        permissions[(feature, "view")] = True

    if user.role == "viewer":
        return permissions

    team = (user.team or "").strip()
    if not team:
        return {
            key: True
            for key in permissions
        }

    feature = LEGACY_TEAM_FEATURE.get(team)
    if feature:
        permissions[(feature, "edit")] = True
        permissions[(feature, "download")] = True

    return permissions


def permission_map(db, user):
    if user.role == "admin":
        return {
            (feature, action): True
            for feature in FEATURE_KEYS
            for action in ACTION_KEYS
        }

    rows = (
        db.query(UserPermission)
        .filter(UserPermission.user_id == user.id)
        .all()
    )
    if not rows:
        return legacy_permissions(user)

    permissions = {
        (feature, action): False
        for feature in FEATURE_KEYS
        for action in ACTION_KEYS
    }
    for row in rows:
        if row.feature in FEATURE_KEYS and row.action in ACTION_KEYS:
            permissions[(row.feature, row.action)] = bool(row.allowed)
        elif row.feature in LEGACY_FEATURE_CHILDREN and row.action in ACTION_KEYS:
            for child in LEGACY_FEATURE_CHILDREN[row.feature]:
                permissions[(child, row.action)] = bool(row.allowed)

    return permissions


def has_permission(db, user, feature, action):
    if user.role == "admin":
        return True
    return permission_map(db, user).get((feature, action), False)


def replace_user_permissions(db, user_id, selected):
    (
        db.query(UserPermission)
        .filter(UserPermission.user_id == user_id)
        .delete(synchronize_session=False)
    )

    for feature in FEATURE_KEYS:
        for action in ACTION_KEYS:
            db.add(
                UserPermission(
                    user_id=user_id,
                    feature=feature,
                    action=action,
                    allowed=(feature, action) in selected,
                )
            )

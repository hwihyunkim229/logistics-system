from app.models.user_permission import UserPermission


PERMISSION_ACTIONS = (
    ("view", "조회"),
    ("edit", "수정"),
    ("download", "다운로드"),
)

PERMISSION_FEATURES = (
    ("logistics", "통합 물류"),
    ("inventory", "수불재고"),
    ("stock", "가계상 재고"),
    ("mrp", "MRP"),
    ("rental", "대여재고"),
    ("workflow_overview", "Workflow 현황/이력"),
    ("workflow_purchase", "Workflow 구매"),
    ("workflow_quality", "Workflow 품질"),
    ("workflow_material", "Workflow 자재"),
    ("workflow_production", "Workflow 생산"),
)

FEATURE_KEYS = {key for key, _ in PERMISSION_FEATURES}
ACTION_KEYS = {key for key, _ in PERMISSION_ACTIONS}

LEGACY_TEAM_FEATURE = {
    "purchase": "workflow_purchase",
    "quality": "workflow_quality",
    "material": "workflow_material",
    "production": "workflow_production",
    "vsp": "rental",
}

ALWAYS_ALLOWED_PREFIXES = (
    "/logout",
    "/change-password",
    "/assistant",
    "/workflow/notification",
)

FEATURE_HOME_PATHS = {
    "logistics": "/search",
    "inventory": "/inventory",
    "stock": "/stock",
    "mrp": "/mrp/result",
    "rental": "/rental",
    "workflow_overview": "/workflow/dashboard",
    "workflow_purchase": "/workflow/purchase",
    "workflow_quality": "/workflow/quality",
    "workflow_material": "/workflow/material",
    "workflow_production": "/workflow/production",
}


def feature_for_path(path):
    if path.startswith("/admin"):
        return "admin"
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
    if path.startswith("/stock"):
        return "stock"
    if path.startswith("/inventory"):
        return "inventory"
    if path.startswith("/mrp"):
        return "mrp"
    if path.startswith("/rental"):
        return "rental"
    return "logistics"


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

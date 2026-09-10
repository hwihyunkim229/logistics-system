"""Shared product catalog for logistics forms and dashboard reporting."""
from app.models.product_category import ProductCategory
from app.models.inbound import Inbound
from app.models.outbound import Outbound
from app.models.movement import Movement

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

def product_categories(db):
    rows = db.query(ProductCategory).order_by(ProductCategory.id).all()
    if not rows:
        for code in SERVICES:
            db.add(ProductCategory(code=code, name=SERVICE_NAMES[code]))
        db.commit()
        rows = db.query(ProductCategory).order_by(ProductCategory.id).all()
    return rows

def dashboard_product_names(db):
    """Registered categories, plus historical codes so existing data is not hidden."""
    rows = db.query(ProductCategory).order_by(ProductCategory.id).all()
    names = {row.code: row.name for row in rows} if rows else dict(SERVICE_NAMES)
    historical_codes = set()
    for model in (Inbound, Outbound, Movement):
        historical_codes.update(
            row[0] for row in db.query(model.product).distinct().all() if row[0]
        )
    for code in sorted(historical_codes):
        names.setdefault(code, SERVICE_NAMES.get(code, code))
    return names

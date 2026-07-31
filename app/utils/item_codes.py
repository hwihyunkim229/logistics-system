import re

def normalize_item_code(value):
    """Remove accidental whitespace from item codes without changing other text."""
    if value is None:
        return ""

    return re.sub(r"\s+", "", str(value))
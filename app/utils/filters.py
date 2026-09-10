"""Repeated query parameters represent OR values within one filter."""


def filter_values(request, name):
    return list(dict.fromkeys(value for value in request.query_params.getlist(name) if value))


def filter_ints(request, name):
    from fastapi import HTTPException

    try:
        values = [int(value) for value in filter_values(request, name)]
        lower, upper = {"year": (1, 9999), "month": (1, 12), "week": (1, 53)}.get(name, (0, 9999))
        if any(value < lower or value > upper for value in values):
            raise ValueError(name)
        return values
    except ValueError:
        raise HTTPException(status_code=422, detail=f"Invalid {name} filter")


def as_values(value):
    if value is None or value == "":
        return []
    return list(value) if isinstance(value, (list, tuple, set)) else [value]


def matches_filter(value, selected):
    values = as_values(selected)
    return not values or value in values

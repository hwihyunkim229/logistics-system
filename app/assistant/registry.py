TOOLS = {}


def tool(name: str):

    def decorator(func):

        TOOLS[name] = func

        return func

    return decorator

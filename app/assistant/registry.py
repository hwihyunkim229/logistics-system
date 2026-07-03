# Every AI/user-facing action must be a plain Python function registered
# here by name. The AI (Groq) and the keyword router only ever produce a
# {"tool": name, "arguments": {...}} dict - they never construct SQL or
# call the database directly. app.assistant.router.ToolRouter looks the
# name up in this dict and calls the function; any name not registered
# here is rejected, so no dynamically built query, eval, or shell command
# can ever be reached through the assistant.
TOOLS = {}


def tool(name: str):

    def decorator(func):

        TOOLS[name] = func

        return func

    return decorator

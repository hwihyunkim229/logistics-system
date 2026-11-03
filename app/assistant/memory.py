class ConversationMemory:

    def __init__(self):
        self.memory = {}
        self.context = {}

    def save(
        self,
        session_id,
        tool,
        items
    ):

        self.memory[session_id] = {

            "tool": tool,

            "items": items

        }

    def get(self, session_id):

        return self.memory.get(session_id)

    def save_context(self, session_id, tool, arguments):
        self.context[session_id] = {
            "tool": tool,
            "arguments": dict(arguments or {}),
        }

    def get_context(self, session_id):
        return self.context.get(session_id)

    def clear(self, session_id):

        if session_id in self.memory:

            del self.memory[session_id]

        if session_id in self.context:
            del self.context[session_id]

memory = ConversationMemory()

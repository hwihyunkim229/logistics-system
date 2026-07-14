class ConversationMemory:

    def __init__(self):
        self.memory = {}

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

    def clear(self, session_id):

        if session_id in self.memory:

            del self.memory[session_id]

memory = ConversationMemory()
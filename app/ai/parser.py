import json

def parse_tool(text):

    try:
        return json.loads(text)

    except Exception:

        return {
            "tool":"general",
            "arguments":{
                "question":text
            }
        }
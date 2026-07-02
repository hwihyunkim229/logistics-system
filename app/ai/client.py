import os

from app.ai.prompts import SYSTEM_PROMPT

try:
    from dotenv import load_dotenv
except ModuleNotFoundError:
    def load_dotenv():
        return False

try:
    from groq import Groq
except ModuleNotFoundError:
    Groq = None

load_dotenv()

MODEL_NAME = "llama-3.3-70b-versatile"

api_key = os.getenv("GROQ_API_KEY")
client = Groq(api_key=api_key) if Groq and api_key else None


def ask_ai(
    user_message: str,
    system_prompt: str = SYSTEM_PROMPT,
    temperature: float = 0
):
    if client is None:
        return ""

    try:
        response = client.chat.completions.create(

            model=MODEL_NAME,

            temperature=temperature,

            messages=[
                {
                    "role": "system",
                    "content": system_prompt
                },
                {
                    "role": "user",
                    "content": user_message
                }
            ]
        )

        return response.choices[0].message.content.strip()

    except Exception:
        return ""
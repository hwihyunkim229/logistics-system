import logging
import os
import threading
import time
from collections import OrderedDict
from datetime import date
from hashlib import sha256

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

MODEL_NAME = os.getenv("GROQ_MODEL", "openai/gpt-oss-20b").strip()

api_key = os.getenv("GROQ_API_KEY")
client = Groq(api_key=api_key) if Groq and api_key else None
logger = logging.getLogger(__name__)

def _env_int(name, default, minimum=0):
    try:
        return max(minimum, int(os.getenv(name, str(default))))
    except (TypeError, ValueError):
        logger.warning("Invalid integer value for %s; using %s", name, default)
        return default

AI_ENABLED = os.getenv("AI_ENABLED", "1").strip().lower() not in ("0", "false", "off", "no")
DAILY_LIMIT = _env_int("AI_DAILY_REQUEST_LIMIT", 100)
CACHE_TTL_SECONDS = _env_int("AI_CACHE_TTL_SECONDS", 3600)
CACHE_MAX_ENTRIES = _env_int("AI_CACHE_MAX_ENTRIES", 256, 1)
FAILURE_THRESHOLD = _env_int("AI_FAILURE_THRESHOLD", 3, 1)
CIRCUIT_SECONDS = _env_int("AI_CIRCUIT_SECONDS", 300, 1)

_lock = threading.Lock()
_cache = OrderedDict()
_usage_day = date.today()
_usage_count = 0
_failure_count = 0
_circuit_until = 0.0


def _cache_key(user_message, system_prompt, temperature):
    raw = f"{MODEL_NAME}\0{temperature}\0{system_prompt}\0{user_message}"
    return sha256(raw.encode("utf-8", errors="replace")).hexdigest()


def _rotate_day():
    global _usage_day, _usage_count
    today = date.today()
    if today != _usage_day:
        _usage_day = today
        _usage_count = 0


def get_ai_status():
    with _lock:
        _rotate_day()
        available = bool(AI_ENABLED and client is not None)
        circuit_open = time.monotonic() < _circuit_until
        quota_exhausted = DAILY_LIMIT > 0 and _usage_count >= DAILY_LIMIT
        return {
            "available": available and not circuit_open and not quota_exhausted,
            "configured": client is not None,
            "enabled": AI_ENABLED,
            "daily_limit": DAILY_LIMIT,
            "used_today": _usage_count,
            "quota_exhausted": quota_exhausted,
            "circuit_open": circuit_open,
            "cache_entries": len(_cache),
        }


def ask_ai(
    user_message: str,
    system_prompt: str = SYSTEM_PROMPT,
    temperature: float = 0
):
    global _usage_count, _failure_count, _circuit_until

    if not AI_ENABLED or client is None:
        return ""

    key = _cache_key(user_message, system_prompt, temperature)
    now = time.monotonic()

    with _lock:
        _rotate_day()
        cached = _cache.get(key)
        if cached and now - cached[0] <= CACHE_TTL_SECONDS:
            _cache.move_to_end(key)
            return cached[1]
        if cached:
            _cache.pop(key, None)
        if now < _circuit_until:
            return ""
        if DAILY_LIMIT > 0 and _usage_count >= DAILY_LIMIT:
            return ""
        _usage_count += 1

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

        text = response.choices[0].message.content.strip()
        with _lock:
            _failure_count = 0
            if text:
                _cache[key] = (time.monotonic(), text)
                _cache.move_to_end(key)
                while len(_cache) > CACHE_MAX_ENTRIES:
                    _cache.popitem(last=False)
        return text

    except Exception:
        with _lock:
            _failure_count += 1
            if _failure_count >= FAILURE_THRESHOLD:
                _circuit_until = time.monotonic() + CIRCUIT_SECONDS
        logger.exception("AI request failed for model %s", MODEL_NAME)
        return ""

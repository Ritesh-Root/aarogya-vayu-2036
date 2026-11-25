"""
Structured-JSON LLM calls for Aarogya-Vāyu.

Provider order:
  1) Google Gemini (primary) via the google-genai async client.
  2) Anthropic Claude (fallback) via the official anthropic SDK, used only when
     Gemini is unconfigured or fails.

Each call returns a validated Pydantic instance plus the provider label, or None
so callers can drop to their deterministic offline fallback.
"""

import os
import base64
import binascii
import time
import asyncio
from contextvars import ContextVar
import logging
from typing import Any, Dict, Optional, Tuple, Type, TypeVar

from pydantic import BaseModel

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)
# (raw bytes, mime type) of an image or audio clip sent alongside the prompt
Media = Tuple[bytes, str]

# `or` (not a getenv default) so an env var that exists but is empty still gets the default
GEMINI_MODELS = [
    os.getenv("DEFAULT_MODEL") or "gemini-3.8-flash",
    os.getenv("FALLBACK_MODEL") or "gemini-3.5-flash-lite",
]
CLAUDE_MODEL = os.getenv("CLAUDE_MODEL") or "claude-haiku-5-5"
LLM_ATTEMPT_TIMEOUT_S = float(os.getenv("LLM_ATTEMPT_TIMEOUT_S", "20"))  # long bilingual CMO answers take 10-15 s
# Overall budget across all attempts, so callers reach their offline fallback before a serverless timeout
LLM_TOTAL_BUDGET_S = float(os.getenv("LLM_TOTAL_BUDGET_S", "36"))
MAX_OUTPUT_TOKENS = 4096
# Optional per-request deadline (monotonic seconds) shared by every LLM call in that request
_request_deadline: ContextVar[Optional[float]] = ContextVar("llm_request_deadline", default=None)


def set_request_deadline(seconds: float) -> None:
    """Cap the total LLM time for the current request, so multi-call endpoints finish before the platform timeout."""
    _request_deadline.set(time.monotonic() + seconds)


def _budget() -> float:
    deadline = _request_deadline.get()
    if deadline is None:
        return LLM_TOTAL_BUDGET_S
    return max(0.5, min(LLM_TOTAL_BUDGET_S, deadline - time.monotonic()))

_gemini_client = None
_claude_client = None


def decode_media(data: str, mime_type: Any, default_mime: str, allowed: set, max_bytes: int, label: str) -> Media:
    """Decode raw base64 or a data URL into (bytes, mime); raises ValueError on bad input."""
    data = data if isinstance(data, str) else ""
    mime_type = mime_type if isinstance(mime_type, str) else None
    if data.startswith("data:"):
        header, _, data = data.partition(",")
        mime_type = header[5:].split(";")[0] or mime_type
    mime = (mime_type or default_mime).split(";")[0].strip().lower()
    if mime not in allowed:
        raise ValueError(f"Unsupported {label} type")
    if len(data) > max_bytes * 4 // 3 + 4:
        raise ValueError(f"{label.capitalize()} too large (max {max_bytes // (1024 * 1024)} MB)")
    try:
        raw = base64.b64decode(data, validate=True)
    except (binascii.Error, ValueError):
        raise ValueError(f"{label.capitalize()} is not valid base64")
    if not raw:
        raise ValueError(f"Empty {label}")
    return raw, mime


# ---- Global daily AI budget ----
# One always-on instance serves every visitor, so a process-wide counter is a real cap on paid model calls.
# When it is spent the app keeps working on its rule-based paths; speech and vision answer 429.
AI_DAILY_CALL_BUDGET = int(os.getenv("AI_DAILY_CALL_BUDGET", "1500"))
_IST = __import__("datetime").timezone(__import__("datetime").timedelta(hours=5, minutes=30))
_budget_state = {"day": None, "used": 0}
_budget_lock = __import__("threading").Lock()


def _today() -> str:
    return __import__("datetime").datetime.now(_IST).date().isoformat()


def _roll_day() -> None:
    day = _today()
    if _budget_state["day"] != day:
        _budget_state["day"], _budget_state["used"] = day, 0


def ai_budget_remaining() -> int:
    with _budget_lock:
        _roll_day()
        return max(0, AI_DAILY_CALL_BUDGET - _budget_state["used"])


def consume_ai_budget() -> bool:
    """Takes one call from today's budget; False when it is spent (resets at IST midnight)."""
    with _budget_lock:
        _roll_day()
        if _budget_state["used"] >= AI_DAILY_CALL_BUDGET:
            return False
        _budget_state["used"] += 1
        return True


def reset_ai_budget() -> None:
    with _budget_lock:
        _budget_state["day"], _budget_state["used"] = None, 0



def _gemini_key() -> Optional[str]:
    return os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY") or os.getenv("GOOGLE_GENAI_API_KEY")


def _vertex_mode() -> bool:
    """Cloud Run: Gemini through Vertex AI with the service account's own credentials (no API key)."""
    return os.getenv("GOOGLE_GENAI_USE_VERTEXAI", "").strip().lower() in ("1", "true", "yes")


def provider_status() -> dict:
    """Which providers have credentials configured (booleans only, never key material)."""
    return {
        "gemini": bool(_gemini_key()) or _vertex_mode(),
        "gemini_via": "vertex" if _vertex_mode() else ("api_key" if _gemini_key() else None),
        "claude": bool(os.getenv("ANTHROPIC_API_KEY")),
        "primary": "gemini",
        "gemini_model": GEMINI_MODELS[0],
        "claude_model": CLAUDE_MODEL,
    }


def _gemini():
    global _gemini_client
    if _gemini_client is None and _vertex_mode():
        from google import genai
        _gemini_client = genai.Client(vertexai=True, project=os.getenv("GOOGLE_CLOUD_PROJECT"),
                                      location=os.getenv("GOOGLE_CLOUD_LOCATION", "global"))
        return _gemini_client
    key = _gemini_key()
    if _gemini_client is None and key:
        from google import genai
        _gemini_client = genai.Client(api_key=key)
    return _gemini_client


def _claude():
    global _claude_client
    if _claude_client is None and os.getenv("ANTHROPIC_API_KEY"):
        import anthropic
        _claude_client = anthropic.AsyncAnthropic(timeout=LLM_ATTEMPT_TIMEOUT_S, max_retries=0)
    return _claude_client


async def _call_gemini(system: str, user: str, schema: Type[T], media: Optional[Media] = None) -> Optional[T]:
    if ai_budget_remaining() <= 0:
        return None
    try:
        client = _gemini()
        if not client:
            return None
        if not consume_ai_budget():
            return None
        from google.genai import types
    except Exception as e:
        logger.warning("Gemini client unavailable: %s", e)
        return None
    config = types.GenerateContentConfig(
        system_instruction=system,
        response_mime_type="application/json",
        response_schema=schema,
        max_output_tokens=MAX_OUTPUT_TOKENS,
        automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
    )
    contents = [types.Part.from_bytes(data=media[0], mime_type=media[1]), user] if media else user
    for model in GEMINI_MODELS:
        try:
            resp = await asyncio.wait_for(
                client.aio.models.generate_content(model=model, contents=contents, config=config),
                timeout=LLM_ATTEMPT_TIMEOUT_S,
            )
            if isinstance(resp.parsed, schema):
                return resp.parsed
            if resp.text:
                return schema.model_validate_json(resp.text)
        except asyncio.TimeoutError:
            logger.warning("Gemini %s timed out after %ss", model, LLM_ATTEMPT_TIMEOUT_S)
            # A slow Gemini is likely slow for every model; leave the budget for Claude, unless Claude can't read this media
            if _claude_can_read(media):
                break
        except Exception as e:
            logger.warning("Gemini %s call failed: %s", model, e)
    return None


def _claude_content(user: str, media: Optional[Media]):
    if not media:
        return user
    return [
        {"type": "image", "source": {"type": "base64", "media_type": media[1], "data": base64.b64encode(media[0]).decode()}},
        {"type": "text", "text": user},
    ]


def _claude_can_read(media: Optional[Media]) -> bool:
    return media is None or media[1].startswith("image/")  # Claude reads images but not audio


async def _call_claude(system: str, user: str, schema: Type[T], media: Optional[Media] = None) -> Optional[T]:
    if ai_budget_remaining() <= 0:
        return None
    if not _claude_can_read(media):
        return None
    try:
        client = _claude()
        if not client:
            return None
        if not consume_ai_budget():
            return None
        import anthropic
    except Exception as e:
        logger.warning("Claude client unavailable: %s", e)
        return None
    try:
        resp = await client.messages.parse(
            model=CLAUDE_MODEL,
            max_tokens=MAX_OUTPUT_TOKENS,
            system=system,
            messages=[{"role": "user", "content": _claude_content(user, media)}],
            output_format=schema,
        )
        if resp.stop_reason == "refusal":
            logger.warning("Claude refused request (request_id=%s)", resp._request_id)
            return None
        return resp.parsed_output
    except anthropic.APIStatusError as e:
        logger.warning("Claude API error %s: %s", e.status_code, e.message)
    except anthropic.APIConnectionError as e:
        logger.warning("Claude connection error: %s", e)
    except Exception as e:
        logger.warning("Claude response parse failed: %s", e)
    return None


async def _generate_json(system: str, user: str, schema: Type[T], media: Optional[Media] = None) -> Optional[Tuple[T, str]]:
    parsed = await _call_gemini(system, user, schema, media)
    if parsed is not None:
        return parsed, "gemini"
    parsed = await _call_claude(system, user, schema, media)
    if parsed is not None:
        return parsed, "claude"
    return None


async def generate_json(system: str, user: str, schema: Type[T], media: Optional[Media] = None) -> Optional[Tuple[T, str]]:
    """Gemini first, Claude as fallback. Returns (parsed, provider) or None."""
    try:
        return await asyncio.wait_for(_generate_json(system, user, schema, media), timeout=_budget())
    except asyncio.TimeoutError:
        logger.warning("LLM budget of %ss exhausted; using offline fallback", LLM_TOTAL_BUDGET_S)
        return None


async def _gemini_tool_call(system: str, user: str, name: str, description: str, parameters: dict) -> Optional[Dict[str, Any]]:
    if ai_budget_remaining() <= 0:
        return None
    try:
        client = _gemini()
        if not client:
            return None
        if not consume_ai_budget():
            return None
        from google.genai import types
    except Exception as e:
        logger.warning("Gemini client unavailable: %s", e)
        return None
    config = types.GenerateContentConfig(
        system_instruction=system,
        tools=[types.Tool(function_declarations=[
            types.FunctionDeclaration(name=name, description=description, parameters_json_schema=parameters)
        ])],
        tool_config=types.ToolConfig(function_calling_config=types.FunctionCallingConfig(
            mode=types.FunctionCallingConfigMode.ANY, allowed_function_names=[name]
        )),
        automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
    )
    for model in GEMINI_MODELS:
        try:
            resp = await asyncio.wait_for(
                client.aio.models.generate_content(model=model, contents=user, config=config),
                timeout=LLM_ATTEMPT_TIMEOUT_S,
            )
            for call in resp.function_calls or []:
                if call.name == name:
                    return dict(call.args or {})
        except asyncio.TimeoutError:
            logger.warning("Gemini %s tool call timed out after %ss", model, LLM_ATTEMPT_TIMEOUT_S)
            break
        except Exception as e:
            logger.warning("Gemini %s tool call failed: %s", model, e)
    return None


async def _claude_tool_call(system: str, user: str, name: str, description: str, parameters: dict) -> Optional[Dict[str, Any]]:
    if ai_budget_remaining() <= 0:
        return None
    try:
        client = _claude()
        if not client:
            return None
        if not consume_ai_budget():
            return None
        import anthropic
    except Exception as e:
        logger.warning("Claude client unavailable: %s", e)
        return None
    try:
        resp = await client.messages.create(
            model=CLAUDE_MODEL,
            max_tokens=1024,
            system=system,
            tools=[{"name": name, "description": description, "input_schema": parameters}],
            tool_choice={"type": "tool", "name": name},
            messages=[{"role": "user", "content": user}],
        )
        for block in resp.content:
            if block.type == "tool_use" and block.name == name:
                return dict(block.input)
    except anthropic.APIError as e:
        logger.warning("Claude tool call failed: %s", e)
    return None


async def _tool_call(system: str, user: str, name: str, description: str, parameters: dict) -> Optional[Tuple[Dict[str, Any], str]]:
    args = await _gemini_tool_call(system, user, name, description, parameters)
    if args is not None:
        return args, "gemini"
    args = await _claude_tool_call(system, user, name, description, parameters)
    if args is not None:
        return args, "claude"
    return None


async def call_tool(system: str, user: str, name: str, description: str, parameters: dict) -> Optional[Tuple[Dict[str, Any], str]]:
    """Force the model to call one declared function; returns (arguments, provider) or None. Gemini first, Claude fallback."""
    try:
        return await asyncio.wait_for(_tool_call(system, user, name, description, parameters), timeout=_budget())
    except asyncio.TimeoutError:
        logger.warning("LLM tool-call budget of %ss exhausted", LLM_TOTAL_BUDGET_S)
        return None

"""LLM provider abstraction (OpenAI or Google Gemini), selected by LLM_PROVIDER.

Both providers expose:
  complete(system, user)                         -> str
  run_tools(system, question, tools, executor)   -> (answer, [tool call log])
The NullProvider is used when no provider / key is configured; callers must then use deterministic fallbacks.
"""
import json
import logging
import threading
import time
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional, Tuple

from backend.app.core.config import settings

logger = logging.getLogger("urban_planning_dss")


@dataclass
class ToolSpec:
    name: str
    description: str
    parameters: Dict[str, Any]  # JSON schema (type: object)


Executor = Callable[[str, Dict[str, Any]], Dict[str, Any]]


class LLMUnavailable(RuntimeError):
    """Raised when every model is overloaded / out of quota, or the local call budget is spent."""


class CallBudget:
    """Sliding-window limiter so a free-tier key is not exhausted by one busy session."""

    def __init__(self, per_minute: int):
        self.per_minute = max(1, per_minute)
        self.calls: List[float] = []
        self.lock = threading.Lock()

    def acquire(self) -> None:
        with self.lock:
            now = time.monotonic()
            self.calls = [t for t in self.calls if now - t < 60]
            if len(self.calls) >= self.per_minute:
                wait = 60 - (now - self.calls[0])
                raise LLMUnavailable(f"Local LLM budget of {self.per_minute} calls/min reached; retry in {wait:.0f}s")
            self.calls.append(now)

    def usage(self) -> Dict[str, int]:
        now = time.monotonic()
        return {"calls_last_minute": len([t for t in self.calls if now - t < 60]), "limit_per_minute": self.per_minute}


class LLMProvider:
    name = "none"
    model = ""
    available = False

    def complete(self, system: str, user: str, max_tokens: int = 600) -> Optional[str]:
        return None

    def run_tools(self, system: str, question: str, tools: List[ToolSpec], executor: Executor,
                  max_steps: int = 5) -> Tuple[Optional[str], List[Dict[str, Any]]]:
        return None, []


class NullProvider(LLMProvider):
    pass


def _json_for_model(result: Dict[str, Any], limit: int = 12000) -> str:
    text = json.dumps(result, default=str)
    return text if len(text) <= limit else text[:limit] + "…(truncated)"


class OpenAIProvider(LLMProvider):
    name = "openai"

    def __init__(self, api_key: str, model: str):
        from openai import OpenAI
        self.client = OpenAI(api_key=api_key, timeout=settings.LLM_TIMEOUT_SECONDS)
        self.model = model
        self.available = True

    def complete(self, system, user, max_tokens=600):
        resp = self.client.chat.completions.create(
            model=self.model, max_tokens=max_tokens, temperature=0.2,
            messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
        )
        return resp.choices[0].message.content

    def run_tools(self, system, question, tools, executor, max_steps=5):
        tool_defs = [{"type": "function", "function": {"name": t.name, "description": t.description,
                                                       "parameters": t.parameters}} for t in tools]
        messages: List[Dict[str, Any]] = [{"role": "system", "content": system}, {"role": "user", "content": question}]
        log: List[Dict[str, Any]] = []
        for _ in range(max_steps):
            resp = self.client.chat.completions.create(model=self.model, messages=messages, tools=tool_defs,
                                                       temperature=0.1, max_tokens=900)
            msg = resp.choices[0].message
            if not msg.tool_calls:
                return msg.content, log
            messages.append({"role": "assistant", "content": msg.content or "",
                             "tool_calls": [tc.model_dump() for tc in msg.tool_calls]})
            for tc in msg.tool_calls:
                try:
                    args = json.loads(tc.function.arguments or "{}")
                except json.JSONDecodeError:
                    args = {}
                result = executor(tc.function.name, args)
                log.append({"tool": tc.function.name, "arguments": args, "result": result})
                messages.append({"role": "tool", "tool_call_id": tc.id, "content": _json_for_model(result)})
        # Step budget exhausted: ask for a final answer without tools
        messages.append({"role": "user", "content": "Answer now using only the tool results above."})
        resp = self.client.chat.completions.create(model=self.model, messages=messages, temperature=0.1, max_tokens=700)
        return resp.choices[0].message.content, log


class GeminiProvider(LLMProvider):
    """Google Gemini via google-genai. Falls back across models on 503 (overloaded) / 429 (quota) and enforces a
    local per-minute call budget to stay inside free-tier limits."""
    name = "gemini"

    def __init__(self, api_key: str, model: str, fallbacks: Optional[List[str]] = None, per_minute: int = 8):
        from google import genai
        from google.genai import types
        self.types = types
        self.client = genai.Client(api_key=api_key,
                                   http_options=types.HttpOptions(timeout=int(settings.LLM_TIMEOUT_SECONDS * 1000)))
        self.models = [model] + [m for m in (fallbacks or []) if m != model]
        self.model = model
        self.budget = CallBudget(per_minute)
        self.available = True

    def _generate(self, contents, config):
        """One logical call: tries each model in turn on transient / quota errors."""
        from google.genai import errors
        self.budget.acquire()
        last = None
        for m in self.models:
            try:
                resp = self.client.models.generate_content(model=m, contents=contents, config=config)
                self.model = m
                return resp
            except errors.APIError as exc:
                last = exc
                code = getattr(exc, "code", None)
                if code in (404, 429, 500, 503, 504) or code is None:  # 404 = model retired
                    logger.warning("Gemini %s failed (%s); trying next model", m, code)
                    continue
                raise
        raise LLMUnavailable(f"All Gemini models unavailable: {str(last)[:200] if last else 'unknown error'}")

    def complete(self, system, user, max_tokens=600):
        t = self.types
        resp = self._generate(user, t.GenerateContentConfig(system_instruction=system, max_output_tokens=max_tokens, temperature=0.2))
        return resp.text

    def run_tools(self, system, question, tools, executor, max_steps=5):
        t = self.types
        decls = [t.FunctionDeclaration(name=s.name, description=s.description, parameters=s.parameters) for s in tools]
        config = t.GenerateContentConfig(
            system_instruction=system, temperature=0.1, max_output_tokens=1200,
            tools=[t.Tool(function_declarations=decls)],
            automatic_function_calling=t.AutomaticFunctionCallingConfig(disable=True),
        )
        contents = [t.Content(role="user", parts=[t.Part(text=question)])]
        log: List[Dict[str, Any]] = []
        for _ in range(max_steps):
            resp = self._generate(contents, config)
            calls = resp.function_calls or []
            if not calls:
                return resp.text, log
            contents.append(resp.candidates[0].content)  # keeps thought signatures for thinking models
            parts = []
            for call in calls:
                args = dict(call.args or {})
                result = executor(call.name, args)
                log.append({"tool": call.name, "arguments": args, "result": result})
                raw = json.dumps(result, default=str)
                payload = {"result": json.loads(raw)} if len(raw) <= 12000 else {"result_truncated": _json_for_model(result)}
                parts.append(t.Part.from_function_response(name=call.name, response=payload))
            contents.append(t.Content(role="user", parts=parts))  # Gemini expects function responses in a user turn
        contents.append(t.Content(role="user", parts=[t.Part(text="Answer now using only the tool results above.")]))
        resp = self._generate(contents, t.GenerateContentConfig(system_instruction=system, temperature=0.1, max_output_tokens=900))
        return resp.text, log


_llm: Optional[LLMProvider] = None


def get_llm() -> LLMProvider:
    global _llm
    if _llm is not None:
        return _llm
    provider = (settings.LLM_PROVIDER or "none").lower()
    try:
        if provider == "openai" and settings.OPENAI_API_KEY:
            _llm = OpenAIProvider(settings.OPENAI_API_KEY, settings.OPENAI_MODEL)
        elif provider == "gemini" and settings.GEMINI_API_KEY:
            _llm = GeminiProvider(settings.GEMINI_API_KEY, settings.GEMINI_MODEL, settings.GEMINI_FALLBACK_MODELS,
                                  settings.LLM_MAX_CALLS_PER_MINUTE)
        else:
            if provider not in ("none", ""):
                logger.warning("LLM_PROVIDER=%s but no API key configured; using rule-based fallback.", provider)
            _llm = NullProvider()
    except Exception as exc:  # SDK missing or misconfigured
        logger.warning("Could not initialise LLM provider %s (%s); using rule-based fallback.", provider, exc)
        _llm = NullProvider()
    return _llm


def set_llm(provider: Optional[LLMProvider]) -> None:
    """Override the provider (used by tests)."""
    global _llm
    _llm = provider

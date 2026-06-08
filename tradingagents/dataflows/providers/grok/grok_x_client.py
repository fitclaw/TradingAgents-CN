#!/usr/bin/env python3
"""Grok/X data source adapter (standalone; NOT wired into the analysis chain).

Uses the xAI Grok API (OpenAI-compatible chat completions + live X search) to
fetch and structure public market signals from X (Twitter).

Intended capability: news / social / macro *leads* only — never price/quote/
fundamental facts.

This module is deliberately self-contained:
  * it is NOT registered in any analyst toolchain, fallback, or data-source registry;
  * it can be unit-tested with mocked HTTP.
Wiring it into the analysis chain is an intentional later step.

The live-search request shape reflects xAI's documented API; it may need minor
adjustment when first validated against a real ``XAI_API_KEY``.
"""
from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Sequence

try:  # pragma: no cover - prefer project logger when available
    from tradingagents.utils.logging_init import get_logger

    logger = get_logger("default")
except Exception:  # pragma: no cover - lightweight fallback
    import logging

    logger = logging.getLogger("grok_x")

DEFAULT_BASE_URL = "https://api.x.ai/v1"
DEFAULT_MODEL = "grok-2-latest"
ENV_API_KEY = "XAI_API_KEY"
ENV_BASE_URL = "XAI_BASE_URL"
ENV_MODEL = "XAI_GROK_MODEL"

SUPPORTED_CATEGORIES = ("news", "social", "macro")
VALID_SENTIMENTS = ("positive", "negative", "neutral")


def _is_valid_api_key(api_key: Optional[str]) -> bool:
    """Reject empty / too-short / placeholder / truncated API keys.

    Mirrors ``app.utils.api_key_utils.is_valid_api_key`` (kept local to avoid a
    ``tradingagents`` -> ``app`` import; the llm_adapters in this package follow
    the same replicate-locally convention). Notably treats the ``.env.example``
    placeholder ``your_xai_api_key_here`` (your_*/*_here) as NOT configured, so a
    user who copies the template unchanged gets a clear local error instead of an
    opaque HTTP 401 from xAI.
    """
    if not api_key:
        return False
    key = str(api_key).strip()
    if len(key) <= 10:
        return False
    if key.startswith("your_") or key.startswith("your-"):
        return False
    if key.endswith("_here") or key.endswith("-here"):
        return False
    if "..." in key:
        return False
    return True


class GrokXError(RuntimeError):
    """Raised when the Grok/X adapter cannot produce a usable result."""


@dataclass
class GrokXSignal:
    """One structured signal extracted from X public information."""

    title: str
    summary: str
    category: str  # news | social | macro
    sentiment: Optional[str] = None  # positive | negative | neutral
    url: Optional[str] = None
    author: Optional[str] = None
    published_at: Optional[str] = None  # ISO8601
    source: str = "grok_x"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class GrokXClient:
    """Thin, testable client over the xAI Grok API for X public-info retrieval."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
        timeout: int = 30,
        session: Any = None,
    ) -> None:
        self.api_key = api_key if api_key is not None else os.getenv(ENV_API_KEY)
        self.base_url = (base_url or os.getenv(ENV_BASE_URL) or DEFAULT_BASE_URL).rstrip("/")
        self.model = model or os.getenv(ENV_MODEL) or DEFAULT_MODEL
        self.timeout = timeout
        self._session = session  # injectable for tests

    def is_configured(self) -> bool:
        """Whether a usable, non-placeholder API key is present (dedicated XAI_API_KEY)."""
        return _is_valid_api_key(self.api_key)

    @staticmethod
    def _normalize_categories(categories: Sequence[str]) -> List[str]:
        if not categories:
            raise GrokXError("categories must not be empty")
        normalized: List[str] = []
        for c in categories:
            key = str(c).strip().lower()
            if key not in SUPPORTED_CATEGORIES:
                raise GrokXError(
                    f"Unsupported category: {c!r}; supported={SUPPORTED_CATEGORIES}"
                )
            if key not in normalized:
                normalized.append(key)
        return normalized

    def fetch_x_signals(
        self,
        query: str,
        *,
        categories: Sequence[str] = ("news", "social"),
        time_window_hours: int = 24,
        limit: int = 20,
        now: Optional[datetime] = None,
    ) -> List[Dict[str, Any]]:
        """Fetch structured X signals for ``query``.

        Returns a list of plain dicts (see :class:`GrokXSignal`). Raises
        :class:`GrokXError` on misconfiguration, bad input, or unparseable output.
        """
        if not str(query or "").strip():
            raise GrokXError("query must not be empty")
        if not self.is_configured():
            raise GrokXError(
                f"{ENV_API_KEY} missing or placeholder; set a real key to call xAI Grok API"
            )

        cats = self._normalize_categories(categories)
        limit = max(1, int(limit))
        messages = self._build_messages(query, cats, time_window_hours, limit)
        payload = self._build_payload(messages, time_window_hours, limit, now=now)
        raw = self._call_api(payload)
        signals = self._parse_response(raw, allowed_categories=cats, limit=limit)
        logger.info(f"🐦 [Grok/X] query={query!r} -> {len(signals)} signals ({cats})")
        return [s.to_dict() for s in signals]

    def _build_messages(
        self, query: str, categories: Sequence[str], time_window_hours: int, limit: int
    ) -> List[Dict[str, str]]:
        system = (
            "You are a market-intelligence assistant that searches X (Twitter) for "
            "recent, credible public posts and returns STRICTLY a JSON object. "
            "Report only news/social/macro leads; never fabricate prices, quotes, or "
            "financial facts."
        )
        user = (
            f"Find up to {limit} recent X signals about: {query}.\n"
            f"Time window: last {time_window_hours} hours.\n"
            f"Allowed categories: {', '.join(categories)}.\n"
            'Return JSON of shape {"signals":[{"title","summary","category",'
            '"sentiment","url","author","published_at"}]}. '
            "category must be one of the allowed categories; sentiment one of "
            "positive/negative/neutral; published_at in ISO8601. "
            'If nothing relevant, return {"signals":[]}.'
        )
        return [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ]

    def _build_payload(
        self,
        messages: List[Dict[str, str]],
        time_window_hours: int,
        limit: int,
        now: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        ref = now or datetime.now(timezone.utc)
        from_dt = ref - timedelta(hours=max(1, int(time_window_hours)))
        return {
            "model": self.model,
            "messages": messages,
            "temperature": 0,
            "response_format": {"type": "json_object"},
            # xAI live search over X
            "search_parameters": {
                "mode": "on",
                "sources": [{"type": "x"}],
                "from_date": from_dt.date().isoformat(),
                "to_date": ref.date().isoformat(),
                "max_search_results": min(max(1, int(limit)), 30),
            },
        }

    def _call_api(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        import requests

        url = f"{self.base_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        try:
            session = self._session or requests
            resp = session.post(url, headers=headers, json=payload, timeout=self.timeout)
            resp.raise_for_status()
            return resp.json()
        except Exception as e:  # noqa: BLE001 - surface as adapter error
            raise GrokXError(f"xAI Grok API request failed: {e}") from e

    def _parse_response(
        self, raw: Dict[str, Any], *, allowed_categories: Sequence[str], limit: int
    ) -> List[GrokXSignal]:
        content = self._extract_content(raw)
        data = self._loads_json(content)
        items = data.get("signals") if isinstance(data, dict) else None
        if not isinstance(items, list):
            raise GrokXError("Unexpected response shape: missing 'signals' list")

        allowed = set(allowed_categories)
        out: List[GrokXSignal] = []
        for item in items:
            if not isinstance(item, dict):
                continue
            title = str(item.get("title") or "").strip()
            summary = str(item.get("summary") or "").strip()
            category = str(item.get("category") or "").strip().lower()
            if category not in allowed:
                continue
            if not title and not summary:
                continue
            sentiment = str(item.get("sentiment") or "").strip().lower() or None
            if sentiment not in VALID_SENTIMENTS:
                sentiment = None
            out.append(
                GrokXSignal(
                    title=title or summary[:80],
                    summary=summary,
                    category=category,
                    sentiment=sentiment,
                    url=_clean_optional(item.get("url")),
                    author=_clean_optional(item.get("author")),
                    published_at=_clean_optional(item.get("published_at")),
                )
            )
            if len(out) >= limit:
                break
        return out

    @staticmethod
    def _extract_content(raw: Dict[str, Any]) -> str:
        try:
            return raw["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as e:
            raise GrokXError(
                f"Unexpected API response: cannot find message content ({e})"
            ) from e

    @staticmethod
    def _loads_json(content: Any) -> Any:
        text = str(content or "").strip()
        if text.startswith("```"):
            text = text.strip("`")
            if text[:4].lower() == "json":
                text = text[4:]
            text = text.strip()
        try:
            return json.loads(text)
        except json.JSONDecodeError as e:
            raise GrokXError(f"Grok response is not valid JSON: {e}") from e


def _clean_optional(value: Any) -> Optional[str]:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def fetch_grok_x_signals(query: str, **kwargs: Any) -> List[Dict[str, Any]]:
    """Convenience wrapper using env-configured credentials (XAI_API_KEY)."""
    return GrokXClient().fetch_x_signals(query, **kwargs)

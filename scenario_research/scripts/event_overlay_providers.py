"""Provider adapters for Phase 5 unstructured event extraction."""
from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from pathlib import Path

try:
    from .event_overlay_engine import PROVIDER_EVENT_SCHEMA, load_event_input
except ImportError:
    from event_overlay_engine import PROVIDER_EVENT_SCHEMA, load_event_input


class EventProviderError(RuntimeError):
    pass


class FixtureEventProvider:
    name = "fixture"
    requires_api_key = False
    api_key_env = None
    live_research_attached = False
    model_name = None

    def __init__(self, input_path: Path):
        self.input_path = Path(input_path)

    def load_events(self) -> list[dict[str, object]]:
        return [dict(row) for row in load_event_input(self.input_path)]


GEMINI_EVENT_RESPONSE_SCHEMA = {
    "type": "object",
    "properties": {
        "events": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "date": {"type": "string", "description": "Event publication or effective date in YYYY-MM-DD format."},
                    "source": {"type": "string", "description": "Source name or provider label."},
                    "title": {"type": "string", "description": "Short event headline."},
                    "url_or_ref": {"type": "string", "description": "URL, citation, or source reference if available."},
                    "event_type": {"type": "string", "enum": PROVIDER_EVENT_SCHEMA["enums"]["event_type"]},
                    "region": {"type": "string", "enum": PROVIDER_EVENT_SCHEMA["enums"]["region"]},
                    "affected_assets": {"type": "string", "description": "Pipe-separated tickers, sectors, asset classes, or countries."},
                    "direction": {"type": "string", "enum": PROVIDER_EVENT_SCHEMA["enums"]["direction"]},
                    "severity": {"type": "number", "minimum": 0, "maximum": 100},
                    "novelty": {"type": "number", "minimum": 0, "maximum": 100},
                    "time_horizon": {"type": "string", "enum": PROVIDER_EVENT_SCHEMA["enums"]["time_horizon"]},
                    "scenario_links": {
                        "type": "array",
                        "items": {"type": "string", "enum": PROVIDER_EVENT_SCHEMA["enums"]["scenario_links"]},
                    },
                    "evidence_span": {"type": "string", "description": "Short quote or compact paraphrase supporting the classification."},
                    "extract_confidence": {"type": "number", "minimum": 0, "maximum": 100},
                },
                "required": ["date", "source", "title", "event_type", "region", "direction", "severity", "novelty", "time_horizon", "scenario_links", "evidence_span", "extract_confidence"],
            },
        }
    },
    "required": ["events"],
}


class GeminiEventProvider:
    name = "gemini"
    requires_api_key = True
    api_key_env = "GEMINI_API_KEY"
    live_research_attached = True

    def __init__(
        self,
        input_path: Path | None = None,
        api_key_env: str | None = None,
        model_name: str | None = None,
        timeout_seconds: int = 60,
        request_fn=None,
    ):
        self.input_path = Path(input_path) if input_path else None
        self.api_key_env = api_key_env or self.api_key_env
        self.model_name = model_name or os.environ.get("GEMINI_EVENT_MODEL") or "gemini-2.5-flash"
        self.timeout_seconds = timeout_seconds
        self._request_fn = request_fn or post_json

    def load_events(self) -> list[dict[str, object]]:
        api_key = os.environ.get(self.api_key_env or "")
        if not api_key:
            raise EventProviderError(
                f"Gemini provider requires {self.api_key_env}. "
                "Set the API key or use --provider fixture for reviewed local inputs."
            )
        if not self.input_path:
            raise EventProviderError("Gemini provider requires an input file containing source events or article text.")

        source_rows = [dict(row) for row in load_event_input(self.input_path)]
        if not source_rows:
            return []

        payload = {
            "contents": [
                {
                    "parts": [
                        {
                            "text": build_gemini_event_prompt(source_rows),
                        }
                    ]
                }
            ],
            "generationConfig": {
                "responseMimeType": "application/json",
                "responseJsonSchema": GEMINI_EVENT_RESPONSE_SCHEMA,
            },
        }
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model_name}:generateContent"
        response = self._request_fn(
            url,
            payload,
            {"Content-Type": "application/json", "x-goog-api-key": api_key},
            self.timeout_seconds,
        )
        rows = parse_gemini_event_response(response)
        for row in rows:
            row.setdefault("source", "gemini")
            if isinstance(row.get("scenario_links"), list):
                row["scenario_links"] = "|".join(str(item) for item in row["scenario_links"] if item)
        return rows


def build_gemini_event_prompt(source_rows: list[dict[str, object]]) -> str:
    compact_rows = []
    for idx, row in enumerate(source_rows, start=1):
        compact_rows.append(
            {
                "id": idx,
                "date": row.get("date") or row.get("published_at") or row.get("as_of_date") or "",
                "source": row.get("source") or row.get("publisher") or row.get("provider") or "",
                "title": row.get("title") or row.get("headline") or "",
                "url_or_ref": row.get("url_or_ref") or row.get("url") or row.get("ref") or "",
                "body": row.get("body") or row.get("text") or row.get("summary") or row.get("evidence_span") or "",
            }
        )
    return (
        "Extract market event overlay rows for a hedge recommendation research system. "
        "Classify only events supported by the supplied source text. "
        "Use the provided scenario code enum exactly, use 0-100 numeric severity/novelty/confidence, "
        "and return JSON only in the requested schema. Source rows:\n"
        f"{json.dumps(compact_rows, ensure_ascii=False, indent=2)}"
    )


def post_json(url: str, payload: dict[str, object], headers: dict[str, str], timeout_seconds: int) -> dict[str, object]:
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    request = urllib.request.Request(url, data=data, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise EventProviderError(f"Gemini provider HTTP {exc.code}: {detail[:500]}") from exc
    except urllib.error.URLError as exc:
        raise EventProviderError(f"Gemini provider request failed: {exc.reason}") from exc
    except json.JSONDecodeError as exc:
        raise EventProviderError(f"Gemini provider returned invalid JSON: {exc}") from exc


def parse_gemini_event_response(response: dict[str, object]) -> list[dict[str, object]]:
    try:
        candidates = response["candidates"]
        parts = candidates[0]["content"]["parts"]
        text = "".join(str(part.get("text") or "") for part in parts)
    except (KeyError, IndexError, TypeError, AttributeError) as exc:
        raise EventProviderError("Gemini provider response did not include candidate text.") from exc
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError as exc:
        raise EventProviderError(f"Gemini provider candidate text was not valid JSON: {exc}") from exc
    if isinstance(parsed, list):
        events = parsed
    elif isinstance(parsed, dict):
        events = parsed.get("events")
    else:
        events = None
    if not isinstance(events, list):
        raise EventProviderError("Gemini provider JSON must contain an events array.")
    if not all(isinstance(row, dict) for row in events):
        raise EventProviderError("Gemini provider events must be objects.")
    return [dict(row) for row in events]


def build_event_provider(provider_name: str, input_path: Path):
    provider = (provider_name or "fixture").strip().lower()
    if provider == "fixture":
        return FixtureEventProvider(input_path)
    if provider == "gemini":
        return GeminiEventProvider(input_path)
    raise EventProviderError(f"Unsupported event provider: {provider_name}")

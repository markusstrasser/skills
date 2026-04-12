from __future__ import annotations

import hashlib
import importlib.metadata
import json
import os
import re
import sys
import traceback
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any, Callable


HELPER_VERSION = "2026-04-10-v1"
DEFAULT_TELEMETRY_PATH = Path(__file__).resolve().parents[1] / ".claude" / "telemetry" / "llm-dispatch.jsonl"

STATUS_EXIT_CODES = {
    "ok": 0,
    "timeout": 10,
    "rate_limit": 11,
    "quota": 12,
    "model_error": 13,
    "schema_error": 14,
    "parse_error": 15,
    "empty_output": 16,
    "config_error": 17,
    "dependency_error": 18,
    "dispatch_error": 19,
}

RETRYABLE_STATUSES = {
    "ok": False,
    "timeout": True,
    "rate_limit": True,
    "quota": False,
    "model_error": False,
    "schema_error": False,
    "parse_error": False,
    "empty_output": True,
    "config_error": False,
    "dependency_error": False,
    "dispatch_error": False,
}

_LLMX_CHAT: Callable[..., Any] | None = None
_LLMX_VERSION: str | None = None


@dataclass(frozen=True)
class DispatchProfile:
    name: str
    intent: str
    provider: str
    model: str
    timeout: int
    reasoning_effort: str | None = None
    max_tokens: int | None = None
    input_token_limit: int | None = None
    input_token_estimator: str = "heuristic:chars_div_4"
    search: bool = False
    api_only: bool = True
    allowed_overrides: tuple[str, ...] = ("timeout", "reasoning_effort", "max_tokens", "search")
    version: str = "v1"

    def fingerprint(self) -> str:
        payload = json.dumps(asdict(self), sort_keys=True, separators=(",", ":")).encode("utf-8")
        return hashlib.sha256(payload).hexdigest()[:16]


PROFILES: dict[str, DispatchProfile] = {
    "fast_extract": DispatchProfile(
        name="fast_extract",
        intent="Low-cost extraction, triage, and short synthesis",
        provider="google",
        model="gemini-3-flash-preview",
        timeout=180,
        input_token_limit=900000,
    ),
    "deep_review": DispatchProfile(
        name="deep_review",
        intent="Long-context structural critique and review",
        provider="google",
        model="gemini-3.1-pro-preview",
        timeout=300,
        reasoning_effort="high",
        input_token_limit=900000,
    ),
    "formal_review": DispatchProfile(
        name="formal_review",
        intent="Formal or quantitative GPT-backed review",
        provider="openai",
        model="gpt-5.4",
        timeout=600,
        reasoning_effort="high",
        max_tokens=32768,
        input_token_limit=120000,
    ),
    "gpt_general": DispatchProfile(
        name="gpt_general",
        intent="General-purpose GPT-backed dispatch",
        provider="openai",
        model="gpt-5.4",
        timeout=600,
        reasoning_effort="medium",
        max_tokens=16384,
        input_token_limit=120000,
    ),
    "search_grounded": DispatchProfile(
        name="search_grounded",
        intent="Search-backed answer synthesis",
        provider="google",
        model="gemini-3.1-pro-preview",
        timeout=300,
        search=True,
        input_token_limit=900000,
    ),
    "cheap_tick": DispatchProfile(
        name="cheap_tick",
        intent="Low-cost maintenance or cycle tick synthesis",
        provider="google",
        model="gemini-3-flash-preview",
        timeout=120,
        input_token_limit=900000,
    ),
}

MODEL_TO_PROFILE = {
    "gemini-3-flash-preview": "fast_extract",
    "gemini-3.1-pro-preview": "deep_review",
    "gpt-5.4": "gpt_general",
}


@dataclass
class DispatchOverrides:
    timeout: int | None = None
    reasoning_effort: str | None = None
    max_tokens: int | None = None
    search: bool | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            key: value
            for key, value in asdict(self).items()
            if value is not None
        }


@dataclass
class DispatchResult:
    status: str
    retryable: bool
    requested_profile: str
    profile_version: str
    profile_fingerprint: str
    provider: str
    model: str
    output_path: str
    meta_path: str
    error_path: str | None
    parsed_path: str | None
    latency: float
    llmx_version: str
    helper_version: str
    error_type: str | None = None
    error_message: str | None = None

    @property
    def exit_code(self) -> int:
        return STATUS_EXIT_CODES[self.status]


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _temperature_for_model(model: str) -> float:
    return 1.0 if any(token in model for token in ("gpt-5", "gemini-3", "kimi-k2")) else 0.7


def _strip_markdown_fences(text: str) -> str:
    stripped = text.strip()
    if stripped.startswith("```"):
        stripped = re.sub(r"^```(?:json)?\s*\n?", "", stripped)
        stripped = re.sub(r"\n?```\s*$", "", stripped)
    return stripped


def _atomic_write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with NamedTemporaryFile("w", dir=path.parent, prefix=f".{path.name}.", suffix=".tmp", delete=False) as handle:
        handle.write(content)
        temp_name = handle.name
    os.replace(temp_name, path)


def _atomic_write_json(path: Path, payload: dict[str, Any]) -> None:
    _atomic_write_text(path, json.dumps(payload, indent=2, sort_keys=True) + "\n")


def _append_jsonl(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a") as handle:
        handle.write(json.dumps(payload, sort_keys=True) + "\n")


def _telemetry_path() -> Path:
    override = os.environ.get("LLM_DISPATCH_TELEMETRY_PATH")
    if override:
        return Path(override).expanduser()
    return DEFAULT_TELEMETRY_PATH


def _extract_usage(response: Any) -> dict[str, Any] | None:
    usage = getattr(response, "usage", None)
    if usage is None:
        return None
    if isinstance(usage, dict):
        return usage
    try:
        return dict(usage)
    except Exception:
        return None


def _write_telemetry(payload: dict[str, Any]) -> None:
    try:
        _append_jsonl(_telemetry_path(), payload)
    except Exception:
        pass


def _remove_if_exists(path: Path | None) -> None:
    if path and path.exists():
        path.unlink()


def _bootstrap_llmx() -> tuple[Callable[..., Any], str]:
    global _LLMX_CHAT, _LLMX_VERSION
    cached_chat = _LLMX_CHAT
    if cached_chat is not None:
        return cached_chat, _LLMX_VERSION or "unknown"

    # Phase 1: try direct import (works if llmx is installed in current venv).
    llmx_chat: Callable[..., Any] | None = None
    try:
        from llmx.api import chat as _llmx_chat  # type: ignore
        llmx_chat = _llmx_chat
    except ImportError:
        # Phase 2: fall back to the uv tool install. CRITICAL: must match the
        # current Python's major.minor version, otherwise we'd add a
        # site-packages dir whose compiled C extensions (e.g.
        # pydantic_core._pydantic_core.cpython-313-darwin.so) cannot be loaded
        # by the current interpreter, producing a cryptic
        # `ModuleNotFoundError: No module named 'pydantic_core._pydantic_core'`
        # at import time.
        #
        # Diagnosed 2026-04-11: phenome `uv run python3 model-review.py` ran
        # under phenome's venv Python 3.12, but the previous fallback used
        # `glob` to pick up the llmx tool install's python3.13 site-packages.
        # Result: 3.13 .so files imported into a 3.12 process, cryptic crash.
        #
        # We also do NOT fall back to ~/Projects/llmx local editable source.
        # That path can SEEM to work (it's pure Python at the entry point) but
        # llmx's runtime deps (openai, pydantic, etc.) still need to be in the
        # current venv, and they typically aren't, so the local-source fallback
        # produces a different cryptic crash one import deeper. Cleaner to
        # raise here with an actionable error message.
        py_ver = f"python{sys.version_info.major}.{sys.version_info.minor}"
        matching_site = Path.home() / ".local/share/uv/tools/llmx/lib" / py_ver / "site-packages"
        if not matching_site.is_dir():
            tool_root = Path.home() / ".local/share/uv/tools/llmx/lib"
            installed_pys = sorted(p.name for p in tool_root.glob("python*")) if tool_root.is_dir() else []
            raise ImportError(
                f"llmx not importable in current Python ({py_ver}). "
                f"The llmx uv tool install at {tool_root} has versions: "
                f"{installed_pys or '(none)'}. "
                f"To fix: either (1) `uv pip install llmx` in the current venv, or "
                f"(2) re-run this script with a Python matching one of the installed "
                f"tool versions (e.g., {installed_pys[0] if installed_pys else 'python3.13'})."
            )
        # Add the site-packages dir. Also process .pth files (editable installs
        # use _llmx.pth → ~/Projects/llmx/; sys.path.insert alone ignores .pth).
        import site
        site.addsitedir(str(matching_site))
        try:
            from llmx.api import chat as _llmx_chat_2  # type: ignore
            llmx_chat = _llmx_chat_2
        except ImportError as exc:
            raise ImportError(
                f"llmx tool install at {matching_site} could not be imported: {exc}. "
                f"The Python version matched but a runtime dependency is missing or "
                f"corrupted. Try `uv tool install --reinstall llmx`."
            ) from exc

    assert llmx_chat is not None  # both branches above set or raise
    _LLMX_CHAT = llmx_chat

    # Resolve version string. Falls back gracefully if metadata is missing
    # (e.g., when loaded from a path-injected source rather than an installed
    # distribution).
    try:
        _LLMX_VERSION = importlib.metadata.version("llmx")
    except importlib.metadata.PackageNotFoundError:
        local_version = Path.home() / "Projects" / "llmx" / "pyproject.toml"
        if local_version.exists():
            text = local_version.read_text()
            match = re.search(r'^version\s*=\s*"([^"]+)"', text, re.MULTILINE)
            _LLMX_VERSION = match.group(1) if match else "unknown"
        else:
            _LLMX_VERSION = "unknown"

    return llmx_chat, _LLMX_VERSION or "unknown"


def _add_additional_properties(schema: dict[str, Any]) -> dict[str, Any]:
    import copy

    transformed = copy.deepcopy(schema)

    def walk(obj: dict[str, Any]) -> None:
        if obj.get("type") == "object":
            obj["additionalProperties"] = False
        for value in obj.values():
            if isinstance(value, dict):
                walk(value)
            elif isinstance(value, list):
                for item in value:
                    if isinstance(item, dict):
                        walk(item)

    walk(transformed)
    return transformed


def _strip_additional_properties(schema: dict[str, Any]) -> dict[str, Any]:
    import copy

    transformed = copy.deepcopy(schema)

    def walk(obj: dict[str, Any]) -> None:
        obj.pop("additionalProperties", None)
        for value in obj.values():
            if isinstance(value, dict):
                walk(value)
            elif isinstance(value, list):
                for item in value:
                    if isinstance(item, dict):
                        walk(item)

    walk(transformed)
    return transformed


def provider_response_schema(provider: str, schema: dict[str, Any] | None) -> dict[str, Any] | None:
    if schema is None:
        return None
    if provider == "openai":
        return _add_additional_properties(schema)
    return _strip_additional_properties(schema)


def map_model_to_profile(model: str) -> str:
    if model not in MODEL_TO_PROFILE:
        raise ValueError(f"no profile mapping defined for model '{model}'")
    return MODEL_TO_PROFILE[model]


def resolve_profile(profile_name: str, overrides: DispatchOverrides | None = None) -> tuple[DispatchProfile, dict[str, Any]]:
    if profile_name not in PROFILES:
        raise ValueError(f"unknown profile '{profile_name}'")
    profile = PROFILES[profile_name]
    override_dict = overrides.as_dict() if overrides else {}
    invalid = sorted(set(override_dict) - set(profile.allowed_overrides))
    if invalid:
        raise ValueError(f"profile '{profile_name}' does not allow overrides: {', '.join(invalid)}")

    resolved: dict[str, Any] = {
        "timeout": profile.timeout,
        "search": profile.search,
    }
    if profile.reasoning_effort is not None:
        resolved["reasoning_effort"] = profile.reasoning_effort
    if profile.max_tokens is not None:
        resolved["max_tokens"] = profile.max_tokens
    resolved.update(override_dict)
    return profile, resolved


def profile_input_budget(profile_name: str) -> dict[str, Any]:
    profile, _ = resolve_profile(profile_name)
    return {
        "profile": profile.name,
        "input_token_limit": profile.input_token_limit,
        "input_token_estimator": profile.input_token_estimator,
    }


def classify_error(exc: Exception) -> tuple[str, str]:
    message = str(exc).strip() or exc.__class__.__name__
    lowered = message.lower()
    if isinstance(exc, (TimeoutError,)):
        return "timeout", message
    if any(marker in lowered for marker in ("timed out", "timeout", "deadline exceeded")):
        return "timeout", message
    if any(marker in lowered for marker in ("rate limit", "rate-limit", "resource_exhausted", "429", "too many requests", "overloaded")):
        return "rate_limit", message
    if any(marker in lowered for marker in ("insufficient_quota", "quota", "billing", "credit", "payment required", "exhausted balance")):
        return "quota", message
    if any(marker in lowered for marker in ("schema", "response_format", "additionalproperties")):
        return "schema_error", message
    if isinstance(exc, ImportError):
        return "dependency_error", message
    return "model_error", message


def _build_full_prompt(prompt: str, context_text: str | None) -> str:
    if context_text and context_text.strip():
        return context_text.rstrip() + "\n\n---\n\n" + prompt
    return prompt


def dispatch(
    *,
    profile: str,
    prompt: str,
    output_path: Path,
    context_path: Path | None = None,
    context_manifest_path: Path | None = None,
    context_text: str | None = None,
    meta_path: Path | None = None,
    error_path: Path | None = None,
    parsed_path: Path | None = None,
    schema: dict[str, Any] | None = None,
    api_only: bool = True,
    overrides: DispatchOverrides | None = None,
    system: str | None = None,
) -> DispatchResult:
    started_at = _utc_now()
    prompt_sha256 = _sha256(prompt)
    meta_path = meta_path or output_path.with_name(f"{output_path.stem}.meta.json")
    error_path = error_path or output_path.with_name(f"{output_path.stem}.error.json")
    parsed_path = parsed_path or (output_path.with_name(f"{output_path.stem}.parsed.json") if schema else None)

    try:
        profile_def, resolved = resolve_profile(profile, overrides)
    except Exception as exc:
        status = "config_error"
        message = str(exc)
        meta = {
            "requested_profile": profile,
            "status": status,
            "retryable": RETRYABLE_STATUSES[status],
            "error_type": status,
            "error_message": message,
            "started_at": started_at,
            "finished_at": _utc_now(),
            "prompt_sha256": prompt_sha256,
            "helper_version": HELPER_VERSION,
        }
        _remove_if_exists(output_path)
        _remove_if_exists(parsed_path)
        _atomic_write_json(meta_path, meta)
        _atomic_write_json(error_path, {"error_type": status, "error_message": message})
        return DispatchResult(
            status=status,
            retryable=False,
            requested_profile=profile,
            profile_version="unknown",
            profile_fingerprint="unknown",
            provider="unknown",
            model="unknown",
            output_path=str(output_path),
            meta_path=str(meta_path),
            error_path=str(error_path),
            parsed_path=str(parsed_path) if parsed_path else None,
            latency=0.0,
            llmx_version="unknown",
            helper_version=HELPER_VERSION,
            error_type=status,
            error_message=message,
        )

    context_body = context_text if context_text is not None else (context_path.read_text() if context_path else "")
    context_sha256 = _sha256(context_body)
    context_manifest = None
    if context_manifest_path is not None:
        context_manifest = json.loads(context_manifest_path.read_text())
    context_payload_hash = (
        (context_manifest or {}).get("payload_hash")
        or (context_manifest or {}).get("rendered_content_hash")
        or context_sha256
    )
    full_prompt = _build_full_prompt(prompt, context_body)

    try:
        llmx_chat, llmx_version = _bootstrap_llmx()
    except Exception as exc:
        status, message = classify_error(exc)
        if status == "model_error":
            status = "dependency_error"
        _remove_if_exists(output_path)
        _remove_if_exists(parsed_path)
        error_payload = {
            "error_type": status,
            "error_message": message,
            "traceback": traceback.format_exc(limit=5),
        }
        meta = {
            "requested_profile": profile_def.name,
            "profile_version": profile_def.version,
            "profile_fingerprint": profile_def.fingerprint(),
            "resolved_provider": profile_def.provider,
            "resolved_model": profile_def.model,
            "resolved_kwargs": resolved,
            "api_only": api_only,
            "status": status,
            "retryable": RETRYABLE_STATUSES[status],
            "error_type": status,
            "error_message": message,
            "started_at": started_at,
            "finished_at": _utc_now(),
            "context_sha256": context_sha256,
            "context_payload_hash": context_payload_hash,
            "context_manifest_path": str(context_manifest_path) if context_manifest_path else None,
            "prompt_sha256": prompt_sha256,
            "llmx_version": "unknown",
            "helper_version": HELPER_VERSION,
            "output_path": str(output_path),
        }
        _atomic_write_json(meta_path, meta)
        _atomic_write_json(error_path, error_payload)
        return DispatchResult(
            status=status,
            retryable=RETRYABLE_STATUSES[status],
            requested_profile=profile_def.name,
            profile_version=profile_def.version,
            profile_fingerprint=profile_def.fingerprint(),
            provider=profile_def.provider,
            model=profile_def.model,
            output_path=str(output_path),
            meta_path=str(meta_path),
            error_path=str(error_path),
            parsed_path=str(parsed_path) if parsed_path else None,
            latency=0.0,
            llmx_version="unknown",
            helper_version=HELPER_VERSION,
            error_type=status,
            error_message=message,
        )

    response_format = provider_response_schema(profile_def.provider, schema)
    call_kwargs: dict[str, Any] = {
        "prompt": full_prompt,
        "provider": profile_def.provider,
        "model": profile_def.model,
        "temperature": _temperature_for_model(profile_def.model),
        "api_only": api_only if api_only is not None else profile_def.api_only,
        "system": system,
        **resolved,
    }
    if response_format is not None:
        call_kwargs["response_format"] = response_format

    try:
        response = llmx_chat(**call_kwargs)
        content = str(response.content or "")
        latency = float(getattr(response, "latency", 0.0) or 0.0)
        usage = _extract_usage(response)
        if not content.strip():
            raise ValueError("empty model output")

        _atomic_write_text(output_path, content)
        _remove_if_exists(error_path)

        parsed_error: dict[str, Any] | None = None
        if schema and parsed_path:
            try:
                parsed = json.loads(_strip_markdown_fences(content))
                _atomic_write_json(parsed_path, parsed)
            except Exception as exc:
                parsed_error = {
                    "error_type": "parse_error",
                    "error_message": str(exc),
                }
                _remove_if_exists(parsed_path)

        status = "ok" if parsed_error is None else "parse_error"
        if parsed_error:
            _atomic_write_json(error_path, parsed_error)

        meta = {
            "requested_profile": profile_def.name,
            "profile_version": profile_def.version,
            "profile_fingerprint": profile_def.fingerprint(),
            "resolved_provider": profile_def.provider,
            "resolved_model": profile_def.model,
            "resolved_kwargs": resolved,
            "api_only": call_kwargs["api_only"],
            "schema_used": bool(schema),
            "status": status,
            "retryable": RETRYABLE_STATUSES[status],
            "error_type": parsed_error["error_type"] if parsed_error else None,
            "error_message": parsed_error["error_message"] if parsed_error else None,
            "latency": latency,
            "started_at": started_at,
            "finished_at": _utc_now(),
            "context_sha256": context_sha256,
            "context_payload_hash": context_payload_hash,
            "context_manifest_path": str(context_manifest_path) if context_manifest_path else None,
            "context_token_estimate": (context_manifest or {}).get("token_estimate"),
            "context_budget_metric": (context_manifest or {}).get("budget_metric"),
            "context_estimate_method": (context_manifest or {}).get("estimate_method"),
            "usage": usage,
            "prompt_sha256": prompt_sha256,
            "llmx_version": llmx_version,
            "helper_version": HELPER_VERSION,
            "output_path": str(output_path),
            "parsed_path": str(parsed_path) if parsed_path else None,
            "error_path": str(error_path) if parsed_error else None,
        }
        _atomic_write_json(meta_path, meta)
        _write_telemetry(
            {
                "started_at": started_at,
                "finished_at": meta["finished_at"],
                "requested_profile": profile_def.name,
                "profile_version": profile_def.version,
                "profile_fingerprint": profile_def.fingerprint(),
                "resolved_provider": profile_def.provider,
                "resolved_model": profile_def.model,
                "status": status,
                "retryable": RETRYABLE_STATUSES[status],
                "latency": latency,
                "context_payload_hash": context_payload_hash,
                "context_token_estimate": (context_manifest or {}).get("token_estimate"),
                "context_budget_metric": (context_manifest or {}).get("budget_metric"),
                "context_estimate_method": (context_manifest or {}).get("estimate_method"),
                "usage": usage,
                "api_only": call_kwargs["api_only"],
            }
        )
        return DispatchResult(
            status=status,
            retryable=RETRYABLE_STATUSES[status],
            requested_profile=profile_def.name,
            profile_version=profile_def.version,
            profile_fingerprint=profile_def.fingerprint(),
            provider=profile_def.provider,
            model=profile_def.model,
            output_path=str(output_path),
            meta_path=str(meta_path),
            error_path=str(error_path) if parsed_error else None,
            parsed_path=str(parsed_path) if parsed_path else None,
            latency=latency,
            llmx_version=llmx_version,
            helper_version=HELPER_VERSION,
            error_type=parsed_error["error_type"] if parsed_error else None,
            error_message=parsed_error["error_message"] if parsed_error else None,
        )

    except Exception as exc:
        status, message = classify_error(exc)
        if status == "model_error" and "empty model output" in message.lower():
            status = "empty_output"
        _remove_if_exists(output_path)
        _remove_if_exists(parsed_path)
        error_payload = {
            "error_type": status,
            "error_message": message,
            "traceback": traceback.format_exc(limit=5),
        }
        _atomic_write_json(error_path, error_payload)
        meta = {
            "requested_profile": profile_def.name,
            "profile_version": profile_def.version,
            "profile_fingerprint": profile_def.fingerprint(),
            "resolved_provider": profile_def.provider,
            "resolved_model": profile_def.model,
            "resolved_kwargs": resolved,
            "api_only": call_kwargs["api_only"],
            "schema_used": bool(schema),
            "status": status,
            "retryable": RETRYABLE_STATUSES[status],
            "error_type": status,
            "error_message": message,
            "latency": 0.0,
            "started_at": started_at,
            "finished_at": _utc_now(),
            "context_sha256": context_sha256,
            "context_payload_hash": context_payload_hash,
            "context_manifest_path": str(context_manifest_path) if context_manifest_path else None,
            "context_token_estimate": (context_manifest or {}).get("token_estimate"),
            "context_budget_metric": (context_manifest or {}).get("budget_metric"),
            "context_estimate_method": (context_manifest or {}).get("estimate_method"),
            "prompt_sha256": prompt_sha256,
            "llmx_version": llmx_version,
            "helper_version": HELPER_VERSION,
            "output_path": str(output_path),
            "parsed_path": str(parsed_path) if parsed_path else None,
            "error_path": str(error_path),
        }
        _atomic_write_json(meta_path, meta)
        _write_telemetry(
            {
                "started_at": started_at,
                "finished_at": meta["finished_at"],
                "requested_profile": profile_def.name,
                "profile_version": profile_def.version,
                "profile_fingerprint": profile_def.fingerprint(),
                "resolved_provider": profile_def.provider,
                "resolved_model": profile_def.model,
                "status": status,
                "retryable": RETRYABLE_STATUSES[status],
                "latency": 0.0,
                "context_payload_hash": context_payload_hash,
                "context_token_estimate": (context_manifest or {}).get("token_estimate"),
                "context_budget_metric": (context_manifest or {}).get("budget_metric"),
                "context_estimate_method": (context_manifest or {}).get("estimate_method"),
                "usage": None,
                "api_only": call_kwargs["api_only"],
                "error_type": status,
            }
        )
        return DispatchResult(
            status=status,
            retryable=RETRYABLE_STATUSES[status],
            requested_profile=profile_def.name,
            profile_version=profile_def.version,
            profile_fingerprint=profile_def.fingerprint(),
            provider=profile_def.provider,
            model=profile_def.model,
            output_path=str(output_path),
            meta_path=str(meta_path),
            error_path=str(error_path),
            parsed_path=str(parsed_path) if parsed_path else None,
            latency=0.0,
            llmx_version=llmx_version,
            helper_version=HELPER_VERSION,
            error_type=status,
            error_message=message,
        )

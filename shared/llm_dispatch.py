from __future__ import annotations

import hashlib
import importlib.metadata
import json
import os
import re
import sys
import traceback
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any, Callable


HELPER_VERSION = "2026-04-10-v1"
DEFAULT_TELEMETRY_PATH = (
    Path(__file__).resolve().parents[1] / ".claude" / "telemetry" / "llm-dispatch.jsonl"
)

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
_LLMX_DISPATCH: Callable[..., Any] | None = None
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
    auth: str = "api"  # "api" | "subscription"
    mode: str = "chat"  # "chat" | "agent" — req/res vs tools/MCP loop
    allowed_overrides: tuple[str, ...] = ("timeout", "reasoning_effort", "max_tokens", "search")
    version: str = "v1"

    def fingerprint(self) -> str:
        payload = json.dumps(asdict(self), sort_keys=True, separators=(",", ":")).encode("utf-8")
        return hashlib.sha256(payload).hexdigest()[:16]


PROFILES: dict[str, DispatchProfile] = {
    "fast_extract": DispatchProfile(
        name="fast_extract",
        intent="Low-cost extraction, triage, and short synthesis",
        provider="openai",
        # 2026-09-05: Astra-low on subscription. Luna does not beat Astra-low
        # on quality (AA Intelligence Index: Astra-low 57 vs Luna-max 43).
        # Keep `-m gpt-6-luna` for metered API bulk where $/tok and speed win.
        model="gpt-6-astra",
        timeout=300,
        reasoning_effort="low",
        auth="subscription",
        input_token_limit=120000,
    ),
    "deep_review": DispatchProfile(
        name="deep_review",
        intent="Long-context structural critique and review",
        provider="google",
        # 2026-09-05: Gemini 3.8 Flash is the current Flash GA (intro $0.75/$3.75
        # through 2026-12-31). Critique-only policy unchanged.
        model="gemini-3.8-flash",
        timeout=300,
        reasoning_effort="high",
        input_token_limit=900000,
    ),
    "formal_review": DispatchProfile(
        name="formal_review",
        intent="Formal or quantitative GPT-backed review",
        provider="openai",
        # 2026-09-05: GPT-6 Astra is the flagship GPT / Codex default.
        # gpt-6.1-sol / gpt-6-luna are the cheaper named cost tiers.
        model="gpt-6-astra",
        timeout=600,
        # 2026-06-10: formal is the GPT reasoning axis for reviews — operator
        # policy is "medium most cases, high for deep/formal". `gpt_general`
        # (general dispatch, "most cases") stays medium; mechanical stays low.
        reasoning_effort="high",
        max_tokens=32768,
        input_token_limit=120000,
    ),
    "gpt_general": DispatchProfile(
        name="gpt_general",
        intent="General-purpose GPT-backed dispatch",
        provider="openai",
        # 2026-09-05: everyday GPT follows the operator Codex default (Astra).
        model="gpt-6-astra",
        timeout=600,
        reasoning_effort="medium",
        # Subscription via codex-cli ($0 on the ChatGPT plan); API metering is opt-in.
        auth="subscription",
        input_token_limit=120000,
    ),
    "mechanical_review": DispatchProfile(
        # Mechanical/lint axis (deep/full presets). Astra at LOW effort:
        # the job is fast pattern-spotting (stale refs, naming, dup), not
        # reasoning.
        name="mechanical_review",
        intent="Low-effort GPT mechanical/lint audit",
        provider="openai",
        model="gpt-6-astra",
        timeout=300,
        reasoning_effort="low",
        # 2026-07-14: subscription lane (codex-cli, $0) — see gpt_general.
        auth="subscription",
        input_token_limit=120000,
    ),
    "search_grounded": DispatchProfile(
        name="search_grounded",
        intent="Search-backed answer synthesis",
        provider="google",
        model="gemini-3.8-flash",
        timeout=300,
        search=True,
        input_token_limit=900000,
    ),
    "cheap_tick": DispatchProfile(
        name="cheap_tick",
        intent="Low-cost maintenance or cycle tick synthesis",
        provider="openai",
        model="gpt-6-astra",
        timeout=300,
        reasoning_effort="low",
        auth="subscription",
        input_token_limit=120000,
    ),
    "observe_bulk": DispatchProfile(
        name="observe_bulk",
        intent="Headless /observe bulk classification — cheap context; verify before promotion",
        provider="openai",
        # NOTE the context drop 900K→120K: callers already size-cap via
        # `just observe-context`; chunk rather than stuff.
        model="gpt-6-astra",
        timeout=300,
        reasoning_effort="low",
        auth="subscription",
        input_token_limit=120000,
    ),
    "legacy_pro_review": DispatchProfile(
        # Pre-2026-05-24 default for deep_review. Kept available for
        # tasks where Pro's specific strengths (ARC-AGI-2, GPQA Diamond,
        # video understanding) actually dominate. For general adversarial
        # critique/synthesis, prefer deep_review (gemini-3.8-flash).
        name="legacy_pro_review",
        intent="Pre-2026-05-24 Gemini Pro fallback for cases needing Pro-specific strengths",
        provider="google",
        model="gemini-3.1-pro-preview",
        timeout=300,
        reasoning_effort="high",
        input_token_limit=900000,
    ),
    "claude_review": DispatchProfile(
        # Opt-in third cosigner: Claude Opus 5.5 via Claude Code subscription
        # (llmx provider `anthropic` → claude-cli transport). NOT in the default
        # Gemini+GPT pairing — request explicitly with `--axes claude` (or add to
        # an axis list). A genuinely third training family for adversarial diversity.
        # auth=subscription → claude-cli OAuth. NEVER auth=api unless caller opts in.
        name="claude_review",
        intent="Claude Opus 5.5 adversarial review via subscription (opt-in cosigner)",
        provider="anthropic",
        model="claude-opus-5-5",
        # Opus max architecture reviews can legitimately run beyond ten minutes.
        # A live 2026-07-10 review was killed at the old 600s boundary with zero
        # output despite a healthy subscription probe. Keep the bound finite, but
        # match llmx's canonical max-effort timeout instead of imposing a
        # second, shorter profile ceiling.
        timeout=3600,
        reasoning_effort="max",
        input_token_limit=200000,
        auth="subscription",
        mode="chat",
        # claude-cli headless has no max_tokens — setting it forces API fallback (billing).
        allowed_overrides=("timeout",),
    ),
    "glm_review": DispatchProfile(
        # Opt-in fourth-lineage cosigner: Z.ai GLM-5.2 via the llmx `zai` provider
        # (routed through OpenRouter today, OPENROUTER_API_KEY). A genuinely NEW
        # training lab (Zhipu/Z.ai) — independent of Google/OpenAI/Anthropic/Cursor —
        # so it adds real cross-lab adversarial diversity (constitution P12: same-lab
        # panels are ~1 effective vote). Metered API (~$1.20/M in, $3.20/M out — cheap,
        # NOT flat-free); auth defaults to "api". NB: GLM emits heavy default reasoning,
        # so a review costs more reasoning tokens than the GPT/Gemini cosigners.
        name="glm_review",
        intent="Z.ai GLM-5.2 adversarial review (opt-in fourth-lineage cosigner)",
        provider="zai",
        model="glm-5.2",
        timeout=600,
        mode="chat",
        input_token_limit=200000,
        allowed_overrides=("timeout",),
    ),
    "premise_scout": DispatchProfile(
        # Repo-grounded premise falsifier — NOT a cosigner axis. Invoked by
        # model-review.py via `codex exec -s read-only -C <project>` before
        # packet-only axes. 2026-10-07: Composer 2.5 retired as outdated; the
        # operator chose GPT-6 Astra at low effort (codex-cli subscription, $0).
        # provider "openai" + auth "subscription" is this file's codex-cli lane.
        name="premise_scout",
        intent="VOI premise scout: grep/read repo to falsify design premises",
        provider="openai",
        model="gpt-6-astra",
        timeout=300,
        reasoning_effort="low",
        auth="subscription",
        mode="chat",
        input_token_limit=120000,
        allowed_overrides=("timeout",),
    ),
    "premise_scout_fallback": DispatchProfile(
        # Served only when the Astra scout fails on a Codex plan/usage limit
        # (llmx exit-6 class). Operator 2026-10-07: "gpt 6.1 sol high"; the
        # slug is gpt-6.1-sol since 2026-10-09; model-guide names Sol as
        # Astra's plan-limit fallback.
        name="premise_scout_fallback",
        intent="Premise scout fallback when the Astra plan limit is exhausted",
        provider="openai",
        model="gpt-6.1-sol",
        timeout=300,
        reasoning_effort="high",
        auth="subscription",
        mode="chat",
        input_token_limit=120000,
        allowed_overrides=("timeout",),
    ),
    "grok_review": DispatchProfile(
        # Opt-in repo-grounded cosigner. model-review.py invokes cursor-agent
        # directly with --mode ask and --workspace; llmx's Cursor chat transport
        # is intentionally packet-only. The exact slug is registry-bound and
        # preflighted before every Grok-axis dispatch.
        name="grok_review",
        intent="Grok 4.7 repo-grounded adversarial review (opt-in cosigner)",
        provider="cursor",
        model="grok-4.7-high",
        timeout=1200,
        auth="subscription",
        mode="chat",
        input_token_limit=120000,
        allowed_overrides=("timeout",),
    ),
}

# Retired profile names refuse with a successor instead of "unknown profile".
_COMPOSER_RETIRED = (
    "Cursor Composer 2.5 retired 2026-10-07 as outdated; use `fast_extract` "
    "(gpt-6-astra, low effort, codex-cli subscription) for packet screens; repo-grounded "
    "premise checks run as `codex exec -s read-only -C <repo> -m gpt-6-astra` (the /critique "
    "premise scout)"
)
RETIRED_PROFILES = {
    "composer_review": _COMPOSER_RETIRED,
    "composer_screen": _COMPOSER_RETIRED,
}

MODEL_TO_PROFILE = {
    "gemini-3.1-flash-lite-preview": "observe_bulk",
    "gemini-3.8-flash": "deep_review",
    "gemini-3.1-pro-preview": "legacy_pro_review",  # demoted 2026-05-24
    "gpt-6-astra": "formal_review",
    "gpt-6": "formal_review",
    "gpt-6.1-sol": "formal_review",
    "gpt-6-sol": "formal_review",  # llmx alias → gpt-6.1-sol; kept for old pins
    "gpt-6-luna": "gpt_general",  # explicit Luna pin; effort is the cheap/mechanical dial
    "claude-opus-5": "claude_review",
    "glm-5.2": "glm_review",
    "grok-4.7-high": "grok_review",
}


@dataclass
class DispatchOverrides:
    timeout: int | None = None
    reasoning_effort: str | None = None
    max_tokens: int | None = None
    search: bool | None = None

    def as_dict(self) -> dict[str, Any]:
        return {key: value for key, value in asdict(self).items() if value is not None}


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
    with NamedTemporaryFile(
        "w", dir=path.parent, prefix=f".{path.name}.", suffix=".tmp", delete=False
    ) as handle:
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


def _wrap_chat_as_dispatch(chat_fn: Callable[..., Any]) -> Callable[..., Any]:
    """Test/compat shim: chat()-like callable → object with DispatchResult fields."""

    @dataclass
    class _ShimResult:
        status: str
        retryable: bool
        text: str = ""
        usage: dict[str, Any] = field(default_factory=dict)
        latency: float = 0.0
        error_type: str | None = None
        error_message: str | None = None
        provider: str = ""
        model: str = ""

    def _wrapped(**kwargs: Any) -> _ShimResult:
        try:
            response = chat_fn(**kwargs)
            content = str(getattr(response, "content", "") or "")
            latency = float(getattr(response, "latency", 0.0) or 0.0)
            usage = _extract_usage(response) or {}
            if not content.strip():
                return _ShimResult(
                    status="empty_output",
                    retryable=True,
                    text=content,
                    usage=usage,
                    latency=latency,
                    error_type="empty_output",
                    error_message="empty model output",
                    provider=str(kwargs.get("provider") or ""),
                    model=str(kwargs.get("model") or ""),
                )
            return _ShimResult(
                status="ok",
                retryable=False,
                text=content,
                usage=usage,
                latency=latency,
                provider=str(getattr(response, "provider", None) or kwargs.get("provider") or ""),
                model=str(getattr(response, "model", None) or kwargs.get("model") or ""),
            )
        except Exception as exc:
            status, message = classify_error(exc)
            return _ShimResult(
                status=status,
                retryable=RETRYABLE_STATUSES.get(status, False),
                error_type=status,
                error_message=message,
                provider=str(kwargs.get("provider") or ""),
                model=str(kwargs.get("model") or ""),
            )

    return _wrapped


def _bootstrap_llmx() -> tuple[Callable[..., Any], str]:
    global _LLMX_CHAT, _LLMX_DISPATCH, _LLMX_VERSION
    # Test hook first: injected chat mock → wrap as structured dispatch (no cache,
    # so per-test patches always apply).
    if _LLMX_CHAT is not None:
        return _wrap_chat_as_dispatch(_LLMX_CHAT), _LLMX_VERSION or "unknown"

    if _LLMX_DISPATCH is not None:
        return _LLMX_DISPATCH, _LLMX_VERSION or "unknown"

    # Phase 1: try direct import (works if llmx is installed in current venv).
    llmx_dispatch: Callable[..., Any] | None = None
    try:
        from llmx.api import dispatch as _llmx_dispatch  # type: ignore

        llmx_dispatch = _llmx_dispatch
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
            installed_pys = (
                sorted(p.name for p in tool_root.glob("python*")) if tool_root.is_dir() else []
            )
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
            from llmx.api import dispatch as _llmx_dispatch_2  # type: ignore

            llmx_dispatch = _llmx_dispatch_2
        except ImportError as exc:
            raise ImportError(
                f"llmx tool install at {matching_site} could not be imported: {exc}. "
                f"The Python version matched but a runtime dependency is missing or "
                f"corrupted. Try `uv tool install --reinstall llmx`."
            ) from exc

    assert llmx_dispatch is not None  # both branches above set or raise
    _LLMX_DISPATCH = llmx_dispatch

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

    return llmx_dispatch, _LLMX_VERSION or "unknown"


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


def resolve_profile(
    profile_name: str, overrides: DispatchOverrides | None = None
) -> tuple[DispatchProfile, dict[str, Any]]:
    if profile_name in RETIRED_PROFILES:
        raise ValueError(f"profile '{profile_name}' is retired: {RETIRED_PROFILES[profile_name]}")
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
    if any(
        marker in lowered
        for marker in (
            "rate limit",
            "rate-limit",
            "resource_exhausted",
            "429",
            "too many requests",
            "overloaded",
            "503",
            "unavailable",
        )
    ):
        return "rate_limit", message
    if any(
        marker in lowered
        for marker in (
            "insufficient_quota",
            "quota",
            "billing",
            "credit",
            "payment required",
            "exhausted balance",
        )
    ):
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


def _resolve_call_auth(
    *,
    profile_auth: str,
    auth: str | None,
    api_only: bool | None,
) -> str:
    if auth is not None and api_only is not None:
        raise ValueError("pass auth= or api_only=, not both")
    if auth is not None:
        token = auth.strip().lower()
        if token not in ("api", "subscription"):
            raise ValueError(f"auth must be 'api' or 'subscription'; got {auth!r}")
        return token
    if api_only is not None:
        return "api" if api_only else "subscription"
    return profile_auth


def _resolve_call_mode(
    *,
    profile_mode: str,
    mode: str | None,
) -> str:
    if mode is not None:
        token = mode.strip().lower()
        if token not in ("chat", "agent"):
            raise ValueError(f"mode must be 'chat' or 'agent'; got {mode!r}")
        return token
    return profile_mode


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
    # None (default) → use the profile's auth. Per-call override via auth=.
    auth: str | None = None,
    mode: str | None = None,
    api_only: bool | None = None,  # deprecated: use auth="api"|"subscription"
    overrides: DispatchOverrides | None = None,
    system: str | None = None,
) -> DispatchResult:
    started_at = _utc_now()
    prompt_sha256 = _sha256(prompt)
    meta_path = meta_path or output_path.with_name(f"{output_path.stem}.meta.json")
    error_path = error_path or output_path.with_name(f"{output_path.stem}.error.json")
    parsed_path = parsed_path or (
        output_path.with_name(f"{output_path.stem}.parsed.json") if schema else None
    )
    start_path = output_path.with_name(f"{output_path.stem}.start.json")

    # Write start marker BEFORE any work so callers can distinguish
    # "subprocess never ran" from "subprocess ran and failed inside dispatch."
    # If meta.json is absent but start.json is present, dispatch entered but
    # died (e.g. SIGKILL, OOM, interpreter crash) before writing telemetry.
    # If both are absent the subprocess never reached dispatch() at all.
    # Removed on successful or error-handled completion below.
    # Evidence: docs/audit/observe-gaps-2026-05-11/findings.md F1.
    _atomic_write_json(
        start_path,
        {
            "started_at": started_at,
            "requested_profile": profile,
            "output_path": str(output_path),
            "pid": os.getpid(),
            "helper_version": HELPER_VERSION,
        },
    )

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
        _remove_if_exists(start_path)
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

    context_body = (
        context_text
        if context_text is not None
        else (context_path.read_text() if context_path else "")
    )
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

    resolved_auth = _resolve_call_auth(
        profile_auth=profile_def.auth,
        auth=auth,
        api_only=api_only,
    )
    resolved_mode = _resolve_call_mode(
        profile_mode=profile_def.mode,
        mode=mode,
    )

    try:
        llmx_transport, llmx_version = _bootstrap_llmx()
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
            "auth": resolved_auth,
            "mode": resolved_mode,
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
        _remove_if_exists(start_path)
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
        "auth": resolved_auth,
        "mode": resolved_mode,
        "system": system,
        **resolved,
    }
    if response_format is not None:
        call_kwargs["response_format"] = response_format

    # Opt-in Flex tier: 50% off, best-effort/variable latency (1–15 min, sheds
    # load with 503s). Gated by the LLMX_FLEX env so ONLY a background/cron caller
    # that explicitly exports it ever flexes — never an interactive or agent-path
    # call (which would block on the variable latency). Google API path only
    # (service_tier is a Gemini param; ignored elsewhere). A Flex 503 is caught by
    # the rate-limit fallback (classify_error + the caller's rate-limit markers).
    if profile_def.provider == "google" and os.environ.get("LLMX_FLEX", "").strip().lower() in (
        "1",
        "true",
        "yes",
    ):
        call_kwargs["service_tier"] = "flex"

    try:
        # Transport layer: llmx.api.dispatch (ADR P1). Returns structured status —
        # does not raise on model/rate-limit failures. Profile I/O stays here.
        transport = llmx_transport(**call_kwargs)
        transport_status = getattr(transport, "status", "dispatch_error")
        # Map llmx-only statuses onto the skills taxonomy.
        if transport_status == "api_key":
            transport_status = "dependency_error"
        elif transport_status == "spend_cap":
            transport_status = "quota"
        elif transport_status == "dry_run":
            transport_status = "config_error"

        if transport_status != "ok":
            status = transport_status if transport_status in RETRYABLE_STATUSES else "model_error"
            message = (
                getattr(transport, "error_message", None)
                or getattr(transport, "error_type", None)
                or transport_status
            )
            _remove_if_exists(output_path)
            _remove_if_exists(parsed_path)
            error_payload = {
                "error_type": status,
                "error_message": message,
                "traceback": None,
            }
            _atomic_write_json(error_path, error_payload)
            meta = {
                "requested_profile": profile_def.name,
                "profile_version": profile_def.version,
                "profile_fingerprint": profile_def.fingerprint(),
                "resolved_provider": profile_def.provider,
                "resolved_model": profile_def.model,
                "resolved_kwargs": resolved,
                "auth": call_kwargs["auth"],
                "mode": call_kwargs["mode"],
                "schema_used": bool(schema),
                "status": status,
                "retryable": RETRYABLE_STATUSES[status],
                "error_type": status,
                "error_message": message,
                "latency": float(getattr(transport, "latency", 0.0) or 0.0),
                "started_at": started_at,
                "finished_at": _utc_now(),
                "context_sha256": context_sha256,
                "context_payload_hash": context_payload_hash,
                "context_manifest_path": str(context_manifest_path)
                if context_manifest_path
                else None,
                "context_token_estimate": (context_manifest or {}).get("token_estimate"),
                "context_budget_metric": (context_manifest or {}).get("budget_metric"),
                "context_estimate_method": (context_manifest or {}).get("estimate_method"),
                "prompt_sha256": prompt_sha256,
                "llmx_version": llmx_version,
                "helper_version": HELPER_VERSION,
                "output_path": str(output_path),
                "parsed_path": str(parsed_path) if parsed_path else None,
                "error_path": str(error_path),
                "llmx_transport": getattr(transport, "transport", None),
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
                    "latency": meta["latency"],
                    "context_payload_hash": context_payload_hash,
                    "context_token_estimate": (context_manifest or {}).get("token_estimate"),
                    "context_budget_metric": (context_manifest or {}).get("budget_metric"),
                    "context_estimate_method": (context_manifest or {}).get("estimate_method"),
                    "usage": getattr(transport, "usage", None) or None,
                    "auth": call_kwargs["auth"],
                    "mode": call_kwargs["mode"],
                    "error_type": status,
                }
            )
            _remove_if_exists(start_path)
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
                latency=float(getattr(transport, "latency", 0.0) or 0.0),
                llmx_version=llmx_version,
                helper_version=HELPER_VERSION,
                error_type=status,
                error_message=str(message),
            )

        content = str(getattr(transport, "text", None) or getattr(transport, "content", "") or "")
        latency = float(getattr(transport, "latency", 0.0) or 0.0)
        usage = getattr(transport, "usage", None) or None
        if isinstance(usage, dict) and not usage:
            usage = None

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
            "auth": call_kwargs["auth"],
            "mode": call_kwargs["mode"],
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
            "llmx_transport": getattr(transport, "transport", None),
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
                "auth": call_kwargs["auth"],
                "mode": call_kwargs["mode"],
            }
        )
        _remove_if_exists(start_path)
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
            "auth": call_kwargs["auth"],
            "mode": call_kwargs["mode"],
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
                "auth": call_kwargs["auth"],
                "mode": call_kwargs["mode"],
                "error_type": status,
            }
        )
        _remove_if_exists(start_path)
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

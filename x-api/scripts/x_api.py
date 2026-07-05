"""X API v2 client — pay-per-use developer tier.

Bearer-token auth (app-only). Reads `X_API_BEARER_TOKEN` from os.environ.
Caller is responsible for loading the env var (e.g., from .env.local,
~/.env, or launchd plist EnvironmentVariables).

Pricing (2026-05-01):
- $0.005 per post read (each tweet returned, not per request)
- $0.010 per user lookup
"""
from __future__ import annotations

import fcntl
import json
import os
import time
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path

import requests

API_BASE = "https://api.x.com/2"
COST_USER_LOOKUP = 0.010
COST_TWEET_READ = 0.005

# Wait at most this long for a rate-limit reset before raising.
# X API resets are typically <=15 min; longer indicates an account-level cap.
MAX_RATE_LIMIT_WAIT_SECONDS = 900

# Global ledger location — wallet-scoped, NOT CWD-scoped, so spend across
# projects sharing one bearer token rolls up to a single budget.
DEFAULT_LEDGER = Path.home() / ".local/state/x-api/cost_ledger.jsonl"


class RateLimitExceeded(RuntimeError):
    """Raised when the rate-limit reset is further away than the caller can wait."""

    def __init__(self, wait_seconds: int):
        super().__init__(f"rate-limited; reset in {wait_seconds}s")
        self.wait_seconds = wait_seconds


class BudgetExceeded(RuntimeError):
    """Raised before any call that would push spend past the monthly cap."""


@dataclass
class CostTally:
    user_lookups: int = 0
    tweet_reads: int = 0

    @property
    def usd(self) -> float:
        return (
            self.user_lookups * COST_USER_LOOKUP
            + self.tweet_reads * COST_TWEET_READ
        )


def _load_dotenv_into_environ(env_file: Path, override: bool = False) -> None:
    """Minimal .env parser.

    Handles `export VAR=value` and `VAR="quoted value"` shell forms in
    addition to bare `VAR=value`. When override=True, replaces values
    already present in os.environ (use when the caller explicitly chose
    this file and wants it to win over shell-pre-loaded values).
    """
    if not env_file.exists():
        return
    for line in env_file.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        if line.startswith("export "):
            line = line[len("export ") :].lstrip()
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip()
        if (len(value) >= 2 and value[0] == value[-1] and value[0] in ("'", '"')):
            value = value[1:-1]
        if not key:
            continue
        if override or key not in os.environ:
            os.environ[key] = value


def load_token_from_dotenv(
    env_file: Path | str | None = None,
    override: bool | None = None,
) -> None:
    """Load X_API_BEARER_TOKEN from a .env file into os.environ.

    Default search order when env_file is None (stops at first hit):
      1. CWD/.env.local
      2. CWD/.env
      3. ~/.env

    When env_file is given explicitly, defaults to override=True so the
    explicitly-named file wins over any shell-pre-loaded stale value.
    When searching defaults, override defaults to False (shell env wins).
    """
    if env_file is not None:
        do_override = True if override is None else override
        _load_dotenv_into_environ(Path(env_file), override=do_override)
        return
    do_override = False if override is None else override
    if not do_override and os.environ.get("X_API_BEARER_TOKEN"):
        return
    for candidate in (Path(".env.local"), Path(".env"), Path.home() / ".env"):
        _load_dotenv_into_environ(candidate, override=do_override)
        if os.environ.get("X_API_BEARER_TOKEN"):
            return


def _headers() -> dict[str, str]:
    token = os.environ.get("X_API_BEARER_TOKEN")
    if not token:
        raise RuntimeError(
            "X_API_BEARER_TOKEN not set. Either export it, place it in "
            ".env.local / .env / ~/.env, or call load_token_from_dotenv()."
        )
    return {"Authorization": f"Bearer {token}", "User-Agent": "x-api-skill/0.1"}


def _request(url: str, params: dict | None = None) -> dict:
    """GET with single retry on 429.

    Sleeps until the actual rate-limit reset time. If reset is more than
    MAX_RATE_LIMIT_WAIT_SECONDS away, raises RateLimitExceeded so the caller
    can skip cleanly instead of blocking the whole batch.
    """
    for attempt in range(2):
        r = requests.get(url, headers=_headers(), params=params, timeout=30)
        if r.status_code == 429 and attempt == 0:
            reset = int(r.headers.get("x-rate-limit-reset", "0"))
            wait = max(1, reset - int(time.time()))
            if wait > MAX_RATE_LIMIT_WAIT_SECONDS:
                raise RateLimitExceeded(wait)
            time.sleep(wait + 1)
            continue
        r.raise_for_status()
        return r.json()
    raise RuntimeError("rate-limited twice")


def get_user(username: str, tally: CostTally | None = None) -> dict:
    data = _request(
        f"{API_BASE}/users/by/username/{username}",
        {"user.fields": "public_metrics,verified,created_at,description"},
    )
    if tally is not None:
        tally.user_lookups += 1
    if "data" not in data:
        # X returns 200 with an `errors` array for suspended/renamed/not-found users —
        # surface the API's own reason instead of a bare KeyError('data').
        errs = data.get("errors") or [{"detail": "no data and no errors in response"}]
        raise RuntimeError(f"user lookup failed for {username!r}: {errs[0].get('detail', errs[0])}")
    return data["data"]


def get_user_tweets(
    user_id: str,
    *,
    max_results: int = 100,
    start_time: str | None = None,
    max_pages: int = 5,
    tally: CostTally | None = None,
) -> list[dict]:
    """Pull a user's recent tweets (excludes replies and retweets).

    `start_time`: ISO 8601, e.g. "2026-04-01T00:00:00Z".
    Hard-capped at `max_pages * max_results` tweets to bound cost.
    """
    params: dict = {
        "max_results": max_results,
        "tweet.fields": "created_at,public_metrics,entities,referenced_tweets,lang",
        "exclude": "replies,retweets",
    }
    if start_time:
        params["start_time"] = start_time
    out: list[dict] = []
    next_token: str | None = None
    for _ in range(max_pages):
        if next_token:
            params["pagination_token"] = next_token
        data = _request(f"{API_BASE}/users/{user_id}/tweets", params)
        page = data.get("data", [])
        out.extend(page)
        if tally is not None:
            tally.tweet_reads += len(page)
        next_token = data.get("meta", {}).get("next_token")
        if not next_token:
            break
    return out


@contextmanager
def _exclusive_lock(path: Path):
    """Whole-file fcntl.LOCK_EX held for the duration of the block."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.touch(exist_ok=True)
    with path.open("a+") as f:
        fcntl.flock(f.fileno(), fcntl.LOCK_EX)
        try:
            yield f
        finally:
            fcntl.flock(f.fileno(), fcntl.LOCK_UN)


def log_cost(tally: CostTally, label: str, ledger: Path | None = None) -> None:
    """Append cost line under exclusive lock so concurrent runs don't interleave."""
    path = Path(ledger) if ledger else DEFAULT_LEDGER
    rec = {
        "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "label": label,
        "user_lookups": tally.user_lookups,
        "tweet_reads": tally.tweet_reads,
        "usd": round(tally.usd, 6),
    }
    with _exclusive_lock(path) as f:
        f.write(json.dumps(rec) + "\n")
        f.flush()
        os.fsync(f.fileno())


def month_to_date_usd(ledger: Path | None = None) -> float:
    """Sum spend in current UTC month. Holds shared lock during read."""
    path = Path(ledger) if ledger else DEFAULT_LEDGER
    if not path.exists():
        return 0.0
    month = time.strftime("%Y-%m", time.gmtime())
    total = 0.0
    with path.open("r") as f:
        fcntl.flock(f.fileno(), fcntl.LOCK_SH)
        try:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                rec = json.loads(line)
                if rec.get("ts", "").startswith(month):
                    total += rec.get("usd", 0.0)
        finally:
            fcntl.flock(f.fileno(), fcntl.LOCK_UN)
    return round(total, 6)


def assert_budget(
    monthly_cap: float,
    projected_call_cost: float,
    ledger: Path | None = None,
    in_flight: float = 0.0,
) -> float:
    """Raise BudgetExceeded if MTD + in_flight + projected > monthly_cap.

    Returns current MTD. Call this BEFORE making each billable request.
    """
    mtd = month_to_date_usd(ledger=ledger)
    if mtd + in_flight + projected_call_cost >= monthly_cap:
        raise BudgetExceeded(
            f"would exceed ${monthly_cap:.2f} cap: "
            f"MTD ${mtd:.2f} + in-flight ${in_flight:.2f} + "
            f"projected ${projected_call_cost:.2f}"
        )
    return mtd

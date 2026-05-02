"""X API v2 client — pay-per-use developer tier.

Bearer-token auth (app-only). Reads `X_API_BEARER_TOKEN` from os.environ.
Caller is responsible for loading the env var (e.g., from .env.local,
~/.env, or launchd plist EnvironmentVariables).

Pricing (2026-05-01):
- $0.005 per post read (each tweet returned, not per request)
- $0.010 per user lookup
"""
from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass
from pathlib import Path

import requests

API_BASE = "https://api.x.com/2"
COST_USER_LOOKUP = 0.010
COST_TWEET_READ = 0.005

# Cost ledger lives in CWD/.scratch — caller's project sees its own ledger
COST_LEDGER = Path(".scratch/x_api_cost_ledger.jsonl")


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


def _load_dotenv_into_environ(env_file: Path) -> None:
    """Minimal .env parser — populates os.environ if not already set."""
    if not env_file.exists():
        return
    for line in env_file.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        if key and key not in os.environ:
            os.environ[key] = value.strip()


def load_token_from_dotenv(env_file: Path | str | None = None) -> None:
    """Convenience: load X_API_BEARER_TOKEN from a .env file into os.environ.

    Default search order:
      1. CWD/.env.local
      2. CWD/.env
      3. ~/.env
    Stops at the first file that defines X_API_BEARER_TOKEN.
    """
    if env_file is not None:
        _load_dotenv_into_environ(Path(env_file))
        return
    if os.environ.get("X_API_BEARER_TOKEN"):
        return
    for candidate in (Path(".env.local"), Path(".env"), Path.home() / ".env"):
        _load_dotenv_into_environ(candidate)
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
    """GET with single retry on 429 honoring Reset header."""
    for attempt in range(2):
        r = requests.get(url, headers=_headers(), params=params, timeout=30)
        if r.status_code == 429 and attempt == 0:
            reset = int(r.headers.get("x-rate-limit-reset", "0"))
            wait = max(1, reset - int(time.time()))
            time.sleep(min(wait, 60))
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


def log_cost(tally: CostTally, label: str, ledger: Path | None = None) -> None:
    """Append cost line to ledger for monthly budget tracking."""
    path = ledger or COST_LEDGER
    path.parent.mkdir(exist_ok=True)
    rec = {
        "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "label": label,
        "user_lookups": tally.user_lookups,
        "tweet_reads": tally.tweet_reads,
        "usd": round(tally.usd, 4),
    }
    with path.open("a") as f:
        f.write(json.dumps(rec) + "\n")


def month_to_date_usd(ledger: Path | None = None) -> float:
    path = ledger or COST_LEDGER
    if not path.exists():
        return 0.0
    month = time.strftime("%Y-%m", time.gmtime())
    total = 0.0
    for line in path.read_text().splitlines():
        if not line.strip():
            continue
        rec = json.loads(line)
        if rec.get("ts", "").startswith(month):
            total += rec.get("usd", 0.0)
    return round(total, 4)

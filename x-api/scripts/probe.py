"""X API v2 smoke probe — auth + recent posts pull.

Validates pay-per-use credentials work and content returns.

Usage:
    uv run --with requests python3 ~/Projects/skills/x-api/scripts/probe.py USERNAME [N] [START_ISO]

Env: X_API_BEARER_TOKEN (auto-loaded from .env.local / .env / ~/.env if unset).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from x_api import (
    COST_TWEET_READ,
    COST_USER_LOOKUP,
    CostTally,
    get_user,
    get_user_tweets,
    load_token_from_dotenv,
)


def main() -> int:
    if len(sys.argv) < 2:
        sys.exit("usage: probe.py USERNAME [MAX_RESULTS=10] [START_ISO]")

    username = sys.argv[1]
    max_results = int(sys.argv[2]) if len(sys.argv) > 2 else 10
    start_time = sys.argv[3] if len(sys.argv) > 3 else None

    load_token_from_dotenv()
    tally = CostTally()

    print(f"\n[probe] @{username}  max={max_results}  start={start_time}")

    print("\n[1/2] User lookup")
    user = get_user(username, tally=tally)
    print(f"  id={user['id']}  name={user.get('name')}  verified={user.get('verified')}")
    pm = user.get("public_metrics", {})
    print(f"  followers={pm.get('followers_count'):,}  "
          f"following={pm.get('following_count'):,}  "
          f"tweets={pm.get('tweet_count'):,}")

    print("\n[2/2] Recent tweets (no replies/RTs)")
    tweets = get_user_tweets(
        user["id"],
        max_results=max_results,
        start_time=start_time,
        max_pages=5,
        tally=tally,
    )
    print(f"  returned {len(tweets)} tweets")

    for i, t in enumerate(tweets[:20], 1):
        m = t.get("public_metrics", {})
        text = t["text"].replace("\n", " ")
        if len(text) > 200:
            text = text[:197] + "..."
        cashtags = [c["tag"] for c in (t.get("entities") or {}).get("cashtags") or []]
        ct = f" cashtags={cashtags}" if cashtags else ""
        print(f"\n  [{i}] {t['created_at']}  "
              f"likes={m.get('like_count')} rts={m.get('retweet_count')} "
              f"impr={m.get('impression_count')}{ct}")
        print(f"      {text}")

    out = Path(".scratch") / f"x_probe_{username}.json"
    out.parent.mkdir(exist_ok=True)
    out.write_text(json.dumps({"user": user, "tweets": tweets}, indent=2))
    print(f"\n[saved] {out}")

    print(f"\n[cost] ~${tally.usd:.3f} "
          f"({tally.user_lookups} user × ${COST_USER_LOOKUP:.3f} + "
          f"{tally.tweet_reads} tweet × ${COST_TWEET_READ:.3f})")
    return 0


if __name__ == "__main__":
    sys.exit(main())

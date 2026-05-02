"""Daily batch pull of curated X accounts → digest markdown.

Generic, project-agnostic. Caller supplies:
  - --config: JSON file with curated account list
  - --tracked-tickers-file (optional): newline-delimited tickers we already track
  - --themes-dir (optional): dir with theme files (lists shown in digest header)
  - --digest-out (optional): where to write the markdown digest

Cost discipline:
  - Preflight projection — refuses to run if max projected cost exceeds
    --max-run-usd (default $3, the project cost-approval gate)
  - Per-account budget assertion — checks the global ledger before each call
    so an in-flight run can't exceed --monthly-cap (default $100)
  - Per-account log_cost — partial spend is recorded even if process crashes
  - Global ledger at ~/.local/state/x-api/cost_ledger.jsonl with fcntl locking

Usage:
    python3 ~/Projects/skills/x-api/scripts/pull.py --config accounts.json
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from x_api import (
    COST_TWEET_READ,
    COST_USER_LOOKUP,
    BudgetExceeded,
    CostTally,
    RateLimitExceeded,
    assert_budget,
    get_user,
    get_user_tweets,
    load_token_from_dotenv,
    log_cost,
    month_to_date_usd,
)

# Allow at least 2 chars after the $ to avoid matching $M / $B / $T
# (money-unit abbreviations) as tickers. Single-letter tickers like $F or $T
# slip through here — server-side entities.cashtags is the primary path
# anyway and X's own tagger correctly handles single-letter tickers.
CASHTAG_FALLBACK = re.compile(r"\$([A-Za-z][A-Za-z0-9.]{1,6})\b")
MATERIAL_KEYWORDS = re.compile(
    r"\b(earnings|guidance|contract|deal|partnership|acquisition|"
    r"merger|order|qualified|customer win|design win|FDA|clinical|"
    r"approval|investigation|lawsuit|short report|insider|buyback|"
    r"dilution|ATM|RFQ|tender|warrant|IPO|listing|10-K|10-Q|8-K)\b",
    re.IGNORECASE,
)


def load_tracked(path: Path | None) -> set[str]:
    if path is None or not path.exists():
        return set()
    out = set()
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or line.startswith("_"):
            continue
        out.add(line.upper())
        out.add(line.split(".")[0].upper())
    return out


def list_themes(path: Path | None) -> list[str]:
    if path is None or not path.exists():
        return []
    return sorted(p.stem for p in path.glob("*.md") if p.stem != "README")


def extract_cashtags(tweet: dict) -> set[str]:
    """Prefer X server-side `entities.cashtags`; regex fallback on text."""
    tags: set[str] = set()
    cashtags = (tweet.get("entities") or {}).get("cashtags") or []
    for c in cashtags:
        tag = (c.get("tag") or "").upper()
        if tag:
            tags.add(tag)
    if not tags:
        for m in CASHTAG_FALLBACK.finditer(tweet.get("text", "")):
            tags.add(m.group(1).upper())
    return tags


def is_material(text: str) -> bool:
    return bool(MATERIAL_KEYWORDS.search(text))


def format_tweet(t: dict, username: str) -> str:
    m = t.get("public_metrics", {})
    text = t["text"].replace("\n", " ").strip()
    if len(text) > 400:
        text = text[:397] + "..."
    url = f"https://x.com/{username}/status/{t['id']}"
    return (
        f"- **{t['created_at'][:16]}Z** "
        f"likes={m.get('like_count')} rts={m.get('retweet_count')} "
        f"impr={m.get('impression_count')}  [link]({url})\n"
        f"  > {text}"
    )


def project_max_cost(accounts: list[dict], max_pages: int) -> float:
    """Worst-case spend if every account hits max pagination.

    Per account: 1 user lookup IF user_id missing from config + (max_pages * 100)
    tweet reads.
    """
    user_calls = sum(1 for a in accounts if not a.get("user_id"))
    tweet_calls = len(accounts) * max_pages * 100
    return user_calls * COST_USER_LOOKUP + tweet_calls * COST_TWEET_READ


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", required=True,
                    help="JSON file with curated account list (key 'accounts')")
    ap.add_argument("--since-hours", type=int, default=24)
    ap.add_argument("--max-pages", type=int, default=2,
                    help="Pages per account; cap is max_pages * 100 tweets")
    ap.add_argument("--tracked-tickers-file",
                    help="Newline-delimited tickers we already track")
    ap.add_argument("--themes-dir",
                    help="Dir with theme *.md files (listed in digest header)")
    ap.add_argument("--digest-out",
                    help="Output markdown path (default: .scratch/social_digest_<date>.md)")
    ap.add_argument("--monthly-cap", type=float, default=100.0,
                    help="Hard monthly spend cap (USD)")
    ap.add_argument("--max-run-usd", type=float, default=3.0,
                    help="Per-run projection cap (USD). Project policy: actions "
                         ">$3 require explicit approval — pass a higher value to "
                         "authorize larger runs.")
    args = ap.parse_args()

    load_token_from_dotenv()

    cfg = json.loads(Path(args.config).read_text())
    accounts = cfg["accounts"]
    print(f"[accounts] {len(accounts)} curated")

    projected = project_max_cost(accounts, args.max_pages)
    print(f"[preflight] worst-case projection: ${projected:.2f}  "
          f"(--max-run-usd={args.max_run_usd:.2f})")
    if projected > args.max_run_usd:
        sys.exit(
            f"BLOCKED: projected ${projected:.2f} exceeds --max-run-usd "
            f"${args.max_run_usd:.2f}. Re-run with --max-run-usd {projected:.2f} "
            f"to authorize, or reduce --max-pages / accounts."
        )

    mtd_start = month_to_date_usd()
    if mtd_start >= args.monthly_cap:
        sys.exit(f"BLOCKED: month-to-date ${mtd_start:.2f} reached "
                 f"${args.monthly_cap:.2f} cap")
    print(f"[budget] month-to-date=${mtd_start:.2f} / cap=${args.monthly_cap}")

    since = datetime.now(timezone.utc) - timedelta(hours=args.since_hours)
    start_time = since.strftime("%Y-%m-%dT%H:%M:%SZ")
    print(f"[window] since {start_time} ({args.since_hours}h)")

    tracked = load_tracked(Path(args.tracked_tickers_file)
                           if args.tracked_tickers_file else None)
    themes = list_themes(Path(args.themes_dir) if args.themes_dir else None)

    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    digest: list[str] = []
    digest.append(f"# X Social Digest — {today}")
    digest.append("")
    digest.append(
        f"_Window: last {args.since_hours}h. "
        f"Accounts: {len(accounts)}. "
        f"Tracked universe: {len(tracked)} tickers. "
        f"Themes: {', '.join(themes) or '(none)'}._"
    )
    digest.append("")

    all_ticker_counts: Counter[str] = Counter()
    untracked_hits: dict[str, list[str]] = {}
    total_spend = 0.0  # rolling spend across accounts in this run

    for acct in accounts:
        username = acct["username"]
        tally = CostTally()  # fresh per-account so log_cost is granular
        print(f"\n[pull] @{username}")

        # Per-account budget assertion BEFORE the call. Worst-case for this
        # account = 1 user lookup (if missing user_id) + max_pages * 100 tweets.
        per_account_max = (
            (0 if acct.get("user_id") else COST_USER_LOOKUP)
            + args.max_pages * 100 * COST_TWEET_READ
        )
        try:
            assert_budget(args.monthly_cap, per_account_max, in_flight=total_spend)
        except BudgetExceeded as e:
            print(f"  BUDGET STOP: {e}")
            digest.append(f"## @{username} — STOPPED (budget): {e}\n")
            break

        try:
            user_id = acct.get("user_id")
            if user_id:
                # Skip $0.01 user lookup when ID is cached in config
                user = {"id": user_id, "name": acct.get("display_name", username)}
            else:
                user = get_user(username, tally=tally)
            tweets = get_user_tweets(
                user["id"],
                max_results=100,
                start_time=start_time,
                max_pages=args.max_pages,
                tally=tally,
            )
        except RateLimitExceeded as e:
            print(f"  RATE-LIMITED: skipping (reset in {e.wait_seconds}s)")
            digest.append(f"## @{username} — SKIPPED (rate limit, "
                          f"reset in {e.wait_seconds}s)\n")
            log_cost(tally, label=f"x_api_pull/{username} (rate-limited)")
            total_spend += tally.usd
            continue
        except Exception as e:
            print(f"  ERROR: {e}")
            digest.append(f"## @{username} — ERROR: {e}\n")
            log_cost(tally, label=f"x_api_pull/{username} (error)")
            total_spend += tally.usd
            continue

        material = [t for t in tweets if is_material(t["text"])]
        ticker_hits = []
        for t in tweets:
            tags = extract_cashtags(t)
            if tags:
                ticker_hits.append((t, tags))
                for tag in tags:
                    all_ticker_counts[tag] += 1
                    if tracked and tag not in tracked:
                        untracked_hits.setdefault(tag, []).append(username)

        # Log cost FIRST so a crash during digest formatting still records spend
        log_cost(tally, label=f"x_api_pull/{username}")
        total_spend += tally.usd

        print(f"  pulled={len(tweets)}  material={len(material)}  "
              f"with_tickers={len(ticker_hits)}  spend=${tally.usd:.3f}")

        digest.append(f"## @{username}")
        sig = acct.get("track_record_signal")
        sig_str = f"{sig:.0%}" if sig is not None else "n/a"
        digest.append(
            f"_Signal: {sig_str}. Pulled {len(tweets)} tweets, "
            f"{len(material)} material, {len(ticker_hits)} with tickers._"
        )
        digest.append("")

        if not tweets:
            digest.append("_No new tweets in window._\n")
            continue

        priority = [t for t, _ in ticker_hits if is_material(t["text"])]
        ticker_only = [t for t, _ in ticker_hits if not is_material(t["text"])]
        material_no_ticker = [t for t in material if not extract_cashtags(t)]

        if priority:
            digest.append("### Material claims with tickers")
            for t in priority[:20]:
                digest.append(format_tweet(t, username))
            digest.append("")
        if ticker_only:
            digest.append("### Ticker mentions (non-material)")
            for t in ticker_only[:10]:
                digest.append(format_tweet(t, username))
            digest.append("")
        if material_no_ticker:
            digest.append("### Material claims (no ticker)")
            for t in material_no_ticker[:5]:
                digest.append(format_tweet(t, username))
            digest.append("")

    digest.append("---\n")
    digest.append("## Ticker frequency (this run)")
    digest.append("")
    digest.append("| Ticker | Mentions | Tracked? |")
    digest.append("|---|---:|:---:|")
    for tag, n in all_ticker_counts.most_common(30):
        ok = "YES" if tracked and tag in tracked else "—"
        digest.append(f"| ${tag} | {n} | {ok} |")
    digest.append("")

    if untracked_hits:
        digest.append("## Untracked candidates (≥3 mentions)")
        digest.append("")
        for tag, hitters in sorted(untracked_hits.items(),
                                    key=lambda kv: -all_ticker_counts[kv[0]]):
            n = all_ticker_counts[tag]
            if n < 3:
                continue
            who = ", ".join(f"@{u}" for u in set(hitters))
            digest.append(f"- **${tag}** — {n} mentions from {who}")
        digest.append("")

    digest.append("---\n")
    digest.append(
        f"_Run spend: ${total_spend:.3f}. "
        f"MTD before run: ${mtd_start:.2f}. "
        f"MTD after run: ${mtd_start + total_spend:.2f}._"
    )

    out_path = (Path(args.digest_out) if args.digest_out
                else Path(".scratch") / f"social_digest_{today}.md")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text("\n".join(digest))

    print(f"\n[digest] {out_path}")
    print(f"[cost]   ${total_spend:.3f} this run, "
          f"${mtd_start + total_spend:.2f} MTD")
    return 0


if __name__ == "__main__":
    sys.exit(main())

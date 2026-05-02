"""Daily batch pull of curated X accounts → digest markdown.

Generic, project-agnostic. Caller supplies:
  - --config: JSON file with curated account list
  - --tracked-tickers-file (optional): newline-delimited tickers we already track
  - --themes-dir (optional): dir with theme files (lists shown in digest header)
  - --digest-out (optional): where to write the markdown digest

$100/month hard cap. Refuses to run if MTD > cap.

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
    CostTally,
    get_user,
    get_user_tweets,
    load_token_from_dotenv,
    log_cost,
    month_to_date_usd,
)

MONTHLY_HARD_CAP = 100.0  # USD

CASHTAG_FALLBACK = re.compile(r"\$([A-Z][A-Z0-9.]{0,6})\b")
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


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", required=True,
                    help="JSON file with curated account list (key 'accounts')")
    ap.add_argument("--since-hours", type=int, default=24)
    ap.add_argument("--max-pages", type=int, default=2,
                    help="Pages per account; cap is max_pages * 100 tweets")
    ap.add_argument("--tracked-tickers-file",
                    help="Newline-delimited tickers we already track (for coverage delta)")
    ap.add_argument("--themes-dir",
                    help="Dir with theme *.md files (listed in digest header)")
    ap.add_argument("--digest-out",
                    help="Output markdown path (default: .scratch/social_digest_<date>.md)")
    args = ap.parse_args()

    load_token_from_dotenv()

    mtd = month_to_date_usd()
    if mtd > MONTHLY_HARD_CAP:
        sys.exit(f"BLOCKED: month-to-date ${mtd:.2f} exceeds ${MONTHLY_HARD_CAP} cap")
    print(f"[budget] month-to-date=${mtd:.2f} / cap=${MONTHLY_HARD_CAP}")

    cfg = json.loads(Path(args.config).read_text())
    accounts = cfg["accounts"]
    print(f"[accounts] {len(accounts)} curated")

    since = datetime.now(timezone.utc) - timedelta(hours=args.since_hours)
    start_time = since.strftime("%Y-%m-%dT%H:%M:%SZ")
    print(f"[window] since {start_time} ({args.since_hours}h)")

    tracked = load_tracked(Path(args.tracked_tickers_file)
                           if args.tracked_tickers_file else None)
    themes = list_themes(Path(args.themes_dir) if args.themes_dir else None)
    tally = CostTally()

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

    for acct in accounts:
        username = acct["username"]
        print(f"\n[pull] @{username}")
        try:
            user = get_user(username, tally=tally)
            tweets = get_user_tweets(
                user["id"],
                max_results=100,
                start_time=start_time,
                max_pages=args.max_pages,
                tally=tally,
            )
        except Exception as e:
            print(f"  ERROR: {e}")
            digest.append(f"## @{username} — ERROR: {e}\n")
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

        print(f"  pulled={len(tweets)}  material={len(material)}  "
              f"with_tickers={len(ticker_hits)}")

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
        f"_Cost this run: ${tally.usd:.3f} "
        f"({tally.user_lookups} user × $0.010 + {tally.tweet_reads} tweet × $0.005). "
        f"MTD after run: ${mtd + tally.usd:.2f}._"
    )

    out_path = (Path(args.digest_out) if args.digest_out
                else Path(".scratch") / f"social_digest_{today}.md")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text("\n".join(digest))
    log_cost(tally, label=f"x_api_pull --since-hours {args.since_hours}")

    print(f"\n[digest] {out_path}")
    print(f"[cost]   ${tally.usd:.3f} this run, "
          f"${mtd + tally.usd:.2f} MTD")
    return 0


if __name__ == "__main__":
    sys.exit(main())

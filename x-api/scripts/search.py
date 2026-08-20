"""Full-archive X search — the third leg beside probe.py and pull.py.

Promoted 2026-08-20 after being hand-rolled 4x across two iq-sex-differences
sessions (discourse harvests). Wraps /2/tweets/search/all with the house
cost-ledger discipline and the hard-won operational lessons baked in:

  * verify handles BEFORE from:-queries — a wrong training-data handle reads
    as a silent zero (and squatter accounts shadow real people; a 2-follower
    "sashagusev" burned a query slot before verification was added)
  * quotes carry commentary, pure RTs only carry reach: default excludes
    retweets but INCLUDES quotes; pass --with-retweets to keep RTs
  * phrase-anchored methods-jargon queries return near-zero — search the
    discourse's own vocabulary, and treat a zero as "not keyword-reachable
    in this phrasing," never "does not exist"
  * search/all: ~1 req/sec on this tier; 429s get one 16s retry
  * every returned post is billed ($0.005) — cap pages deliberately

Usage:
  search.py query 'QUERY' [--pages 1] [--max 100] [--out FILE.jsonl] [--label L]
  search.py verify HANDLE [HANDLE ...]
  search.py thread CONVERSATION_ID [--author HANDLE] [--out FILE.jsonl]

Query syntax refs: from:user, is:quote, -is:retweet, lang:en, conversation_id:.
Output: JSONL, one enriched tweet per line (username + author_followers joined
from expansions). Cost is logged to the wallet-scoped ledger per invocation.
"""
import argparse
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from x_api import CostTally, load_token_from_dotenv, log_cost  # noqa: E402

import os  # noqa: E402

import requests  # noqa: E402

API = "https://api.x.com/2"
FIELDS = "created_at,public_metrics,author_id,conversation_id,referenced_tweets"


def _headers() -> dict:
    load_token_from_dotenv()
    tok = os.environ.get("X_API_BEARER_TOKEN")
    if not tok:
        sys.exit("X_API_BEARER_TOKEN not set (checked shell env, .env.local, .env, ~/.env)")
    return {"Authorization": f"Bearer {tok}", "User-Agent": "x-api-skill/search"}


def _get(url: str, params: dict, retried: bool = False) -> dict:
    r = requests.get(url, headers=_headers(), params=params, timeout=30)
    if r.status_code == 429 and not retried:
        time.sleep(16)
        return _get(url, params, retried=True)
    if r.status_code == 402:
        sys.exit("402 credits depleted — vendor-side balance, top up at developer.x.com "
                 "(NOT the local $100/mo ledger cap)")
    r.raise_for_status()
    return r.json()


def _enrich(body: dict) -> list[dict]:
    users = {u["id"]: u for u in body.get("includes", {}).get("users", [])}
    tweets = body.get("data", [])
    for t in tweets:
        u = users.get(t.get("author_id"), {})
        t["username"] = u.get("username")
        t["author_followers"] = (u.get("public_metrics") or {}).get("followers_count")
    return tweets


def search_all(query: str, pages: int, max_results: int, tally: CostTally) -> list[dict]:
    rows: list[dict] = []
    next_token = None
    for _ in range(pages):
        params = {"query": query, "max_results": max_results, "tweet.fields": FIELDS,
                  "expansions": "author_id", "user.fields": "username,public_metrics"}
        if next_token:
            params["next_token"] = next_token
        body = _get(f"{API}/tweets/search/all", params)
        got = _enrich(body)
        tally.tweet_reads += len(got)
        rows.extend(got)
        next_token = body.get("meta", {}).get("next_token")
        if not next_token:
            break
        time.sleep(1.2)
    return rows


def verify_handles(handles: list[str], tally: CostTally) -> dict[str, dict]:
    """Batch-verify usernames. Returns {handle: {followers, id}} for the ones
    that exist; prints missing ones. Flags likely squatters (<100 followers on
    a name you expected to be a public figure is a smell, not proof)."""
    body = _get(f"{API}/users/by",
                {"usernames": ",".join(handles), "user.fields": "public_metrics"})
    tally.user_lookups += len(handles)
    ok = {u["username"]: {"id": u["id"],
                          "followers": u["public_metrics"]["followers_count"]}
          for u in body.get("data", [])}
    missing = [e.get("value") for e in body.get("errors", [])]
    for h, meta in sorted(ok.items(), key=lambda kv: -kv[1]["followers"]):
        flag = "  [<100 fol — possible squatter]" if meta["followers"] < 100 else ""
        print(f"  @{h}  {meta['followers']:,} fol{flag}")
    if missing:
        print(f"  missing: {missing}")
    return ok


def pull_thread(conversation_id: str, author: str | None, tally: CostTally) -> list[dict]:
    q = f"conversation_id:{conversation_id}"
    if author:
        q += f" from:{author}"
    rows = search_all(q, pages=1, max_results=100, tally=tally)
    rows.sort(key=lambda t: t.get("created_at", ""))
    return rows


def main() -> None:
    ap = argparse.ArgumentParser(description=(__doc__ or "").split("\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)

    q = sub.add_parser("query", help="full-archive search")
    q.add_argument("query")
    q.add_argument("--pages", type=int, default=1)
    q.add_argument("--max", type=int, default=100, dest="max_results")
    q.add_argument("--out", type=Path, default=None)
    q.add_argument("--label", default="x_search")
    q.add_argument("--with-retweets", action="store_true",
                   help="do not auto-append -is:retweet")

    v = sub.add_parser("verify", help="batch handle verification")
    v.add_argument("handles", nargs="+")

    t = sub.add_parser("thread", help="pull a conversation")
    t.add_argument("conversation_id")
    t.add_argument("--author", default=None)
    t.add_argument("--out", type=Path, default=None)

    args = ap.parse_args()
    tally = CostTally()

    if args.cmd == "verify":
        verify_handles(args.handles, tally)
        log_cost(tally, "x_search/verify")
        print(f"cost ${tally.usd:.3f}")
        return

    if args.cmd == "query":
        query = args.query
        if "-is:retweet" not in query and "is:retweet" not in query \
                and not args.with_retweets:
            query += " -is:retweet"
        rows = search_all(query, args.pages, args.max_results, tally)
        label = args.label
    else:  # thread
        rows = pull_thread(args.conversation_id, args.author, tally)
        label = "x_search/thread"

    if args.out:
        with args.out.open("w") as fh:
            for r in rows:
                fh.write(json.dumps(r) + "\n")
        print(f"{len(rows)} posts -> {args.out}")
    else:
        for r in sorted(rows, key=lambda x: -(x.get("public_metrics") or {}).get("like_count", 0)):
            pm = r.get("public_metrics") or {}
            text = r.get("text", "").replace("\n", " ")[:240]
            print(f"@{r.get('username')} ({r.get('author_followers')}f) "
                  f"{pm.get('like_count')}L {r.get('created_at', '')[:10]}: {text}")
    log_cost(tally, label)
    print(f"cost ${tally.usd:.3f} · {tally.tweet_reads} reads, {tally.user_lookups} lookups")


if __name__ == "__main__":
    main()

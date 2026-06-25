"""
scrape_targeted.py — Reddit listing scraper for r/FullmetalAlchemist and r/evangelion.

Uses Reddit's public top-post listing endpoint (same approach as scrape.py — proven to work).
Keyword search is done client-side after fetching, since Reddit's /search endpoint returns 403.

Three passes per subreddit:
  1. Meme-register  — short posts or posts containing internet-slang signals → oversample Reactive
  2. Informational  — question-titled posts + long explanatory comments → oversample Informational
  3. General        — all remaining unseen posts → balanced coverage

Output: dataset_targeted.csv  (same schema as dataset.csv, labels left blank)

Run:
    python scrape_targeted.py
"""
import csv
import re
import time
from pathlib import Path
import requests

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

OUTPUT = Path(__file__).parent / "dataset_targeted.csv"
FIELDS = ["id", "type", "post_title", "text", "author", "score", "url", "flair", "label"]

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/125.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json",
}

SUBREDDITS = [
    {"name": "FullmetalAlchemist", "display": "FMA"},
    {"name": "evangelion",         "display": "NGE"},
]

MEME_SIGNALS = {
    "unironically", "roman empire", "rent free", "ngl", "based",
    "cope", "lmao", "bruh", "no thoughts", "sending me",
    "i cannot", "bestie", "crying", "vocal stim",
    "living in my head", "that's it", "💀", "😭",
}

FETCH_TARGET      = 300   # posts to pull per subreddit before filtering
COMMENTS_PER_POST = 3     # top-level comments per post
SLEEP             = 1.0   # seconds between requests


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _safe_print(msg: str) -> None:
    print(msg.encode("cp1252", errors="replace").decode("cp1252"))


def _clean(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "")).strip()


def _has_meme_signal(text: str) -> bool:
    lower = text.lower()
    return any(s in lower for s in MEME_SIGNALS)


def _word_count(text: str) -> int:
    return len(text.split())


def _load_existing_ids() -> set[str]:
    existing = Path(__file__).parent / "dataset.csv"
    if not existing.exists():
        return set()
    with open(existing, newline="", encoding="utf-8") as f:
        return {row["id"] for row in csv.DictReader(f) if row.get("id")}


# ---------------------------------------------------------------------------
# Reddit API calls  (listing endpoint — same as scrape.py)
# ---------------------------------------------------------------------------

def _fetch_posts_page(subreddit: str, after: str | None = None) -> tuple[list[dict], str | None]:
    params: dict = {"sort": "top", "t": "all", "limit": 100, "raw_json": 1}
    if after:
        params["after"] = after
    try:
        resp = requests.get(
            f"https://www.reddit.com/r/{subreddit}/top.json",
            params=params, headers=HEADERS, timeout=20,
        )
        resp.raise_for_status()
        data = resp.json()["data"]
        posts = [c["data"] for c in data["children"] if c.get("kind") == "t3"]
        return posts, data.get("after")
    except Exception as e:
        _safe_print(f"    [warn] fetch failed: {e}")
        return [], None


def _fetch_comments(subreddit: str, post_id: str) -> list[dict]:
    try:
        resp = requests.get(
            f"https://www.reddit.com/r/{subreddit}/comments/{post_id}.json",
            params={"limit": COMMENTS_PER_POST * 3, "sort": "top", "depth": 1, "raw_json": 1},
            headers=HEADERS, timeout=20,
        )
        resp.raise_for_status()
        children = resp.json()[1]["data"]["children"]
        return [c["data"] for c in children if c.get("kind") == "t1"]
    except Exception:
        return []


def _collect_posts(subreddit: str, display: str, target: int = FETCH_TARGET) -> list[dict]:
    """Page through top posts until we have enough to filter from."""
    all_posts: list[dict] = []
    after: str | None = None
    while len(all_posts) < target:
        batch, after = _fetch_posts_page(subreddit, after=after)
        if not batch:
            break
        all_posts.extend(batch)
        _safe_print(f"    [{display}] fetched {len(all_posts)} posts...")
        time.sleep(SLEEP)
        if not after:
            break
    return all_posts


# ---------------------------------------------------------------------------
# Normalise
# ---------------------------------------------------------------------------

def _norm_post(p: dict, subreddit: str) -> dict:
    pid   = p.get("id", "")
    title = _clean(p.get("title", ""))
    body  = _clean(p.get("selftext", "") or "")
    if body in ("[deleted]", "[removed]"):
        body = ""
    text = f"{title}. {body}".rstrip(". ") if body else title
    return {
        "id":         f"t3_{pid}",
        "type":       "post",
        "post_title": title,
        "text":       text,
        "author":     "",
        "score":      p.get("score", 0),
        "url":        f"https://www.reddit.com/r/{subreddit}/comments/{pid}/",
        "flair":      _clean(p.get("link_flair_text", "") or "Discussion"),
        "label":      "",
    }


def _norm_comment(c: dict, post_title: str, post_url: str) -> dict:
    return {
        "id":         f"t1_{c.get('id', '')}",
        "type":       "comment",
        "post_title": post_title,
        "text":       _clean(c.get("body", "")),
        "author":     "",
        "score":      c.get("score", 0),
        "url":        post_url,
        "flair":      "",
        "label":      "",
    }


def _add_comments(subreddit: str, p: dict, post_row: dict,
                  seen: set[str], rows: list[dict], filter_fn=None) -> None:
    comments = _fetch_comments(subreddit, p["id"])
    time.sleep(SLEEP)
    added = 0
    for c in comments:
        if added >= COMMENTS_PER_POST:
            break
        cid  = f"t1_{c.get('id', '')}"
        body = _clean(c.get("body", ""))
        if not c.get("id") or cid in seen:
            continue
        if not body or body in ("[deleted]", "[removed]"):
            continue
        if filter_fn and not filter_fn(body):
            continue
        seen.add(cid)
        rows.append(_norm_comment(c, post_row["post_title"], post_row["url"]))
        added += 1


# ---------------------------------------------------------------------------
# Three passes (client-side filtering on the fetched post list)
# ---------------------------------------------------------------------------

def _meme_pass(posts: list[dict], subreddit: str, display: str,
               seen: set[str], rows: list[dict]) -> None:
    _safe_print(f"\n  [{display}] Meme-register pass...")
    found = 0
    for p in posts:
        pid  = p.get("id", "")
        full = f"t3_{pid}"
        if not pid or full in seen:
            continue
        title    = _clean(p.get("title", ""))
        body     = _clean(p.get("selftext", "") or "")
        combined = f"{title} {body}"
        if not (_has_meme_signal(combined) or _word_count(combined) < 80):
            continue
        seen.add(full)
        row = _norm_post(p, subreddit)
        rows.append(row)
        _safe_print(f"      [meme] {title[:70]}")
        _add_comments(subreddit, p, row, seen, rows,
                      filter_fn=lambda t: _has_meme_signal(t) or _word_count(t) < 60)
        found += 1
    _safe_print(f"    -> {found} posts matched")


def _informational_pass(posts: list[dict], subreddit: str, display: str,
                        seen: set[str], rows: list[dict]) -> None:
    _safe_print(f"\n  [{display}] Informational pass...")
    found = 0
    for p in posts:
        pid  = p.get("id", "")
        full = f"t3_{pid}"
        if not pid or full in seen:
            continue
        title = p.get("title", "")
        tl    = title.lower()
        is_q  = "?" in title or any(
            tl.startswith(w)
            for w in ("why", "how", "what", "when", "where", "did", "does",
                      "is ", "are ", "can ", "explain", "help")
        )
        if not is_q:
            continue
        seen.add(full)
        row = _norm_post(p, subreddit)
        rows.append(row)
        _safe_print(f"      [info] {title[:70]}")
        _add_comments(subreddit, p, row, seen, rows,
                      filter_fn=lambda t: _word_count(t) >= 80)
        found += 1
    _safe_print(f"    -> {found} posts matched")


def _general_pass(posts: list[dict], subreddit: str, display: str,
                  seen: set[str], rows: list[dict]) -> None:
    _safe_print(f"\n  [{display}] General pass (unseen posts)...")
    found = 0
    for p in posts:
        pid  = p.get("id", "")
        full = f"t3_{pid}"
        if not pid or full in seen:
            continue
        seen.add(full)
        row = _norm_post(p, subreddit)
        rows.append(row)
        _add_comments(subreddit, p, row, seen, rows, filter_fn=None)
        found += 1
    _safe_print(f"    -> {found} posts matched")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    existing_ids = _load_existing_ids()
    _safe_print(f"Loaded {len(existing_ids)} existing IDs to skip.")

    rows: list[dict] = []
    seen: set[str]   = set(existing_ids)

    for sub in SUBREDDITS:
        name, display = sub["name"], sub["display"]
        _safe_print(f"\n{'='*60}")
        _safe_print(f"  Subreddit: r/{name} ({display})")
        _safe_print(f"{'='*60}")

        posts = _collect_posts(name, display)
        _safe_print(f"  Total fetched: {len(posts)} posts")

        _meme_pass(posts, name, display, seen, rows)
        _informational_pass(posts, name, display, seen, rows)
        _general_pass(posts, name, display, seen, rows)

    _safe_print(f"\nCollected {len(rows)} new rows total.")
    _safe_print(f"  posts:    {sum(1 for r in rows if r['type'] == 'post')}")
    _safe_print(f"  comments: {sum(1 for r in rows if r['type'] == 'comment')}")

    with open(OUTPUT, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)

    _safe_print(f"\nSaved -> {OUTPUT}")
    _safe_print("Next: label dataset_targeted.csv then merge into dataset.csv.")


if __name__ == "__main__":
    main()

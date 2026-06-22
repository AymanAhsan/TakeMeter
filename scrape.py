"""
TakeMeter scraper — r/attackontitan Discussion/Question flair.

Uses Reddit's public JSON API (no credentials required).
Collects up to TARGET posts+comments combined and writes to dataset.csv.
"""

import csv
import time
import requests
from pathlib import Path

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/125.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json",
    "Accept-Language": "en-US,en;q=0.9",
}

CSV_PATH = Path(__file__).parent / "dataset.csv"
CSV_FIELDS = ["id", "type", "title", "text", "author", "score", "url", "flair", "label"]

TARGET = 100
COMMENTS_PER_POST = 3   # top-level comments to grab per post
SLEEP_BETWEEN_POSTS = 1  # seconds (Reddit asks ≥1s between requests)


# ---------------------------------------------------------------------------
# Fetch helpers
# ---------------------------------------------------------------------------

def fetch_posts(limit: int = 25, after: str | None = None) -> tuple[list, str | None]:
    """Return (children, next_after) using the flair listing endpoint."""
    params: dict = {
        "f": 'flair_name:"Discussion/Question"',
        "sort": "top",
        "t": "all",
        "limit": limit,
        "raw_json": 1,
    }
    if after:
        params["after"] = after

    resp = requests.get(
        "https://www.reddit.com/r/attackontitan/.json",
        params=params,
        headers=HEADERS,
        timeout=20,
    )
    resp.raise_for_status()
    data = resp.json()["data"]
    return data["children"], data.get("after")


def fetch_top_comments(post_id: str, n: int = 5) -> list[dict]:
    """Return up to n top-level comments for a post."""
    resp = requests.get(
        f"https://www.reddit.com/r/attackontitan/comments/{post_id}.json",
        params={"limit": n, "sort": "top", "depth": 1},
        headers=HEADERS,
        timeout=20,
    )
    if resp.status_code != 200:
        return []
    try:
        comment_listing = resp.json()[1]["data"]["children"]
    except (IndexError, KeyError):
        return []

    result = []
    for child in comment_listing:
        if child.get("kind") != "t1":
            continue
        body = child["data"].get("body", "").strip()
        if body and body not in ("[deleted]", "[removed]"):
            result.append(child["data"])
    return result


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    items: list[dict] = []
    seen: set[str] = set()
    after: str | None = None

    print(f"Scraping r/attackontitan (Discussion/Question) -> target {TARGET} items\n")

    while len(items) < TARGET:
        posts, after = fetch_posts(limit=25, after=after)
        if not posts:
            print("No more posts returned.")
            break

        for child in posts:
            if len(items) >= TARGET:
                break

            p = child["data"]
            pid = p["id"]
            if pid in seen:
                continue
            seen.add(pid)

            title = p.get("title", "").strip()
            text = p.get("selftext", "").strip()
            if not title:
                continue

            post_row = {
                "id": f"t3_{pid}",
                "type": "post",
                "title": title,
                "text": text,
                "author": p.get("author", ""),
                "score": p.get("score", 0),
                "url": f"https://www.reddit.com{p.get('permalink', '')}",
                "flair": p.get("link_flair_text", "Discussion/Question"),
                "label": "",
            }
            items.append(post_row)
            print(f"[{len(items):>3}] POST  {title[:70]}")

            # --- top comments for this post ---
            if len(items) < TARGET:
                try:
                    comments = fetch_top_comments(pid, n=COMMENTS_PER_POST + 2)
                    for c in comments[:COMMENTS_PER_POST]:
                        if len(items) >= TARGET:
                            break
                        cid = c["id"]
                        if cid in seen:
                            continue
                        seen.add(cid)
                        items.append({
                            "id": f"t1_{cid}",
                            "type": "comment",
                            "title": title,
                            "text": c.get("body", "").strip(),
                            "author": c.get("author", ""),
                            "score": c.get("score", 0),
                            "url": f"https://www.reddit.com{c.get('permalink', '')}",
                            "flair": p.get("link_flair_text", "Discussion/Question"),
                            "label": "",
                        })
                        print(f"[{len(items):>3}]   COMMENT  {c.get('body', '')[:60]!r}")
                except Exception as exc:
                    print(f"      [warn] comments failed for {pid}: {exc}")

            time.sleep(SLEEP_BETWEEN_POSTS)

        if not after:
            print("Reached last page of results.")
            break

        print(f"  -> page done, {len(items)} items so far, fetching next page...")
        time.sleep(2)

    items = items[:TARGET]
    print(f"\nCollected {len(items)} items total.")

    with open(CSV_PATH, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_FIELDS)
        writer.writeheader()
        writer.writerows(items)

    print(f"Saved → {CSV_PATH}")
    label_dist = {"post": 0, "comment": 0}
    for item in items:
        label_dist[item["type"]] += 1
    print(f"  posts: {label_dist['post']}  comments: {label_dist['comment']}")


if __name__ == "__main__":
    main()

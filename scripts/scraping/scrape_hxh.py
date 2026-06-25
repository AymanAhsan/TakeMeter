"""
Scrape r/HunterXHunter Discussion flair posts + top comments via PullPush API.
Appends 200 entries to dataset.csv.
"""

import csv
import time
import requests

DATASET = "dataset.csv"
TARGET = 200
SUBREDDIT = "HunterXHunter"
FLAIR = "Discussion"
COMMENTS_PER_POST = 4

BASE = "https://api.pullpush.io/reddit/search"


def _p(msg: str) -> None:
    """Print safely on Windows terminals that can't handle all Unicode."""
    safe = msg.encode("cp1252", errors="replace").decode("cp1252")
    print(safe)


def fetch_posts(before: int = 0, size: int = 25) -> list[dict]:
    params = {
        "subreddit": SUBREDDIT,
        "link_flair_text": FLAIR,
        "size": size,
        "sort": "desc",
        "sort_type": "created_utc",
    }
    if before:
        params["before"] = before
    resp = requests.get(f"{BASE}/submission/", params=params, timeout=30)
    resp.raise_for_status()
    return resp.json().get("data", [])


def fetch_comments(link_id: str, size: int = 10) -> list[dict]:
    params = {
        "link_id": link_id,
        "size": size,
        "sort": "desc",
        "sort_type": "score",
    }
    resp = requests.get(f"{BASE}/comment/", params=params, timeout=30)
    resp.raise_for_status()
    return resp.json().get("data", [])


def clean(text: str) -> str:
    return (text or "").replace("\n", " ").replace("\r", " ").strip()


def main():
    entries = []
    seen_ids: set[str] = set()
    before = 0

    _p(f"Collecting {TARGET} entries from r/{SUBREDDIT} [{FLAIR}] via PullPush...")

    while len(entries) < TARGET:
        try:
            posts = fetch_posts(before=before, size=25)
        except Exception as e:
            _p(f"  [!] fetch_posts failed: {e}")
            break

        if not posts:
            _p("  [!] No more posts.")
            break

        for p in posts:
            if len(entries) >= TARGET:
                break

            post_id = p.get("id", "")
            full_id = f"t3_{post_id}"
            if full_id in seen_ids:
                continue
            seen_ids.add(full_id)

            title = clean(p.get("title", ""))
            selftext = clean(p.get("selftext", ""))
            score = p.get("score", 0)
            url = f"https://www.reddit.com/r/{SUBREDDIT}/comments/{post_id}/"
            flair_text = clean(p.get("link_flair_text", FLAIR)) or FLAIR

            entries.append({
                "id": full_id,
                "type": "post",
                "post_title": title,
                "text": selftext,
                "author": "",
                "score": score,
                "url": url,
                "flair": flair_text,
                "label": "",
            })
            _p(f"  [{len(entries):3d}] POST: {title[:65]}")

            if len(entries) >= TARGET:
                break

            time.sleep(0.4)
            try:
                comments = fetch_comments(link_id=post_id, size=COMMENTS_PER_POST)
            except Exception as e:
                _p(f"         [!] comments failed for {post_id}: {e}")
                comments = []

            for c in comments[:COMMENTS_PER_POST]:
                if len(entries) >= TARGET:
                    break
                cid = f"t1_{c.get('id', '')}"
                if cid in seen_ids:
                    continue
                seen_ids.add(cid)
                body = clean(c.get("body", ""))
                if not body or body in ("[deleted]", "[removed]"):
                    continue
                entries.append({
                    "id": cid,
                    "type": "comment",
                    "post_title": title,
                    "text": body,
                    "author": "",
                    "score": c.get("score", 0),
                    "url": url,
                    "flair": flair_text,
                    "label": "",
                })
                _p(f"  [{len(entries):3d}]   comment: {body[:55]}")

        if posts:
            before = min(p.get("created_utc", 0) for p in posts)
        time.sleep(0.8)

    _p(f"\nCollected {len(entries)} entries.")

    fieldnames = ["id", "type", "post_title", "text", "author", "score", "url", "flair", "label"]
    with open(DATASET, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        for row in entries:
            writer.writerow(row)

    _p(f"Appended {len(entries)} rows to {DATASET}.")


if __name__ == "__main__":
    main()

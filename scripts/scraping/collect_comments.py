"""
collect_comments.py — fetches comments for FMA + NGE posts via Reddit's .json endpoint.
Uses Playwright (browser) to bypass IP blocking.
Applies three-pass filtering then writes dataset_targeted.csv.

Run: python collect_comments.py
"""
import csv
import json
import re
import time
from pathlib import Path
from playwright.sync_api import sync_playwright

from collected_posts import FMA_POSTS, NGE_POSTS

OUTPUT = Path(__file__).parent / "dataset_targeted.csv"
FIELDS = ["id", "type", "post_title", "text", "author", "score", "url", "flair", "label"]
COMMENTS_PER_POST = 4

MEME_SIGNALS = {
    "unironically", "roman empire", "rent free", "ngl", "based",
    "cope", "lmao", "bruh", "no thoughts", "sending me",
    "i cannot", "bestie", "crying", "vocal stim",
    "living in my head", "that's it", "\U0001f480", "\U0001f62d",
}


def _p(msg: str) -> None:
    print(msg.encode("cp1252", errors="replace").decode("cp1252"))


def _clean(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "")).strip()


def _word_count(text: str) -> int:
    return len(text.split())


def _has_meme_signal(text: str) -> bool:
    lower = text.lower()
    return any(s in lower for s in MEME_SIGNALS)


def _is_question(title: str) -> bool:
    tl = title.lower()
    return "?" in title or any(tl.startswith(w) for w in (
        "why", "how", "what", "when", "where", "did", "does",
        "is ", "are ", "can ", "explain", "help",
    ))


def _load_existing_ids() -> set:
    p = Path(__file__).parents[2] / "data" / "dataset.csv"
    if not p.exists():
        return set()
    with open(p, newline="", encoding="utf-8") as f:
        return {row["id"] for row in csv.DictReader(f) if row.get("id")}


def fetch_post_data(page, post: dict) -> dict:
    """Navigate to post JSON endpoint and return enriched post + comments."""
    pid = post["id"].replace("t3_", "")
    sub = post["subreddit"]
    url = f"https://www.reddit.com/r/{sub}/comments/{pid}.json?limit=12&sort=top&depth=1&raw_json=1"
    try:
        page.goto(url, timeout=25000)
        time.sleep(1.2)
        raw = page.evaluate("() => document.body.innerText")
        if not raw or not raw.strip().startswith("["):
            _p(f"  [warn] {post['id']}: unexpected response (not JSON array), got: {repr(raw[:80])}")
            return {"selftext": "", "flair": post.get("flair", ""), "comments": []}
        import json as _json
        data = _json.loads(raw)
        p = data[0]["data"]["children"][0]["data"]
        comments = [
            {"id": "t1_" + c["data"]["id"], "body": c["data"].get("body", ""), "score": c["data"].get("score", 0)}
            for c in data[1]["data"]["children"] if c.get("kind") == "t1"
        ]
        return {
            "selftext": _clean(p.get("selftext", "") or ""),
            "flair": p.get("link_flair_text", "") or post.get("flair", ""),
            "comments": comments,
        }
    except Exception as e:
        _p(f"  [warn] {post['id']}: {e}")
    return {"selftext": "", "flair": post.get("flair", ""), "comments": []}


def build_rows(post: dict, fetched: dict, seen: set, pass_name: str,
               comment_filter=None) -> list:
    rows = []
    pid = post["id"]
    if pid in seen:
        return rows

    title = _clean(post["title"])
    selftext = fetched["selftext"]
    body_text = selftext if selftext and selftext not in ("[deleted]", "[removed]") else ""
    text = f"{title}. {body_text}".rstrip(". ") if body_text else title
    flair = fetched.get("flair") or post.get("flair") or "Discussion"
    url = post["url"]

    seen.add(pid)
    rows.append({
        "id": pid, "type": "post", "post_title": title,
        "text": text, "author": "", "score": post["score"],
        "url": url, "flair": flair, "label": "",
    })

    added = 0
    for c in fetched["comments"]:
        if added >= COMMENTS_PER_POST:
            break
        cid = c["id"]
        body = _clean(c["body"])
        if not cid or cid in seen or not body or body in ("[deleted]", "[removed]"):
            continue
        if comment_filter and not comment_filter(body):
            continue
        seen.add(cid)
        rows.append({
            "id": cid, "type": "comment", "post_title": title,
            "text": body, "author": "", "score": c["score"],
            "url": url, "flair": flair, "label": "",
        })
        added += 1

    _p(f"  [{pass_name}] {title[:65]} -> {len(rows)} rows")
    return rows


def main():
    existing_ids = _load_existing_ids()
    _p(f"Loaded {len(existing_ids)} existing IDs to skip.")

    all_posts = FMA_POSTS + NGE_POSTS
    _p(f"Total posts to process: {len(all_posts)}")

    seen = set(existing_ids)
    all_rows = []

    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=False)
        page = browser.new_page()
        page.set_extra_http_headers({"Accept-Language": "en-US,en;q=0.9"})

        for sub_name, posts in [("FMA", FMA_POSTS), ("NGE", NGE_POSTS)]:
            _p(f"\n{'='*55}")
            _p(f"  {sub_name} - {len(posts)} posts")
            _p(f"{'='*55}")

            # ── Pass 1: Meme/Reactive ──────────────────────────────
            # Trigger: actual meme signals OR image-only post (no selftext, title < 12 words)
            _p("\n  [Pass 1] Meme-register...")
            for p in posts:
                combined = p["title"] + " " + p.get("selftext", "")
                is_image_post = not p.get("selftext") and _word_count(p["title"]) < 12
                if _has_meme_signal(combined) or is_image_post:
                    fetched = fetch_post_data(page, p)
                    all_rows.extend(build_rows(
                        p, fetched, seen, "meme",
                        comment_filter=None,  # grab all comments for meme posts
                    ))

            # ── Pass 2: Informational ──────────────────────────────
            _p("\n  [Pass 2] Informational...")
            for p in posts:
                if p["id"] not in seen and _is_question(p["title"]):
                    fetched = fetch_post_data(page, p)
                    all_rows.extend(build_rows(
                        p, fetched, seen, "info",
                        comment_filter=lambda t: _word_count(t) >= 80,
                    ))

            # ── Pass 3: General (remaining) ────────────────────────
            _p("\n  [Pass 3] General...")
            for p in posts:
                if p["id"] not in seen:
                    fetched = fetch_post_data(page, p)
                    all_rows.extend(build_rows(p, fetched, seen, "general"))

        browser.close()

    _p(f"\nCollected {len(all_rows)} rows total.")
    _p(f"  posts:    {sum(1 for r in all_rows if r['type'] == 'post')}")
    _p(f"  comments: {sum(1 for r in all_rows if r['type'] == 'comment')}")

    with open(OUTPUT, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(all_rows)

    _p(f"\nSaved -> {OUTPUT}")
    _p("Next: label dataset_targeted.csv then merge into dataset.csv.")


if __name__ == "__main__":
    main()

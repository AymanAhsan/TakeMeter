"""
scrape_fma_playwright.py — scrape r/FullmetalAlchemist Discussion/Opinion posts
and their top comments using Python Playwright (no Reddit API).

Target: 200 rows (posts + comments) appended to dataset.csv.
Run:
    python scrape_fma_playwright.py
"""

import csv
import re
import time
from pathlib import Path

from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

FLAIR_URL = (
    "https://www.reddit.com/r/FullmetalAlchemist/"
    "?f=flair_name%3A%22Discussion%2FOpinion%22"
)
CSV_PATH          = Path(__file__).parent / "dataset.csv"
FIELDS            = ["id", "type", "post_title", "text", "author", "score", "url", "flair", "label"]
TARGET_NEW_ROWS   = 200
COMMENTS_PER_POST = 3
SCROLL_PAUSE      = 1.5   # seconds between scrolls
POST_PAUSE        = 1.2   # seconds between post visits
MAX_SCROLL_ROUNDS = 30    # safety cap on infinite scroll attempts


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _clean(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "")).strip()


def _load_existing_ids() -> set[str]:
    if not CSV_PATH.exists():
        return set()
    with open(CSV_PATH, newline="", encoding="utf-8") as f:
        return {row["id"] for row in csv.DictReader(f) if row.get("id")}


def _append_rows(rows: list[dict]) -> None:
    file_exists = CSV_PATH.exists() and CSV_PATH.stat().st_size > 0
    with open(CSV_PATH, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        if not file_exists:
            writer.writeheader()
        writer.writerows(rows)


def _safe_print(msg: str) -> None:
    print(msg.encode("cp1252", errors="replace").decode("cp1252"))


# ---------------------------------------------------------------------------
# Scraping
# ---------------------------------------------------------------------------

def collect_post_links(page, target: int = 60) -> list[str]:
    """Scroll the listing page and collect post permalinks."""
    links: list[str] = []
    seen: set[str] = set()

    for _ in range(MAX_SCROLL_ROUNDS):
        posts = page.query_selector_all("shreddit-post")
        for el in posts:
            href = el.get_attribute("permalink") or ""
            if href and href not in seen:
                seen.add(href)
                links.append("https://www.reddit.com" + href)

        _safe_print(f"  [listing] {len(links)} links found so far...")
        if len(links) >= target:
            break

        # scroll down
        page.evaluate("window.scrollBy(0, 2000)")
        time.sleep(SCROLL_PAUSE)

        # check if a "load more" button appeared
        try:
            more = page.query_selector("faceplate-partial[loading=lazy]")
            if more:
                more.scroll_into_view_if_needed()
                time.sleep(SCROLL_PAUSE)
        except Exception:
            pass

    return links


def scrape_post(page, url: str, existing_ids: set[str]) -> list[dict]:
    """Visit one post page and return rows (post + top comments) not already seen."""
    rows: list[dict] = []

    try:
        page.goto(url, wait_until="domcontentloaded", timeout=20000)
    except PWTimeout:
        _safe_print(f"    [timeout] {url}")
        return rows

    time.sleep(1.2)

    # ---- post data ----
    post_el = page.query_selector("shreddit-post")
    if not post_el:
        return rows

    pid        = post_el.get_attribute("id") or ""          # e.g. t3_abc123
    title      = _clean(post_el.get_attribute("post-title") or "")
    author     = post_el.get_attribute("author") or ""
    score      = post_el.get_attribute("score") or "0"
    flair_text = "Discussion/Opinion"

    if not pid or pid in existing_ids:
        return rows

    # selftext lives inside a <div slot="text-body"> or similar
    body = ""
    try:
        body_el = page.query_selector('[slot="text-body"], .md, [data-click-id="text"]')
        if body_el:
            body = _clean(body_el.inner_text())
    except Exception:
        pass

    text = f"{title}. {body}".rstrip(". ") if body else title

    post_row = {
        "id":         pid,
        "type":       "post",
        "post_title": title,
        "text":       text,
        "author":     author,
        "score":      score,
        "url":        url,
        "flair":      flair_text,
        "label":      "",
    }
    rows.append(post_row)
    existing_ids.add(pid)

    # ---- top comments ----
    try:
        page.wait_for_selector("shreddit-comment", timeout=6000)
    except PWTimeout:
        _safe_print(f"    [no comments] {title[:50]}")
        return rows

    comment_els = page.query_selector_all("shreddit-comment[depth='0']")
    added = 0
    for cel in comment_els:
        if added >= COMMENTS_PER_POST:
            break
        cid = cel.get_attribute("thingid") or cel.get_attribute("id") or ""
        if not cid or cid in existing_ids:
            continue

        # body text
        cbody = ""
        try:
            p_els = cel.query_selector_all("p")
            cbody = _clean(" ".join(p.inner_text() for p in p_els))
        except Exception:
            pass

        if not cbody or cbody.lower() in ("[deleted]", "[removed]"):
            continue

        cauthor = cel.get_attribute("author") or ""
        cscore  = cel.get_attribute("score") or "0"

        existing_ids.add(cid)
        rows.append({
            "id":         cid,
            "type":       "comment",
            "post_title": title,
            "text":       cbody,
            "author":     cauthor,
            "score":      cscore,
            "url":        url,
            "flair":      flair_text,
            "label":      "",
        })
        added += 1

    return rows


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    existing_ids = _load_existing_ids()
    _safe_print(f"Existing IDs loaded: {len(existing_ids)}")

    new_rows: list[dict] = []

    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=False)   # visible so Reddit doesn't block
        ctx     = browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/125.0.0.0 Safari/537.36"
            ),
            viewport={"width": 1280, "height": 900},
        )
        page = ctx.new_page()

        # --- 1. listing page ---
        _safe_print(f"\nNavigating to listing: {FLAIR_URL}")
        page.goto(FLAIR_URL, wait_until="domcontentloaded", timeout=20000)
        time.sleep(2)

        # estimate how many posts we need (assume ~4 rows/post on average)
        posts_needed = max(60, (TARGET_NEW_ROWS // (1 + COMMENTS_PER_POST)) + 10)
        post_links = collect_post_links(page, target=posts_needed)
        _safe_print(f"\nCollected {len(post_links)} post links")

        # --- 2. visit each post ---
        for i, url in enumerate(post_links):
            if len(new_rows) >= TARGET_NEW_ROWS:
                break

            _safe_print(f"\n[{i+1}/{len(post_links)}] {url}")
            rows = scrape_post(page, url, existing_ids)
            new_rows.extend(rows)
            _safe_print(f"  -> {len(rows)} rows  (total new: {len(new_rows)})")

            time.sleep(POST_PAUSE)

        browser.close()

    # --- 3. write results ---
    new_rows = new_rows[:TARGET_NEW_ROWS]
    _safe_print(f"\nAppending {len(new_rows)} new rows to {CSV_PATH}")
    _append_rows(new_rows)

    posts    = sum(1 for r in new_rows if r["type"] == "post")
    comments = sum(1 for r in new_rows if r["type"] == "comment")
    _safe_print(f"Done — {posts} posts, {comments} comments")
    _safe_print(f"dataset.csv now has {len(_load_existing_ids())} unique IDs")


if __name__ == "__main__":
    main()

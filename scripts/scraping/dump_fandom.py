#!/usr/bin/env python3
"""
Stage 1: Fandom wiki ingestion via MediaWiki API.

Dumps all namespace-0 pages as plain text JSON to data/wiki_raw/<series>/.
No API key required. Re-runs are free — existing files are skipped.
Uses prop=revisions (batch, 50 pages/req) + wikitext stripping because
Fandom disables the TextExtracts extension.

Usage:
    python scripts/scraping/dump_fandom.py [--series aot hxh fma nge]
"""

import argparse
import json
import pathlib
import re
import time

import requests

WIKIS: dict[str, str] = {
    "aot": "https://attackontitan.fandom.com",
    "hxh": "https://hunterxhunter.fandom.com",
    "fma": "https://fma.fandom.com",
    "nge": "https://evangelion.fandom.com",
}

OUTPUT_BASE = pathlib.Path("data/wiki_raw")
RATE_DELAY = 0.5          # seconds between API calls (~2 req/s)
BATCH_SIZE = 50           # page IDs per revisions call (MediaWiki limit)
MIN_TEXT_CHARS = 100      # skip pages shorter than this after stripping
USER_AGENT = "TakeMeter/1.0 (aymanahsan06@gmail.com; research project)"


# ---------------------------------------------------------------------------
# Wikitext stripping
# ---------------------------------------------------------------------------

def _strip_templates(text: str) -> str:
    """Remove {{...}} templates, iterating to handle nesting."""
    prev = None
    while prev != text:
        prev = text
        text = re.sub(r"\{\{[^{}]*?\}\}", "", text, flags=re.DOTALL)
    return text


def strip_wikitext(wikitext: str) -> str:
    """Convert raw MediaWiki markup to rough plaintext for RAG indexing."""
    text = wikitext

    # Templates (handles nesting up to convergence)
    text = _strip_templates(text)

    # Tables  {| ... |}
    prev = None
    while prev != text:
        prev = text
        text = re.sub(r"\{\|[^{|]*?\|\}", "", text, flags=re.DOTALL)

    # HTML comments
    text = re.sub(r"<!--.*?-->", "", text, flags=re.DOTALL)

    # HTML tags (ref, gallery, etc.)
    text = re.sub(r"<[^>]+>", " ", text)

    # [[File:...]] / [[Image:...]] / [[Category:...]]
    text = re.sub(
        r"\[\[(?:File|Image|Category|Media):[^\]]*\]\]",
        "",
        text,
        flags=re.IGNORECASE,
    )

    # Internal links: [[link|display]] → display
    text = re.sub(r"\[\[[^\]|]*\|([^\]]*)\]\]", r"\1", text)

    # Internal links: [[link]] → link
    text = re.sub(r"\[\[([^\]]*)\]\]", r"\1", text)

    # External links: [url text] → text
    text = re.sub(r"\[https?://[^\s\]]+\s+([^\]]+)\]", r"\1", text)
    text = re.sub(r"\[https?://[^\]]*\]", "", text)

    # Section headers: ==Foo== → Foo
    text = re.sub(r"={2,6}\s*([^=\n]+?)\s*={2,6}", r"\n\n\1\n", text)

    # Bold / italic markup
    text = re.sub(r"'{2,3}", "", text)

    # List / indent markers at start of lines
    text = re.sub(r"^[*#;:]+\s*", "", text, flags=re.MULTILINE)

    # Collapse whitespace
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)

    return text.strip()


# ---------------------------------------------------------------------------
# MediaWiki API helpers
# ---------------------------------------------------------------------------

def _make_session() -> requests.Session:
    s = requests.Session()
    s.headers["User-Agent"] = USER_AGENT
    return s


def enumerate_pages(session: requests.Session, base_url: str) -> list[dict]:
    """Return all namespace-0 pages as [{pageid, title}, ...] via list=allpages."""
    api = f"{base_url}/api.php"
    params: dict = {
        "action": "query",
        "list": "allpages",
        "apnamespace": 0,
        "aplimit": 500,
        "format": "json",
    }
    pages: list[dict] = []
    while True:
        resp = session.get(api, params=params, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        pages.extend(data["query"]["allpages"])
        if "continue" not in data:
            break
        params.update(data["continue"])
        time.sleep(RATE_DELAY)
    return pages


def fetch_wikitext_batch(
    session: requests.Session, base_url: str, page_ids: list[int]
) -> dict:
    """Fetch raw wikitext for up to BATCH_SIZE page IDs."""
    api = f"{base_url}/api.php"
    params = {
        "action": "query",
        "pageids": "|".join(str(p) for p in page_ids),
        "prop": "revisions",
        "rvprop": "content",
        "rvslots": "main",
        "format": "json",
    }
    resp = session.get(api, params=params, timeout=120)
    resp.raise_for_status()
    return resp.json()["query"]["pages"]


# ---------------------------------------------------------------------------
# Main dump logic
# ---------------------------------------------------------------------------

def safe_filename(title: str) -> str:
    return "".join(c if c.isalnum() or c in " _-." else "_" for c in title).strip()[:200]


def extract_wikitext_from_page(page_data: dict) -> str:
    """Pull raw wikitext out of a revisions API response entry."""
    revisions = page_data.get("revisions")
    if not revisions:
        return ""
    rev = revisions[0]
    # Newer MediaWiki: slots.main.*
    slots = rev.get("slots", {})
    if slots:
        return slots.get("main", {}).get("*", "")
    # Older format: direct *
    return rev.get("*", "")


def dump_wiki(series: str, base_url: str) -> None:
    out_dir = OUTPUT_BASE / series
    out_dir.mkdir(parents=True, exist_ok=True)

    session = _make_session()

    print(f"[{series.upper()}] Enumerating pages from {base_url} …")
    pages = enumerate_pages(session, base_url)
    total = len(pages)
    print(f"[{series.upper()}] {total} pages found. Fetching wikitext …")

    id_to_title: dict[int, str] = {p["pageid"]: p["title"] for p in pages}
    all_ids = list(id_to_title.keys())

    saved = skipped = redirects = empty = 0
    n_batches = (len(all_ids) + BATCH_SIZE - 1) // BATCH_SIZE

    for batch_num, i in enumerate(range(0, len(all_ids), BATCH_SIZE), start=1):
        batch_ids = all_ids[i : i + BATCH_SIZE]

        uncached: list[int] = []
        for pid in batch_ids:
            fname = safe_filename(id_to_title[pid]) + ".json"
            if (out_dir / fname).exists():
                skipped += 1
            else:
                uncached.append(pid)

        if not uncached:
            if batch_num % 20 == 0:
                print(f"[{series.upper()}] {batch_num}/{n_batches} — all cached")
            continue

        try:
            pages_data = fetch_wikitext_batch(session, base_url, uncached)
        except requests.RequestException as exc:
            print(f"[{series.upper()}] Batch {batch_num}/{n_batches} failed: {exc} — skipping")
            time.sleep(RATE_DELAY * 4)
            continue

        for pid_str, page_data in pages_data.items():
            pid = int(pid_str)
            title = id_to_title.get(pid, page_data.get("title", "unknown"))
            wikitext = extract_wikitext_from_page(page_data)

            if not wikitext:
                empty += 1
                continue

            # Skip redirect pages
            if wikitext.lstrip().upper().startswith("#REDIRECT"):
                redirects += 1
                continue

            text = strip_wikitext(wikitext)
            if len(text) < MIN_TEXT_CHARS:
                empty += 1
                continue

            doc = {
                "series": series,
                "page_title": title,
                "url": f"{base_url}/wiki/{title.replace(' ', '_')}",
                "text": text,
            }
            fname = safe_filename(title) + ".json"
            (out_dir / fname).write_text(
                json.dumps(doc, ensure_ascii=False, indent=2), encoding="utf-8"
            )
            saved += 1

        print(
            f"[{series.upper()}] {batch_num}/{n_batches} batches — "
            f"saved={saved} cached={skipped} redirects={redirects} empty={empty}"
        )
        time.sleep(RATE_DELAY)

    print(
        f"[{series.upper()}] Done.  "
        f"Saved: {saved}  Cached: {skipped}  Redirects: {redirects}  Empty: {empty}"
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Dump Fandom wiki pages via MediaWiki API.")
    parser.add_argument(
        "--series",
        nargs="+",
        choices=list(WIKIS),
        default=list(WIKIS),
        help="Which series to fetch (default: all four).",
    )
    args = parser.parse_args()

    for series in args.series:
        dump_wiki(series, WIKIS[series])

    print("\nStage 1 complete — raw wiki pages saved to data/wiki_raw/")


if __name__ == "__main__":
    main()

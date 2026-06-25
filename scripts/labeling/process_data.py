"""
Process posts_data.json -> dataset.csv
Target: ~100 rows (posts + comments).
"""
import csv
import json
import re
from pathlib import Path

SRC = Path(__file__).parents[2] / "data" / "posts_data.json"
OUT = Path(__file__).parents[2] / "data" / "dataset.csv"
FIELDS = ["id", "type", "post_title", "text", "author", "score", "url", "flair", "label"]

IMAGE_RE = re.compile(r'https?://\S+\.(jpeg|jpg|png|gif|webp)\S*', re.I)
PREVIEW_RE = re.compile(r'https?://preview\.redd\.it/\S+', re.I)
GIPHY_RE = re.compile(r'!\[gif\]\(giphy\|[^\)]+\)', re.I)

SKIP_AUTHORS = {"AutoModerator"}


def clean(text: str) -> str:
    t = GIPHY_RE.sub('', text)
    t = PREVIEW_RE.sub('', t)
    t = IMAGE_RE.sub('', t)
    t = re.sub(r'#Join our.*?\*I am a bot.*?\*', '', t, flags=re.S)
    t = re.sub(r'\*I am a bot.*', '', t, flags=re.S)
    t = re.sub(r'\s+', ' ', t).strip()
    return t


def post_text(post: dict) -> str:
    title = post["title"].strip()
    body = clean(post.get("selftext", "") or "")
    return f"{title}. {body}".strip().rstrip('.') if body else title


def main():
    data = json.loads(SRC.read_text(encoding="utf-8"))
    rows = []

    for post in data:
        # --- post row ---
        pid = post["id"]
        pt = post_text(post)
        rows.append({
            "id": f"t3_{pid}",
            "type": "post",
            "post_title": post["title"],
            "text": pt,
            "author": "",          # omit author for classifier cleanliness
            "score": post["score"],
            "url": f"https://www.reddit.com{post.get('permalink', '')}",
            "flair": post["flair"],
            "label": "",
        })

        # --- comment rows (max 4 per post) ---
        comment_count = 0
        for c in post.get("comments", []):
            if comment_count >= 4:
                break
            if c["author"] in SKIP_AUTHORS:
                continue
            body = clean(c.get("body", ""))
            if not body or len(body) < 10:
                continue
            rows.append({
                "id": f"t1_{c['id']}",
                "type": "comment",
                "post_title": post["title"],
                "text": body,
                "author": "",
                "score": c["score"],
                "url": f"https://www.reddit.com{post.get('permalink', '')}",
                "flair": post["flair"],
                "label": "",
            })
            comment_count += 1

    rows = rows[:100]

    with open(OUT, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)

    posts = sum(1 for r in rows if r["type"] == "post")
    comments = sum(1 for r in rows if r["type"] == "comment")
    print(f"Written {len(rows)} rows to {OUT}")
    print(f"  posts: {posts}   comments: {comments}")


if __name__ == "__main__":
    main()

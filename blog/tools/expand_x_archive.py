#!/usr/bin/env python3
"""Add the replies X shows under each saved post to tweets.json, without logging in.

    python3 blog/tools/expand_x_archive.py --out blog/fable-5-1-build-days-bhopal --keyword bhopal

X's trend timelines list posts but not the replies under them, and search is
closed to readers without an account. The server-rendered page of a post,
though, carries the few replies X shows logged-out visitors. This script opens
the page of every saved post that has replies, collects the post ids in it,
fetches each unknown one through X's syndication endpoint (the one embedded
posts use, no login), and merges the ones that belong to the conversation
(a reply to or a quote of a saved post, or a post that names the keyword) into
tweets.json, in the same shape capture_x_trend.py writes. Added posts carry
in_timelines ["conversation"]; X does not expose their repost or view counts.
Replies found this way are scanned themselves on later runs, so threads fill
in over time. A run stops after --max-pages pages so it stays short.
"""
import argparse
import datetime
import html
import json
import math
import os
import re
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import capture_x_trend as capx  # noqa: E402

UTC, IST = capx.UTC, capx.IST
RESCAN_AFTER = 6 * 3600


def synd_token(tweet_id):
    """The token X's embed code derives from the id (base36 of id/1e15*pi, zeros and dot removed)."""
    n = (int(tweet_id) / 1e15) * math.pi
    digits = "0123456789abcdefghijklmnopqrstuvwxyz"
    ip, fr = int(n), n - int(n)
    s = ""
    while ip > 0:
        s, ip = digits[ip % 36] + s, ip // 36
    f = ""
    for _ in range(11):
        fr *= 36
        f += digits[int(fr)]
        fr -= int(fr)
    return (s + "." + f).replace("0", "").replace(".", "")


def fetch_post(tweet_id):
    code, body = capx.http(f"https://cdn.syndication.twimg.com/tweet-result?id={tweet_id}&token={synd_token(tweet_id)}&lang=en")
    if code != 200:
        return None
    try:
        t = json.loads(body)
    except ValueError:
        return None
    return t if t.get("__typename") == "Tweet" and t.get("id_str") else None


def normalise(t):
    u = t.get("user") or {}
    ents = t.get("entities") or {}
    text = t.get("text", "")
    urls = []
    for e in ents.get("urls", []) or []:
        if e.get("url") and e.get("expanded_url"):
            text = text.replace(e["url"], e["expanded_url"])
            urls.append(e["expanded_url"])
    media = []
    for m in t.get("mediaDetails") or []:
        text = text.replace(m.get("url", ""), "")
        if m.get("type") == "photo":
            media.append({"type": "photo", "url": m.get("media_url_https")})
        else:
            vu, vb = capx.pick_video((m.get("video_info") or {}).get("variants"))
            media.append({"type": m.get("type"), "thumbnail": m.get("media_url_https"), "video_url": vu, "video_url_best": vb})
    text = html.unescape(re.sub(r"[ \t]+\n", "\n", text).strip())
    dt = datetime.datetime.fromisoformat(t["created_at"].replace("Z", "+00:00"))
    handle = u.get("screen_name")
    quoted = (t.get("quoted_tweet") or {}).get("id_str")
    reply_to = t.get("in_reply_to_status_id_str")
    return {
        "id": t["id_str"], "url": f"https://x.com/{handle}/status/{t['id_str']}",
        "author": {"name": u.get("name"), "handle": handle, "verified": bool(u.get("is_blue_verified") or u.get("verified")),
                   "followers": None, "profile_image": (u.get("profile_image_url_https") or "").replace("_normal", "_400x400")},
        "created_at_utc": dt.astimezone(UTC).isoformat().replace("+00:00", "Z"),
        "created_at_ist": dt.astimezone(IST).strftime("%Y-%m-%d %H:%M IST"),
        "type": "reply" if reply_to else ("quote" if quoted else "post"),
        "in_reply_to": {"handle": t.get("in_reply_to_screen_name"), "status_id": reply_to} if reply_to else None,
        "quoted_status_id": quoted or None,
        "text": text, "text_raw": t.get("text", ""), "lang": t.get("lang"),
        "metrics": {"likes": t.get("favorite_count"), "reposts": None, "replies": t.get("conversation_count"),
                    "quotes": None, "bookmarks": None, "views": None},
        "urls": urls, "hashtags": [h.get("text") for h in ents.get("hashtags", []) or []],
        "mentions": [m.get("screen_name") for m in ents.get("user_mentions", []) or []],
        "media": media,
    }


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", default=".", help="folder that holds tweets.json")
    ap.add_argument("--keyword", help="posts whose text contains this word are kept even if they reply to nothing saved")
    ap.add_argument("--max-pages", type=int, default=40, help="post pages to open per run")
    a = ap.parse_args()
    path = os.path.join(a.out, "tweets.json")
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    meta, posts = data["meta"], data["posts"]
    by_id = {p["id"]: p for p in posts}
    kw = (a.keyword or meta.get("keyword") or "").lower()
    skip = set(meta.get("expand", {}).get("not_posts", []))
    start = datetime.datetime.fromisoformat(meta["trend"]["created_at_utc"].replace("Z", "+00:00")) - datetime.timedelta(hours=8)
    now = datetime.datetime.now(UTC)

    def stale(p):
        s = p.get("conversation_scan")
        if not s:
            return True
        age = (now - datetime.datetime.fromisoformat(s["at"].replace("Z", "+00:00"))).total_seconds()
        return s.get("replies") != (p["metrics"].get("replies") or 0) or age > RESCAN_AFTER

    todo = [p for p in posts if (p["metrics"].get("replies") or 0) > 0 and stale(p)]
    todo.sort(key=lambda p: (p.get("conversation_scan") is not None, -(p["metrics"].get("replies") or 0)))
    print(f"{len(posts)} posts saved; {len(todo)} pages to scan, opening up to {a.max_pages}")
    added, opened, blocked = [], 0, False
    for p in todo[:a.max_pages]:
        code, body = capx.http(p["url"])
        opened += 1
        if code in (403, 429) or code == 0:
            print(f"  x.com answered {code} on {p['url']}; stopping this run", file=sys.stderr)
            blocked = True
            break
        found = 0
        if code == 200:
            for cid in sorted(set(re.findall(r"\d{19}", body))):
                if cid == p["id"] or cid in by_id or cid in skip:
                    continue
                if not (start <= capx.snowflake_utc(cid) <= now):
                    continue
                t = fetch_post(cid)
                time.sleep(0.2)
                if t is None:
                    skip.add(cid)
                    continue
                row = normalise(t)
                belongs = ((row["in_reply_to"] or {}).get("status_id") in by_id or row["quoted_status_id"] in by_id
                           or (kw and kw in row["text"].lower()))
                if not belongs:
                    skip.add(cid)
                    continue
                row["in_timelines"] = ["conversation"]
                row["first_seen_utc"] = now.isoformat(timespec="seconds").replace("+00:00", "Z")
                row["found_under"] = p["id"]
                by_id[cid] = row
                added.append(row)
                found += 1
        p["conversation_scan"] = {"at": now.isoformat(timespec="seconds").replace("+00:00", "Z"),
                                  "replies": p["metrics"].get("replies") or 0, "found": found}
        print(f"  @{p['author']['handle']}: {found} new under a post with {p['metrics'].get('replies')} replies")
        time.sleep(1.0)

    posts = sorted(by_id.values(), key=lambda r: r["created_at_utc"])
    for p in posts:
        p["matches_keyword"] = (kw in p["text"].lower()) if kw else None
    meta["counts"]["posts_total"] = len(posts)
    meta["counts"]["posts_matching_keyword"] = sum(1 for p in posts if p.get("matches_keyword")) if kw else None
    meta["counts"]["authors"] = len({p["author"]["handle"] for p in posts})
    meta["counts"]["posts_from_conversations"] = sum(1 for p in posts if "conversation" in (p.get("in_timelines") or []))
    meta["expand"] = {"last_run_utc": now.isoformat(timespec="seconds").replace("+00:00", "Z"), "pages_opened": opened,
                      "pages_left": max(0, len(todo) - opened), "blocked": blocked, "not_posts": sorted(skip)[-5000:]}
    with open(path, "w", encoding="utf-8") as f:
        json.dump({"meta": meta, "posts": posts}, f, ensure_ascii=False, indent=1)
    print(f"saved {len(posts)} posts ({len(added)} new from conversations, {meta['counts']['posts_from_conversations']} in total"
          + (f", {meta['counts']['posts_matching_keyword']} match '{kw}'" if kw else "") + f"); {meta['expand']['pages_left']} pages left for later runs")


if __name__ == "__main__":
    main()

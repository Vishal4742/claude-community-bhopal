#!/usr/bin/env python3
"""Save every post from an X (Twitter) trend page, without logging in.

Usage:
    python3 blog/tools/capture_x_trend.py https://x.com/i/trending/2098201852286324889 --keyword bhopal --out blog/fable-5-1-build-days-bhopal

Writes <out>/tweets.json. If that file already exists the new capture is merged
into it: posts already saved stay, their counts are refreshed, new posts are
added, and nothing is ever dropped (pass --no-merge to start over).

How it works: X's GraphQL API hands out a guest token to anyone. With it,
AiTrendByRestId returns the trend's story (title, Grok summary) and the ids of
its "Top" and "Latest" post timelines, and GenericTimelineById pages through
those. Query ids change every few weeks; they are refreshed from the
community-maintained TwitterInternalAPIDocument project, with a fallback to the
ids that worked on 2026-09-11. Only the standard library is used.
"""
import argparse
import datetime
import html
import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request

BEARER = ("AAAAAAAAAAAAAAAAAAAAANRILgAAAAAAnNwIzUejRCOuH5E6I8xnZz4puTs%3D"
          "1Zv7ttfk8LF81IUq16cHjhLTvJu4FA33AGWWjCpTnA")
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/128.0 Safari/537.36")
API_DOC = "https://raw.githubusercontent.com/fa0311/TwitterInternalAPIDocument/master/docs/json/API.json"
FALLBACK = {
    "AiTrendByRestId": {"queryId": "OrL2ZsqsgKrVk9u-21fwkA", "features": {}},
    "GenericTimelineById": {"queryId": "91IOyupSYIgmmAnZszKqBQ", "features": {}},
}
IST = datetime.timezone(datetime.timedelta(hours=5, minutes=30))
UTC = datetime.timezone.utc


def http(url, headers=None, data=None, timeout=40):
    req = urllib.request.Request(url, data=data, headers={"User-Agent": UA, **(headers or {})})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, r.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", "replace")
    except Exception as e:  # noqa: BLE001
        return 0, str(e)


def guest_token():
    for attempt in range(3):
        code, body = http("https://api.x.com/1.1/guest/activate.json", {"Authorization": "Bearer " + BEARER}, data=b"")
        if code == 200:
            return json.loads(body)["guest_token"]
        time.sleep(3 * (attempt + 1))
    sys.exit(f"guest token failed: HTTP {code} {body[:200]}")


def query_ids():
    ops = {k: dict(v) for k, v in FALLBACK.items()}
    try:
        code, body = http(API_DOC)
        if code == 200:
            g = json.loads(body)["graphql"]
            for op in ops:
                if op in g:
                    ops[op] = {"queryId": g[op]["queryId"], "features": g[op].get("features", {})}
    except Exception as e:  # noqa: BLE001
        print("could not refresh query ids, using fallback:", e, file=sys.stderr)
    return ops


def gql(op, ops, gt, variables):
    feats = dict(ops[op]["features"])
    code, body = 0, ""
    for _ in range(16):
        url = (f"https://api.x.com/graphql/{ops[op]['queryId']}/{op}"
               f"?variables={urllib.parse.quote(json.dumps(variables))}"
               f"&features={urllib.parse.quote(json.dumps(feats))}")
        code, body = http(url, {"Authorization": "Bearer " + BEARER, "x-guest-token": gt,
                                "content-type": "application/json", "x-twitter-active-user": "yes",
                                "x-twitter-client-language": "en"})
        m = re.search(r'"message":"([^"]+)","path":\["variable","([^"]+)"\]', body)
        fm = re.search(r'The following features cannot be null: ([^"]+)"', body)
        if code == 422 and m and "must be defined" in m.group(1):
            var = m.group(2)
            variables[var] = 40 if var == "count" else ("" if "cursor" in var.lower() else False)
            continue
        if fm:
            for name in fm.group(1).split(","):
                feats[name.strip()] = True
            continue
        return code, body
    return code, body


def collect(body):
    d = json.loads(body)
    tweets, cursors = [], {}

    def rec(x):
        if isinstance(x, dict):
            eid = x.get("entryId", "")
            if eid.startswith("cursor-") and isinstance(x.get("content"), dict):
                c = x["content"]
                cursors[eid.split("-")[1]] = c.get("value") or (c.get("itemContent") or {}).get("value")
            if x.get("__typename") == "Tweet" and "legacy" in x and "rest_id" in x:
                tweets.append(x)
            for v in x.values():
                rec(v)
        elif isinstance(x, list):
            for v in x:
                rec(v)
    rec(d)
    return tweets, cursors


def pick_video(variants):
    mp4 = [v for v in variants or [] if v.get("content_type") == "video/mp4" and v.get("url")]
    if not mp4:
        return None, None
    best = max(mp4, key=lambda v: v.get("bitrate", 0))
    mid = [v for v in mp4 if re.search(r"/(720|540|480|360)x", v["url"])]
    pick = max(mid, key=lambda v: v.get("bitrate", 0)) if mid else min(mp4, key=lambda v: v.get("bitrate", 0))
    return pick["url"], best["url"]


def normalise(t):
    leg = t["legacy"]
    u = ((t.get("core") or {}).get("user_results") or {}).get("result") or {}
    uc, ul = u.get("core") or {}, u.get("legacy") or {}
    handle = uc.get("screen_name") or ul.get("screen_name")
    ents = leg.get("entities") or {}
    text = leg.get("full_text", "")
    urls = []
    for e in ents.get("urls", []) or []:
        if e.get("url") and e.get("expanded_url"):
            text = text.replace(e["url"], e["expanded_url"])
            urls.append(e["expanded_url"])
    media_ents = ((leg.get("extended_entities") or ents).get("media") or [])
    for m in media_ents:
        text = text.replace(m.get("url", ""), "")
    text = html.unescape(re.sub(r"[ \t]+\n", "\n", text).strip())
    q = ((t.get("quoted_status_result") or {}).get("result") or {})
    if q.get("__typename") == "TweetWithVisibilityResults":
        q = q.get("tweet", {})
    dt = datetime.datetime.strptime(leg["created_at"], "%a %b %d %H:%M:%S %z %Y")
    media = []
    for m in media_ents:
        if m.get("type") == "photo":
            media.append({"type": "photo", "url": m.get("media_url_https")})
        else:
            vu, vb = pick_video((m.get("video_info") or {}).get("variants"))
            media.append({"type": m.get("type"), "thumbnail": m.get("media_url_https"), "video_url": vu, "video_url_best": vb})
    return {
        "id": t["rest_id"], "url": f"https://x.com/{handle}/status/{t['rest_id']}",
        "author": {"name": uc.get("name") or ul.get("name"), "handle": handle,
                   "verified": bool(u.get("is_blue_verified")),
                   "followers": (u.get("relationship_counts") or {}).get("followers") or ul.get("followers_count"),
                   "profile_image": ((u.get("avatar") or {}).get("image_url") or ul.get("profile_image_url_https") or "").replace("_normal", "_400x400")},
        "created_at_utc": dt.astimezone(UTC).isoformat().replace("+00:00", "Z"),
        "created_at_ist": dt.astimezone(IST).strftime("%Y-%m-%d %H:%M IST"),
        "type": "reply" if leg.get("in_reply_to_status_id_str") else ("quote" if q.get("rest_id") else "post"),
        "in_reply_to": ({"handle": leg.get("in_reply_to_screen_name"), "status_id": leg.get("in_reply_to_status_id_str")}
                        if leg.get("in_reply_to_status_id_str") else None),
        "quoted_status_id": q.get("rest_id") or None,
        "text": text, "text_raw": leg.get("full_text", ""), "lang": leg.get("lang"),
        "metrics": {"likes": leg.get("favorite_count"), "reposts": leg.get("retweet_count"),
                    "replies": leg.get("reply_count"), "quotes": leg.get("quote_count"),
                    "bookmarks": leg.get("bookmark_count"), "views": int((t.get("views") or {}).get("count") or 0)},
        "urls": urls, "hashtags": [h.get("text") for h in ents.get("hashtags", []) or []],
        "mentions": [m.get("screen_name") for m in ents.get("user_mentions", []) or []],
        "media": media,
    }


def snowflake_utc(sid):
    return datetime.datetime.fromtimestamp(((int(sid) >> 22) + 1288834974657) / 1000, UTC)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("trend", help="trend URL or numeric id")
    ap.add_argument("--keyword", help="flag posts whose text contains this word (case-insensitive)")
    ap.add_argument("--out", default=".", help="folder that holds tweets.json (default: current)")
    ap.add_argument("--max-pages", type=int, default=80, help="pages per timeline (40 posts each)")
    ap.add_argument("--no-merge", action="store_true", help="ignore an existing tweets.json instead of merging into it")
    a = ap.parse_args()
    m = re.search(r"(\d{15,20})", a.trend)
    if not m:
        sys.exit("could not find a trend id in " + a.trend)
    trend_id = m.group(1)
    out_path = os.path.join(a.out, "tweets.json")
    existing = None
    if not a.no_merge and os.path.exists(out_path):
        with open(out_path, encoding="utf-8") as f:
            existing = json.load(f)
        print(f"merging into {out_path} ({len(existing.get('posts', []))} posts already saved)")

    ops = query_ids()
    gt = guest_token()
    code, body = gql("AiTrendByRestId", ops, gt, {"trendId": trend_id, "includePromotedContent": False})
    if code != 200:
        sys.exit(f"AiTrendByRestId failed: HTTP {code} {body[:300]}")
    page = json.loads(body)["data"]["ai_trend_by_rest_id"]["result"]["page"]
    article = page.get("article") or {}
    title = article.get("title")
    summary = ((article.get("article_text") or {}).get("text"))
    print("trend:", title)
    # X's own size of the trend (postCount in the story page's payload). Only a
    # fraction of those posts is shown to readers without an account.
    post_count = None
    code_h, html_page = http(f"https://x.com/i/trending/{trend_id}")
    mm = re.search(r"postCount:(\d+)", html_page) if code_h == 200 else None
    if mm:
        post_count = int(mm.group(1))
        print("posts in the trend, by X's count:", post_count)
    timelines = {t["label"].lower(): t["post_timeline"]["id"] for t in page.get("post_timelines", [])}

    fresh = {}
    for label, tid in timelines.items():
        variables = {"timelineId": tid, "count": 40, "withQuickPromoteEligibilityTweetFields": True}
        seen, empty, n = set(), 0, 0
        while n < a.max_pages:
            code, body = gql("GenericTimelineById", ops, gt, variables)
            if code != 200:
                print(f"  {label}: HTTP {code} {body[:200]}", file=sys.stderr)
                break
            tweets, cursors = collect(body)
            n += 1
            for t in tweets:
                fresh.setdefault(t["rest_id"], {"tweet": t, "in": set()})["in"].add(label)
            print(f"  {label} page {n}: {len(tweets)} posts")
            bot = cursors.get("bottom")
            empty = empty + 1 if not tweets else 0
            if not bot or bot in seen or empty >= 2:
                break
            seen.add(bot)
            variables["cursor"] = bot
            time.sleep(0.8)

    merged = {p["id"]: p for p in (existing or {}).get("posts", [])}
    added = 0
    skipped = 0
    for rid, f in fresh.items():
        try:
            row = normalise(f["tweet"])
        except (KeyError, ValueError, TypeError) as e:  # a withheld or deleted post comes back without its fields
            skipped += 1
            print(f"  skipping {rid}: {type(e).__name__} {e}", file=sys.stderr)
            continue
        old = merged.get(rid)
        if old is None:
            added += 1
        row["in_timelines"] = sorted(set((old or {}).get("in_timelines", [])) | f["in"])
        row["first_seen_utc"] = (old or {}).get("first_seen_utc") or datetime.datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z")
        merged[rid] = {**(old or {}), **row}
    posts = sorted(merged.values(), key=lambda r: r["created_at_utc"])
    kw = (a.keyword or (existing or {}).get("meta", {}).get("keyword") or "").lower()
    for p in posts:
        p["matches_keyword"] = (kw in p["text"].lower()) if kw else None
        p.pop("mentions_bhopal", None)
        p.pop("about_bhopal", None)

    now = datetime.datetime.now(UTC).replace(second=0, microsecond=0)
    now_ist = now.astimezone(IST)
    old_meta = (existing or {}).get("meta", {})
    old_trend = old_meta.get("trend", {})
    created = snowflake_utc(trend_id)
    # X rewrites the story's headline as the trend evolves; keep every one we have seen.
    history = list(old_trend.get("title_history") or [])
    if not history and old_trend.get("title_original"):
        history.append({"title": old_trend["title_original"], "seen_utc": created.isoformat().replace("+00:00", "Z")})
    if title and (not history or history[-1]["title"] != title):
        seen = (datetime.datetime.fromtimestamp(page["last_updated_at_ms"] / 1000, UTC) if page.get("last_updated_at_ms") else now)
        history.append({"title": title, "seen_utc": seen.isoformat(timespec="seconds").replace("+00:00", "Z")})
    meta = {
        "trend": {"id": trend_id, "url": f"https://x.com/i/trending/{trend_id}",
                  "title": title, "title_original": old_trend.get("title_original") or title,
                  "summary_by_grok": summary, "summary_original": old_trend.get("summary_original") or summary,
                  "summary_disclaimer": page.get("disclaimer"),
                  "post_count": post_count if post_count is not None else old_trend.get("post_count"),
                  "title_history": history,
                  "summary_last_updated_utc": (datetime.datetime.fromtimestamp(page["last_updated_at_ms"] / 1000, UTC).isoformat().replace("+00:00", "Z")
                                               if page.get("last_updated_at_ms") else None),
                  "created_at_utc": created.isoformat().replace("+00:00", "Z"),
                  "created_at_ist": created.astimezone(IST).strftime("%Y-%m-%d %H:%M IST")},
        "anchor_post_id": old_meta.get("anchor_post_id") or (posts[0]["id"] if posts else None),
        "keyword": kw or None,
        "first_captured_at_utc": old_meta.get("first_captured_at_utc") or old_meta.get("captured_at_utc") or now.isoformat().replace("+00:00", "Z"),
        "captured_at_utc": now.isoformat().replace("+00:00", "Z"),
        "captured_at_ist": now_ist.strftime("%Y-%m-%d %H:%M IST"),
        "captured_at_pretty": now_ist.strftime("%-I:%M %p").lower() + " IST on " + now_ist.strftime("%B %-d"),
        "counts": {"posts_total": len(posts),
                   "posts_matching_keyword": sum(1 for p in posts if p.get("matches_keyword")) if kw else None,
                   "authors": len({p["author"]["handle"] for p in posts})},
    }
    os.makedirs(a.out, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump({"meta": meta, "posts": posts}, f, ensure_ascii=False, indent=1)
    print(f"saved {len(posts)} posts to {out_path} ({added} new" + (f", {skipped} skipped" if skipped else "")
          + (f", {meta['counts']['posts_matching_keyword']} match '{kw}'" if kw else "") + ")")


if __name__ == "__main__":
    main()

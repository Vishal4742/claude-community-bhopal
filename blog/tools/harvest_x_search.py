#!/usr/bin/env python3
"""Search X through a Nitter mirror, without an account, and add matching posts to tweets.json.

    python3 blog/tools/harvest_x_search.py --out blog/fable-5-1-build-days-bhopal --keyword bhopal \
        --queries "bhopal fable" "bhopal claude" --max-pages 6

X's own search needs a login. Nitter mirrors expose it to anyone, but most sit
behind an Anubis challenge that plain HTTP clients cannot pass; Scrapling's
stealth browser (pip install "scrapling[fetchers]" && scrapling install) can.
One browser session serves the whole run, so the challenge is solved once.
Every result that looks relevant is fetched through X's syndication endpoint,
so the saved rows have the same shape as the rest of tweets.json, and kept only
if it names the keyword alongside the trend's vocabulary, or replies to or
quotes a saved post. Added posts carry in_timelines ["search"]. The mirror is
asked for a few pages per query with a pause between requests.
"""
import argparse
import datetime
import html
import json
import os
import re
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import capture_x_trend as capx  # noqa: E402
import expand_x_archive as ex  # noqa: E402

UTC = capx.UTC
INSTANCES = ["nitter.tiekoetter.com", "xcancel.com", "nitter.privacydev.net"]
CONTEXT = re.compile(r"claude|fable|anthropic|build ?day|buildathon|hackathon|bengaluru|bangalore|\bblr\b|poha", re.I)
DEFAULT_QUERIES = ["bhopal fable", "bhopal claude", "bhopal anthropic", "bhopal buildathon", "bhopal bengaluru",
                   "bhopal build day", "poha claude", "bhopal since:2026-09-10"]


class Mirror:
    """Fetches mirror pages; one stealth browser session for the whole run so the
    challenge is solved once. Returns (status, items, cursor); items are
    (id, text, is_reply) and cursor is the value of the 'Load more' link."""

    def __init__(self, pause):
        self.pause = pause
        try:
            from scrapling.fetchers import StealthySession
            self.session = StealthySession(headless=True)
            self.session.__enter__()
        except ImportError:
            print("scrapling is not installed; plain HTTP rarely passes the mirrors' challenge", file=sys.stderr)
            self.session = None

    def close(self):
        if self.session:
            self.session.__exit__(None, None, None)

    def get(self, url):
        for attempt in range(2):
            if self.session:
                try:
                    page = self.session.fetch(url, wait_selector=".timeline-item", timeout=60000)
                except Exception as e:  # noqa: BLE001  (timeouts, refused connections, challenge not solved)
                    print(f"  {url.split('/')[2]}: {type(e).__name__}", file=sys.stderr)
                    return 0, [], None
                if page.status == 429 and attempt == 0:
                    time.sleep(30)
                    continue
                if page.status != 200:
                    return page.status, [], None
                items = []
                for it in page.css(".timeline-item"):
                    href = it.css("a.tweet-link::attr(href)").get() or ""
                    m = re.search(r"/status/(\d{15,20})", href)
                    if m:
                        text = re.sub(r"\s+", " ", " ".join(it.css(".tweet-content ::text").getall())).strip()
                        items.append((m.group(1), text, bool(it.css(".replying-to"))))
                cursors = [h for h in page.css(".show-more a::attr(href)").getall() if "cursor=" in h]
                cursor = capx.urllib.parse.unquote(cursors[-1].split("cursor=")[-1].split("&")[0]) if cursors else None
                return 200, items, cursor
            code, body = capx.http(url)
            if code == 429 and attempt == 0:
                time.sleep(30)
                continue
            items = [(m, "", False) for m in re.findall(r'class="tweet-link" href="/[A-Za-z0-9_]{1,15}/status/(\d{15,20})', body)]
            cursors = re.findall(r'class="show-more"><a href="[^"]*cursor=([^"&]+)"', body)
            return code, items, (html.unescape(cursors[-1]) if cursors else None)
        return 429, [], None


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", default=".")
    ap.add_argument("--keyword", help="the word a found post must contain (default: the archive's keyword)")
    ap.add_argument("--queries", nargs="*", default=DEFAULT_QUERIES)
    ap.add_argument("--max-pages", type=int, default=6, help="pages per query")
    ap.add_argument("--instance", help="use this mirror only")
    ap.add_argument("--pause", type=float, default=8.0, help="seconds between requests to the mirror (it answers 429 to faster clients)")
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
    mirror = Mirror(a.pause)

    instance, added, seen_ids, stats, first_page = None, [], set(), {}, None
    for inst in ([a.instance] if a.instance else INSTANCES):
        code, items, cursor = mirror.get(f"https://{inst}/search?f=tweets&q={capx.urllib.parse.quote(a.queries[0])}")
        if items:
            instance, first_page = inst, (items, cursor)
            break
        print(f"  {inst}: HTTP {code}, no results (challenge, rate limit or search disabled)", file=sys.stderr)
        time.sleep(a.pause)
    if not instance:
        mirror.close()
        sys.exit("no mirror answered the search")
    print("mirror:", instance)

    for q in a.queries:
        cursor, pages, found = None, 0, 0
        while pages < a.max_pages:
            if q == a.queries[0] and pages == 0 and first_page:
                items, cursor = first_page
            else:
                time.sleep(a.pause)
                url = f"https://{instance}/search?f=tweets&q={capx.urllib.parse.quote(q)}" + (f"&cursor={capx.urllib.parse.quote(cursor)}" if cursor else "")
                code, items, cursor = mirror.get(url)
                if code != 200:
                    print(f"  {q!r}: mirror answered HTTP {code}, moving on")
                    break
            pages += 1
            for tid, text, is_reply in items:
                if tid in by_id or tid in skip or tid in seen_ids or not (start <= capx.snowflake_utc(tid) <= now):
                    continue
                seen_ids.add(tid)
                if not (is_reply or (kw and kw in text.lower())):
                    continue
                t = ex.fetch_post(tid)
                time.sleep(0.2)
                if t is None:
                    skip.add(tid)
                    continue
                row = ex.normalise(t)
                low = row["text"].lower()
                belongs = ((row["in_reply_to"] or {}).get("status_id") in by_id or row["quoted_status_id"] in by_id
                           or (kw and kw in low and CONTEXT.search(low)))
                if not belongs:
                    skip.add(tid)
                    continue
                row["in_timelines"] = ["search"]
                row["first_seen_utc"] = now.isoformat(timespec="seconds").replace("+00:00", "Z")
                row["found_via"] = f"{instance} search: {q}"
                by_id[tid] = row
                added.append(row)
                found += 1
            print(f"  {q!r} page {pages}: {len(items)} results, {found} kept so far")
            if not items or not cursor:
                break
        stats[q] = {"pages": pages, "found": found}
    mirror.close()

    posts = sorted(by_id.values(), key=lambda r: r["created_at_utc"])
    for p in posts:
        p["matches_keyword"] = (kw in p["text"].lower()) if kw else None
    meta["counts"]["posts_total"] = len(posts)
    meta["counts"]["posts_matching_keyword"] = sum(1 for p in posts if p.get("matches_keyword")) if kw else None
    meta["counts"]["authors"] = len({p["author"]["handle"] for p in posts})
    meta["counts"]["posts_from_search"] = sum(1 for p in posts if "search" in (p.get("in_timelines") or []))
    meta.setdefault("expand", {})["not_posts"] = sorted(skip)[-5000:]
    meta["search"] = {"last_run_utc": now.isoformat(timespec="seconds").replace("+00:00", "Z"), "instance": instance, "queries": stats}
    with open(path, "w", encoding="utf-8") as f:
        json.dump({"meta": meta, "posts": posts}, f, ensure_ascii=False, indent=1)
    print(f"saved {len(posts)} posts ({len(added)} new from search, {meta['counts']['posts_from_search']} in total"
          + (f", {meta['counts']['posts_matching_keyword']} match '{kw}'" if kw else "") + ")")


if __name__ == "__main__":
    main()

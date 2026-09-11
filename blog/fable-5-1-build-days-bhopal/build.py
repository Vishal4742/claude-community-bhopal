#!/usr/bin/env python3
"""Build this post's index.html (and tweets.csv) from tweets.json.

    python3 blog/fable-5-1-build-days-bhopal/build.py

Run capture_x_trend.py first to refresh tweets.json. Images and avatars for the
posts shown are fetched into media/ on first use and kept after that.
"""
import csv
import datetime
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "tools"))
import blogkit as bk  # noqa: E402

SLUG = os.path.basename(HERE)
POST_URL = f"{bk.SITE}/blog/{SLUG}/"
MEDIA = os.path.join(HERE, "media")
os.makedirs(MEDIA, exist_ok=True)

TITLE = "The night Bhopal trended on X"
DESC = ("Claude announced Fable 5.1 Build Days in cities around the world. Bhopal was the only Indian city on the list, "
        "and X noticed. Every post that named Bhopal, saved in one place, plus the Build Day on Sep 20.")

# Posts that are about Bhopal without using the word (hand-picked).
CONTEXT_IDS = {
    "2098155215367377346", "2098253864424357947", "2098261992524144910", "2098191966525874523", "2098291317088657818",
    "2098300201345974558", "2098300320895967608", "2098300663591752142", "2098305414035075521", "2098306439479705870",
}

# Featured cards, grouped by mood (hand-picked; ids missing from tweets.json are skipped).
GROUPS = [
    ("Bhopal, on the map", "The hometown crowd woke up to good news.",
     ["2098269800204263690", "2098226939731583245", "2098279981331906567", "2098267027677102416", "2098229368309039191",
      "2098291244921397416", "2098204659035034063", "2098270852840366541", "2098243567710044405", "2098261700076339555",
      "2098254687376204029", "2098266915734982774", "2098303996108959764"]),
    ("Sorry, Bengaluru", "The most-viewed posts of the night were about the city that was not on the list.",
     ["2098145206650692009", "2098190601644888455", "2098148045389201461", "2098149439584317883", "2098155215367377346",
      "2098253864424357947", "2098268060738338990", "2098275536506433621", "2098231941250334861", "2098188540798705972",
      "2098272331798040775", "2098178895640166585", "2098306513437851727", "2098306480797868441"]),
    ("Bengaluru gets one too, afterwards", "There was no Bengaluru Build Day when the trend started. One went up after it, announced at 1:44 pm by its host, for Friday the 25th. Bhopal's, on the 20th, came first.",
     ["2098324283143700669", "2098328022890029508", "2098326733825229259", "2098333150204076220", "2098325311838634384"]),
    ("Wait, why Bhopal?", 'Fair question. The answer is a few scrolls up, under <a href="#why-bhopal">Why Bhopal?</a>',
     ["2098186648357843343", "2098148907704520830", "2098142420416512215", "2098230260051693859", "2098195509014106121",
      "2098251137153691990", "2098221619965768021", "2098289813732626887", "2098288267221520554", "2098291317088657818",
      "2098273574322831854", "2098228434443162050"]),
    ("The memes", "Poha stocks are up.",
     ["2098191966525874523", "2098158341524738408", "2098182461754839131", "2098292489627292141", "2098289796829380654",
      "2098180941483323446", "2098305414035075521"]),
    ("From the people making it happen", "The organisers and regulars of the Bhopal chapter, replying with a Luma link.",
     ["2098261992524144910", "2098252000450457658", "2098289190081638684"]),
]

BUILD_DAYS = [("Cape Town", "Sat, Sep 12"), ("Oslo", "Mon, Sep 14"), ("Brisbane", "Wed, Sep 16"), ("Chicago", "Wed, Sep 16"),
              ("Sydney", "Thu, Sep 17"), ("New York", "Thu, Sep 17"), ("Tel Aviv", "Thu, Sep 17"), ("Mexico City", "Thu, Sep 17"), ("Singapore", "Fri, Sep 18"),
              ("Osaka", "Sat, Sep 19"), ("Medellín", "Sat, Sep 19"), ("Nairobi", "Sat, Sep 19"), ("San Francisco", "Sat, Sep 19"),
              ("Austin", "Sat, Sep 19"), ("Bhopal", "Sun, Sep 20"), ("Taipei", "Sun, Sep 20"), ("Miami", "Sun, Sep 20"),
              ("Seoul", "Wed, Sep 23"), ("Barcelona", "Wed, Sep 23"), ("Melbourne", "Thu, Sep 24"), ("Bengaluru", "Fri, Sep 25")]

# ---------------------------------------------------------------- data
with open(os.path.join(HERE, "tweets.json"), encoding="utf-8") as f:
    data = json.load(f)
meta = data["meta"]
posts = {p["id"]: p for p in data["posts"]}
for p in posts.values():
    p["mentions_bhopal"] = bool(p.get("matches_keyword", p.get("mentions_bhopal", False)))
    p["about_bhopal"] = p["mentions_bhopal"] or p["id"] in CONTEXT_IDS
ordered = sorted(posts.values(), key=lambda p: p["created_at_utc"])
anchor = posts[meta["anchor_post_id"]]
about = [p for p in ordered if p["about_bhopal"] and p["id"] != anchor["id"]]
counts = {"posts_total": len(ordered), "posts_mentioning_bhopal": sum(1 for p in ordered if p["mentions_bhopal"]),
          "posts_about_bhopal": len(about)}
featured_ids = [pid for _, _, ids in GROUPS for pid in ids if pid in posts]

# media for everything that appears on the page
for p in [anchor] + about + [posts[i] for i in featured_ids]:
    bk.ensure_media(p, MEDIA)

esc, fmt, tpl = bk.esc, bk.fmt, bk.tpl

# ---------------------------------------------------------------- page
groups_html = ""
for title, lead, ids in GROUPS:
    cards = "".join(bk.card(posts[i], posts, MEDIA) for i in ids if i in posts)
    groups_html += f'<h3 class="kicker">{esc(title)}</h3><p class="lead">{lead}</p><div class="cards">{cards}</div>'
archive_html = "\n".join(bk.archive_card(p, i, MEDIA, tagged=not p["mentions_bhopal"]) for i, p in enumerate(about, 1))
context_n = counts["posts_about_bhopal"] - sum(1 for p in about if p["mentions_bhopal"])
bd_html = "".join(f'<li{" class=\"here\"" if c_ == "Bhopal" else ""}><b>{c_}</b><span>{d}</span></li>' for c_, d in BUILD_DAYS)
tr = meta["trend"]
renamed = (f' and later renamed <em>"{esc(tr["title"])}"</em>' if tr.get("title") and tr["title"] != tr.get("title_original") else "")
correction = ("<p>One correction to that summary. Luma still showed seats for the Impact Lab when this page was last built, "
              "so it was not sold out.</p>" if "sold" in (tr.get("summary_by_grok") or "") else "")
x_count = tr.get("post_count")
proof_html = (f'<li>{x_count:,} posts in the trend, by X\'s count</li><li>{counts["posts_total"]} saved here, readable without an account</li>'
              if x_count else f'<li>{counts["posts_total"]} posts in the trend</li>')
lead_open = ((f'X counts {x_count:,} posts in this trend but shows only some of them to readers without an account: '
              f'the trend\'s own timelines, plus the replies visible under each post. All of those were read, one by one. '
              f'Of the {counts["posts_total"]} saved so far, ')
             if x_count else f'Every post in the trend, read one by one. Of {counts["posts_total"]}, ')
now_ist = datetime.datetime.now(bk.IST).replace(second=0, microsecond=0)
jsonld = json.dumps({
    "@context": "https://schema.org", "@type": "BlogPosting", "headline": TITLE, "description": DESC,
    "image": [f"{POST_URL}og.jpg"], "datePublished": "2026-09-11T14:00:00+05:30", "dateModified": now_ist.isoformat(),
    "inLanguage": "en-IN", "mainEntityOfPage": POST_URL,
    "author": {"@type": "Organization", "name": "Claude Community Bhopal", "url": bk.SITE},
    "publisher": {"@type": "Organization", "name": "Claude Community Bhopal", "url": bk.SITE,
                  "logo": {"@type": "ImageObject", "url": f"{bk.SITE}/assets/claude-logo.png"}},
    "about": [{"@type": "Event", "name": "Bhopal | Claude Code Build Day - Fable 5.1",
               "startDate": "2026-09-20T11:00:00+05:30", "endDate": "2026-09-20T18:00:00+05:30",
               "url": "https://luma.com/claude-z01j", "eventAttendanceMode": "https://schema.org/OfflineEventAttendanceMode",
               "eventStatus": "https://schema.org/EventScheduled", "isAccessibleForFree": True,
               "location": {"@type": "Place", "name": "Bhopal",
                            "address": {"@type": "PostalAddress", "addressLocality": "Bhopal", "addressRegion": "Madhya Pradesh", "addressCountry": "IN"}},
               "organizer": {"@type": "Organization", "name": "Claude Community Bhopal", "url": bk.SITE},
               "offers": {"@type": "Offer", "price": "0", "priceCurrency": "INR", "url": "https://luma.com/claude-z01j",
                          "availability": "https://schema.org/InStock"}}],
}, ensure_ascii=False, indent=1)

body = f'''{bk.FILTERS}
{bk.nav("../assets/", "../index.html")}
<header class="hero">
  <div class="wrap hero-grid">
    <div>
      <p class="label">Blog · Thursday, September 11, 2026 · 8 min read</p>
      <h1>The night Bhopal <em>trended</em> on X</h1>
      <p class="deck">Claude announced Fable 5.1 Build Days in cities around the world. One Indian city made the list. The timeline had opinions. All of them are saved here.</p>
      <ul class="proof">{proof_html}<li>{counts["posts_mentioning_bhopal"]} name Bhopal</li><li>{fmt(anchor["metrics"]["views"])} views on the announcement</li></ul>
    </div>
    <figure class="hero-fig">
      <div class="polaroid">
        <video src="media/{anchor["id"]}-0.mp4" poster="media/{anchor["id"]}-0-thumb.jpg" controls preload="none" playsinline width="960" height="1200" aria-label="Claude's Fable 5.1 Build Days announcement video"></video>
        <figcaption>@claudeai · 1:27 am, Sep 11 · <a href="{esc(anchor["url"])}" target="_blank" rel="noopener">watch on X ↗</a></figcaption>
      </div>
    </figure>
  </div>
</header>

<main>
<section class="paper" id="what-happened">
  <div class="wrap narrow">
    <h2 class="kicker">What happened</h2>
    <p>At 1:27 am on Thursday, <a href="https://x.com/claudeai" target="_blank" rel="noopener">@claudeai</a> posted a 30-second video. Fable 5.1 Build Days, a worldwide buildathon from September 11 to 25, with the Claude community hosting in cities across every continent. The video scrolls through the host cities. Nairobi. Stockholm. Cape Town. Oslo. Mexico City. Osaka. Miami. Then, in a clay-coloured box: <strong>Bhopal</strong>.</p>
    <p>Bhopal was the only Indian city on the list. No Bengaluru, no Delhi, no Mumbai, no Hyderabad. Within half an hour the quote-posts started, and they did not stop. By 5:37 am X's trending system had bundled the conversation into its own story page, first titled <em>"{esc(tr.get("title_original") or tr.get("title") or "")}"</em>{renamed}. That page is where this post comes from.</p>
    <p><strong>Update, 2 pm IST:</strong> Bengaluru is on the list now, and it got there after Bhopal trended. There was no Bengaluru event when the announcement went out at 1:27 am. The first word of one came at 1:44 pm, twelve hours later, from <a href="https://x.com/knowShubhangi" target="_blank" rel="noopener">@knowShubhangi</a>, who is hosting it: a <a href="https://luma.com/claude-x5dm" target="_blank" rel="noopener">Claude Fable Build Day in Bengaluru</a> on Friday, September 25, followed by a Claude Conversation in Mumbai on the 26th. Bhopal, on the 20th, was first on the list and is first on the calendar.</p>
    {bk.card(anchor, posts, MEDIA)}
    <p class="asof">Counts on this page are as of {esc(meta.get("captured_at_pretty") or meta.get("captured_at_ist") or "")}. They will have moved since.</p>
    <blockquote class="grok">
      <p>{esc(tr.get("summary_by_grok") or "")}</p>
      <cite>X's summary of the trend, written by Grok. X adds: "{esc(tr.get("summary_disclaimer") or "")}"</cite>
    </blockquote>
    {correction}
  </div>
</section>

<section class="ink-section" id="why-bhopal">
  <div class="wrap narrow">
    <h2 class="kicker cream">Why Bhopal?</h2>
    <p>Because the local chapter put an event on the calendar. Build Days are hosted by Claude community chapters in each city, and Bhopal has one: a volunteer-run group, hosted by The Origin Guild, that has held nine free meetups since March, from Claude Code workshops to a full-day Impact Lab in August. When the Fable 5.1 Build Days went up on the global calendar, Bhopal was on it.</p>
    <p>Three events are on the chapter's calendar for September, and the Build Day is the one the whole timeline was arguing about.</p>
    <div class="ev-grid">
      <a class="ev" href="https://luma.com/claude-6khk" target="_blank" rel="noopener"><span class="ev-date">Sat, Sep 12 · 6:00–8:30 pm</span><span class="ev-title">Claude Conversation</span><span class="ev-desc">A small room, one question: what does AI mean for the future of building startups? The problem the room picks becomes Sunday's build.</span><span class="ev-cta">Reserve a seat ↗</span></a>
      <a class="ev" href="https://luma.com/claude-r61u" target="_blank" rel="noopener"><span class="ev-date">Sun, Sep 13 · 10 am–7 pm</span><span class="ev-title">Claude Impact Lab</span><span class="ev-desc">A full day of building on Saturday's problem, in teams, with demos by evening.</span><span class="ev-cta">Reserve a seat ↗</span></a>
      <a class="ev hot" href="https://luma.com/claude-z01j" target="_blank" rel="noopener"><span class="ev-date">Sun, Sep 20 · 11 am–6 pm</span><span class="ev-title">Claude Code Build Day · Fable 5.1</span><span class="ev-desc">The Build Day everyone was posting about. Three tracks: Delight, Breakthrough, Everyday. Solo or teams of 2–4. Hosted by Aniket Sahu, who runs the chapter's events.</span><span class="ev-cta">Register, it's free ↗</span></a>
    </div>
    <p class="fine">All three are free and approval-based. Register early on Luma. The venue is shared with confirmed registrants.</p>
    <h3 class="kicker cream small">Where else Build Days are happening</h3>
    <ul class="bd-list">{bd_html}</ul>
    <p class="fine">From the <a href="https://luma.com/claudecommunity?tag=build%20day" target="_blank" rel="noopener">Claude Community calendar</a> on Luma, as of September 11. More cities keep getting added.</p>
  </div>
</section>

<section class="paper" id="reactions">
  <div class="wrap">
    <h2 class="kicker">What the timeline said</h2>
    <p class="lead-wide">{lead_open}{counts["posts_mentioning_bhopal"]} name Bhopal directly and a handful more are clearly about it. Here are the ones worth your time, grouped by mood. The full list is at the bottom.</p>
    {groups_html}
  </div>
</section>

<section class="clay-section" id="the-reply">
  <div class="wrap narrow">
    <h2 class="kicker">The reply from Bhopal</h2>
    <p class="big">The chapter's answer to the jokes is a date. On Sunday, September 20, the people who signed up will spend the day building with the newest model there is, in the city the whole timeline was posting about. Anyone travelling from Bengaluru has already been offered a couch by at least one person on X. And since Bengaluru got a date of its own out of all this, Friday the 25th, the couch offers can go both ways.</p>
    <p><a class="btn btn-dark" href="https://luma.com/claude-z01j" target="_blank" rel="noopener"><span>Register for the Bhopal Build Day</span><span class="arrow">↗</span></a></p>
  </div>
</section>

<section class="paper" id="archive">
  <div class="wrap">
    <h2 class="kicker">Every post that named Bhopal</h2>
    <p class="lead-wide">{counts["posts_about_bhopal"]} posts, exactly as their authors wrote them, salty bits included. Times are IST. {bk.number_word(context_n)} of them talk about Bhopal without using the word; those are marked.</p>
    <div class="ar-tools" hidden>
      <div class="ar-sort" role="group" aria-label="Sort posts">
        <button type="button" data-sort="old" aria-pressed="true">Oldest first</button>
        <button type="button" data-sort="new" aria-pressed="false">Newest first</button>
        <button type="button" data-sort="views" aria-pressed="false">Most seen</button>
        <button type="button" data-sort="likes" aria-pressed="false">Most liked</button>
      </div>
      <label class="ar-search"><span class="sr-only">Filter posts</span><input type="search" id="arFilter" placeholder="Filter by a word or @handle" autocomplete="off"></label>
      <span class="ar-count" id="arCount" aria-live="polite">{counts["posts_about_bhopal"]} posts</span>
    </div>
    <ol class="ar-wall" id="arWall">
{archive_html}
    </ol>
    <p class="ar-empty" id="arEmpty" hidden>Nothing matches that. Try another word.</p>
  </div>
</section>

</main>
{bk.foot("../assets/", "../index.html")}
</body>
</html>
'''
page = bk.head(title=f"{TITLE} · Claude Community Bhopal", desc=esc(DESC), assets="../assets/", url=POST_URL, ogtype="article",
               ogtitle=esc(TITLE), ogimg=f"{POST_URL}og.jpg",
               ogalt="The night Bhopal trended on X. Fable 5.1 Build Days, Sunday September 20.",
               jsonld=f'<script type="application/ld+json">\n{jsonld}\n</script>') + body
with open(os.path.join(HERE, "index.html"), "w", encoding="utf-8") as f:
    f.write(page)
with open(os.path.join(HERE, "tweets.csv"), "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f)
    w.writerow(["id", "url", "handle", "name", "created_at_ist", "type", "likes", "reposts", "replies", "views", "mentions_bhopal", "text"])
    for p in about:
        w.writerow([p["id"], p["url"], p["author"]["handle"], p["author"]["name"], p["created_at_ist"], p["type"],
                    p["metrics"]["likes"], p["metrics"]["reposts"], p["metrics"]["replies"], p["metrics"]["views"], p["mentions_bhopal"], p["text"]])
print(f"built {SLUG}: {counts['posts_total']} posts, {counts['posts_mentioning_bhopal']} name Bhopal, "
      f"{counts['posts_about_bhopal']} in the archive, {len(featured_ids)} featured, media files {len(os.listdir(MEDIA))}")

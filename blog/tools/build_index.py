#!/usr/bin/env python3
"""Build blog/index.html, the list of posts.

    python3 blog/tools/build_index.py

Add new posts to POSTS (newest first).
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import blogkit as bk  # noqa: E402

BLOG = os.path.join(HERE, "..")
URL = f"{bk.SITE}/blog/"
DESC = ("Notes from the Claude community in Bhopal: what happened at our meetups, what people built, "
        "and the occasional night we trend on X.")
POSTS = [
    {"slug": "fable-5-1-build-days-bhopal", "title": "The night Bhopal trended on X",
     "date": "September 11, 2026", "iso": "2026-09-11T14:00:00+05:30", "read": "8 min read",
     "desc": ("Claude announced Fable 5.1 Build Days in cities around the world. Bhopal was the only Indian city on the list, "
              "and X noticed. Every post that named Bhopal, saved in one place, plus the Build Day on Sep 20.")},
]

esc = bk.esc
jsonld = json.dumps({
    "@context": "https://schema.org", "@type": "Blog", "name": "Claude Community Bhopal · Blog", "url": URL, "description": DESC,
    "publisher": {"@type": "Organization", "name": "Claude Community Bhopal", "url": bk.SITE},
    "blogPost": [{"@type": "BlogPosting", "headline": p["title"], "url": f"{URL}{p['slug']}/", "datePublished": p["iso"],
                  "image": f"{URL}{p['slug']}/og.jpg"} for p in POSTS],
}, ensure_ascii=False, indent=1)
cards = "".join(f'''
      <li class="post-card">
        <a class="post-cover" href="{p["slug"]}/index.html"><img src="{p["slug"]}/og.jpg" alt="" width="1200" height="630" loading="lazy"></a>
        <div class="post-body">
          <p class="label">{esc(p["date"])} · {esc(p["read"])}</p>
          <h2><a href="{p["slug"]}/index.html">{esc(p["title"])}</a></h2>
          <p>{esc(p["desc"])}</p>
          <a class="tl-link" href="{p["slug"]}/index.html">Read the post <span aria-hidden="true">→</span></a>
        </div>
      </li>''' for p in POSTS)
body = f'''{bk.FILTERS}
{bk.nav("assets/", "index.html", current=True)}
<header class="hero hero-short">
  <div class="wrap">
    <p class="label">Blog</p>
    <h1>Notes from <em>Bhopal</em></h1>
    <p class="deck">What happened at our meetups, what people built, and the occasional night we trend on X.</p>
  </div>
</header>
<main>
<section class="paper">
  <div class="wrap">
    <ul class="post-list">{cards}
    </ul>
  </div>
</section>
</main>
{bk.foot("assets/", "index.html")}
</body>
</html>
'''
page = bk.head(title="Blog · Claude Community Bhopal", desc=esc(DESC), assets="assets/", url=URL, ogtype="website",
               ogtitle="Blog · Claude Community Bhopal", ogimg=f"{URL}{POSTS[0]['slug']}/og.jpg", ogalt="Claude Community Bhopal blog",
               jsonld=f'<script type="application/ld+json">\n{jsonld}\n</script>') + body
with open(os.path.join(BLOG, "index.html"), "w", encoding="utf-8") as f:
    f.write(page)
print(f"built blog/index.html with {len(POSTS)} post(s)")

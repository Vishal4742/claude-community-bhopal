"""Shared pieces for building blog posts: page chrome, tweet cards, media fetching.

Used by each post's build.py. Only the standard library is required; Pillow is
optional and, when present, resizes images and avatars so the repo stays small.
"""
import datetime
import html
import os
import re
import shutil
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
SITE = "https://claude-community-bhopal.netlify.app"
IST = datetime.timezone(datetime.timedelta(hours=5, minutes=30))
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/128.0 Safari/537.36")
MAX_VIDEO_BYTES = 4_000_000

with open(os.path.join(HERE, "blog.css"), encoding="utf-8") as _f:
    CSS = _f.read()

# ---------------------------------------------------------------- helpers

def tpl(t, **kw):
    for k, v in kw.items():
        t = t.replace("{" + k + "}", str(v))
    return t


def esc(s):
    return html.escape(s or "", quote=True)


def when(p):
    dt = datetime.datetime.fromisoformat(p["created_at_utc"].replace("Z", "+00:00")).astimezone(IST)
    return dt.strftime("%-I:%M %p · %b %-d").replace("AM", "am").replace("PM", "pm")


def epoch(p):
    return int(datetime.datetime.fromisoformat(p["created_at_utc"].replace("Z", "+00:00")).timestamp())


def fmt(n):
    n = n or 0
    if n >= 1_000_000:
        return f"{n/1e6:.1f}M".replace(".0M", "M")
    if n >= 1000:
        return f"{n/1e3:.1f}K".replace(".0K", "K")
    return str(n)


def rich(text):
    t = esc(text)
    t = re.sub(r'(https?://[^\s<]+)',
               lambda m: f'<a href="{m.group(1)}" target="_blank" rel="noopener">{re.sub(r"^https?://(www\.)?", "", m.group(1))[:48]}</a>', t)
    t = re.sub(r'(?<![\w/])@([A-Za-z0-9_]{1,15})',
               r'<a href="https://x.com/\1" target="_blank" rel="noopener">@\1</a>', t)
    return t.replace("\n", "<br>")


NUMBER_WORDS = {0: "None", 1: "One", 2: "Two", 3: "Three", 4: "Four", 5: "Five", 6: "Six", 7: "Seven", 8: "Eight",
                9: "Nine", 10: "Ten", 11: "Eleven", 12: "Twelve", 13: "Thirteen", 14: "Fourteen", 15: "Fifteen"}


def stat(title, icon, value):
    """One metric for a card footer; nothing when X did not expose it (None)."""
    return "" if value is None else f'<span title="{title}">{icon} {fmt(value)}</span>'


def number_word(n):
    return NUMBER_WORDS.get(n, str(n))

# ---------------------------------------------------------------- media

def download(url, path, timeout=40, max_bytes=None):
    try:
        req = urllib.request.Request(url, headers={"User-Agent": UA})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            data = r.read(max_bytes + 1) if max_bytes else r.read()
        if max_bytes and len(data) > max_bytes:
            return False
        with open(path, "wb") as f:
            f.write(data)
        return True
    except Exception:
        return False


def save_image(src, dst, avatar=False):
    try:
        from PIL import Image, ImageOps
    except ImportError:
        shutil.copy(src, dst)
        return True
    try:
        im = ImageOps.exif_transpose(Image.open(src))
        if avatar:
            im = im.convert("RGB").resize((160, 160), Image.LANCZOS)
            im.save(dst, "JPEG", quality=85, optimize=True)
        else:
            w, h = im.size
            m = max(w, h)
            if m > 1200:
                im = im.resize((round(w * 1200 / m), round(h * 1200 / m)), Image.LANCZOS)
            if im.mode in ("RGBA", "LA", "P"):
                bg = Image.new("RGB", im.size, (251, 248, 241))
                bg.paste(im.convert("RGBA"), mask=im.convert("RGBA").split()[-1])
                im = bg
            else:
                im = im.convert("RGB")
            im.save(dst, "JPEG", quality=84, optimize=True, progressive=True)
        return True
    except Exception:
        return False


def _fetch_image(url, dst, avatar=False):
    if not url or os.path.exists(dst):
        return os.path.exists(dst)
    tmp = dst + ".tmp"
    ok = download(url, tmp)
    if ok:
        ok = save_image(tmp, dst, avatar=avatar)
    if os.path.exists(tmp):
        os.remove(tmp)
    return ok


def ensure_avatar(post, media_dir):
    h = post["author"]["handle"]
    dst = os.path.join(media_dir, f"avatar-{h}.jpg")
    url = (post["author"].get("profile_image") or "").replace("_400x400", "_200x200").replace("_normal", "_200x200")
    return f"media/avatar-{h}.jpg" if _fetch_image(url, dst, avatar=True) else None


def ensure_media(post, media_dir):
    pid = post["id"]
    for i, m in enumerate(post.get("media") or []):
        if m.get("type") == "photo":
            url = m.get("url") or ""
            mm = re.match(r"^(.*)\.(jpg|jpeg|png|webp)$", url)
            big = f"{mm.group(1)}?format={mm.group(2)}&name=large" if mm else url
            dst = os.path.join(media_dir, f"{pid}-{i}.jpg")
            if not _fetch_image(big, dst):
                _fetch_image(url, dst)
        else:
            _fetch_image(m.get("thumbnail") or m.get("url") or "", os.path.join(media_dir, f"{pid}-{i}-thumb.jpg"))
            vu = m.get("video_url")
            dstv = os.path.join(media_dir, f"{pid}-{i}.mp4")
            if vu and not os.path.exists(dstv):
                download(vu, dstv, timeout=90, max_bytes=MAX_VIDEO_BYTES)


def media_for(post, media_dir):
    out = []
    for i, m in enumerate(post.get("media") or []):
        if m.get("type") == "photo":
            f = f"{post['id']}-{i}.jpg"
            if os.path.exists(os.path.join(media_dir, f)):
                out.append(("photo", f"media/{f}", None))
        else:
            th = f"{post['id']}-{i}-thumb.jpg"
            mp = f"{post['id']}-{i}.mp4"
            has_th = os.path.exists(os.path.join(media_dir, th))
            if os.path.exists(os.path.join(media_dir, mp)):
                out.append((m.get("type"), f"media/{mp}", f"media/{th}" if has_th else None))
            elif has_th:
                out.append(("photo", f"media/{th}", None))
    return out

# ---------------------------------------------------------------- cards

def card(post, posts, media_dir, note=None):
    p = post
    a = p["author"]
    av = ensure_avatar(p, media_dir)
    m = p["metrics"]
    ctx = ""
    if p["type"] == "reply" and p.get("in_reply_to"):
        h = esc(p["in_reply_to"]["handle"])
        ctx = f'<div class="tw-ctx">replying to <a href="https://x.com/{h}" target="_blank" rel="noopener">@{h}</a></div>'
    elif p["type"] == "quote" and p.get("quoted_status_id") in posts:
        q = posts[p["quoted_status_id"]]
        ctx = f'<div class="tw-ctx">quoting <a href="{esc(q["url"])}" target="_blank" rel="noopener">@{esc(q["author"]["handle"])}</a></div>'
    avatar = (f'<img class="tw-av" src="{av}" alt="" width="44" height="44" loading="lazy">' if av
              else f'<span class="tw-av tw-av-txt" aria-hidden="true">{esc((a["name"] or "?")[0].upper())}</span>')
    med = ""
    for typ, src, poster in media_for(p, media_dir):
        pstr = f' poster="{poster}"' if poster else ""
        if typ == "photo":
            med += f'<a class="tw-media" href="{esc(p["url"])}" target="_blank" rel="noopener"><img src="{src}" alt="Image attached to the post" loading="lazy"></a>'
        elif typ == "animated_gif":
            med += f'<video class="tw-media" src="{src}"{pstr} autoplay loop muted playsinline aria-label="GIF attached to the post"></video>'
        else:
            med += f'<video class="tw-media" src="{src}"{pstr} controls preload="none" playsinline aria-label="Video attached to the post"></video>'
    notehtml = f'<div class="tw-note">{esc(note)}</div>' if note else ""
    return f'''<article class="tw" id="p{p["id"]}">
  <header class="tw-head">{avatar}<div class="tw-who"><a class="tw-name" href="https://x.com/{esc(a["handle"])}" target="_blank" rel="noopener">{esc(a["name"] or a["handle"])}</a><span class="tw-handle">@{esc(a["handle"])}</span></div><a class="tw-time" href="{esc(p["url"])}" target="_blank" rel="noopener">{when(p)}</a></header>
  {ctx}<p class="tw-text">{rich(p["text"])}</p>{med}
  <footer class="tw-foot">{stat("likes", "♥", m["likes"])}{stat("reposts", "⟲", m["reposts"])}{stat("replies", "✎", m["replies"])}{stat("views", "◉", m["views"])}<a href="{esc(p["url"])}" target="_blank" rel="noopener">Open on X ↗</a></footer>{notehtml}
</article>'''


def archive_card(post, i, media_dir, tag_text="about Bhopal", tagged=False, themes=()):
    p = post
    a = p["author"]
    av = ensure_avatar(p, media_dir)
    m = p["metrics"]
    tag = f'<span class="ar-tag">{esc(tag_text)}</span>' if tagged else ""
    avatar = (f'<img class="ar-av" src="{av}" alt="" width="36" height="36" loading="lazy">' if av
              else f'<span class="ar-av ar-av-txt" aria-hidden="true">{esc((a["name"] or "?")[0].upper())}</span>')
    thumb = ""
    for typ, src, poster in media_for(p, media_dir):
        img = src if typ == "photo" else poster
        if img:
            thumb = f'<a class="ar-thumb" href="{esc(p["url"])}" target="_blank" rel="noopener"><img src="{img}" alt="" loading="lazy"></a>'
            break
    search = esc((p["text"] + " " + a["handle"] + " " + (a["name"] or "")).lower())
    return f'''<li class="ar-card" data-t="{epoch(p)}" data-views="{m["views"] or 0}" data-likes="{m["likes"] or 0}" data-themes="{" ".join(themes)}" data-s="{search}">
  <div class="ar-head">{avatar}<div class="ar-who"><a class="ar-name" href="https://x.com/{esc(a["handle"])}" target="_blank" rel="noopener">{esc(a["name"] or a["handle"])}</a><span class="ar-handle">@{esc(a["handle"])}</span></div><span class="ar-n">{i:02d}</span></div>
  <p class="ar-text">{rich(p["text"])}</p>{thumb}
  <div class="ar-foot"><a class="ar-time" href="{esc(p["url"])}" target="_blank" rel="noopener">{when(p)} ↗</a>{tag}<span class="ar-stats">♥ {fmt(m["likes"])}{" · ◉ " + fmt(m["views"]) if m["views"] is not None else ""}</span></div>
</li>'''

# ---------------------------------------------------------------- page chrome

FILTERS = '''<svg width="0" height="0" style="position:absolute" aria-hidden="true">
  <filter id="rough"><feTurbulence type="fractalNoise" baseFrequency="0.014" numOctaves="2" result="n"/><feDisplacementMap in="SourceGraphic" in2="n" scale="3"/></filter>
  <filter id="pencil"><feTurbulence type="fractalNoise" baseFrequency="0.03" numOctaves="2" seed="2" result="n"/><feDisplacementMap in="SourceGraphic" in2="n" scale="2"/></filter>
</svg>'''

NAV = '''<nav>
  <div class="nav-inner">
    <a href="{site}/" class="brand"><img src="{assets}claude-logo.png" alt="Claude" width="482" height="104"><span class="city">Bhopal</span></a>
    <button class="nav-toggle" id="navToggle" aria-label="Menu" aria-expanded="false" aria-controls="navLinks"><span></span><span></span><span></span></button>
    <div class="nav-links" id="navLinks">
      <a href="{site}/#upcoming">Upcoming</a>
      <a href="{site}/#join-roles">Join Roles</a>
      <a href="{site}/#faq">FAQ</a>
      <a href="{blogroot}" {blogcur}>Blog</a>
      <a href="{cta_url}" class="nav-cta" target="_blank" rel="noopener">{cta_text}</a>
    </div>
  </div>
</nav>'''

FOOT = '''<footer>
  <div class="wrap foot">
    <a href="{site}/" class="brand" style="gap:10px"><img src="{assets}claude-logo.png" alt="Claude" width="482" height="104"><span class="foot-tag">Bhopal</span></a>
    <div class="foot-links">
      <a href="{site}/#upcoming">Upcoming</a>
      <a href="{site}/#join-roles">Open Calls</a>
      <a href="{site}/#faq">FAQ</a>
      <a href="{blogroot}">Blog</a>
      <a href="https://t.me/tog_guild" target="_blank" rel="noopener">Telegram</a>
      <a href="https://www.instagram.com/theoriginguild" target="_blank" rel="noopener">Instagram</a>
      <a href="https://x.com/og_guild" target="_blank" rel="noopener">X / Twitter</a>
      <a href="https://www.linkedin.com/company/theoriginguild" target="_blank" rel="noopener">LinkedIn</a>
    </div>
    <span class="foot-tag">City of Lakes <span aria-hidden="true">✻</span></span>
  </div>
  <div class="foot-sub">
    <span>© 2026 Claude Community Bhopal · Hosted by The Origin Guild</span>
    <span>Code of Conduct · Open &amp; Non-commercial Community</span>
  </div>
</footer>
<script>
const t=document.getElementById('navToggle'),l=document.getElementById('navLinks');
const setMenu=open=>{l.classList.toggle('open',open);t.setAttribute('aria-expanded',open)};
t.addEventListener('click',()=>setMenu(!l.classList.contains('open')));
addEventListener('keydown',e=>{if(e.key==='Escape'&&l.classList.contains('open')){setMenu(false);t.focus()}});
matchMedia('(min-width:901px)').addEventListener('change',e=>{if(e.matches)setMenu(false)});
(function(){
  const wall=document.getElementById('arWall');if(!wall)return;
  const tools=document.querySelector('.ar-tools'),count=document.getElementById('arCount'),empty=document.getElementById('arEmpty'),input=document.getElementById('arFilter');
  tools.hidden=false;
  const cards=Array.from(wall.children);
  const key={old:c=>+c.dataset.t,new:c=>-c.dataset.t,views:c=>-c.dataset.views,likes:c=>-c.dataset.likes};
  let mode='views',theme='all';
  function apply(){
    const q=(input.value||'').trim().toLowerCase();
    const sorted=cards.slice().sort((a,b)=>key[mode](a)-key[mode](b)||(+a.dataset.t-+b.dataset.t));
    let n=0;sorted.forEach(c=>{const ok=(!q||c.dataset.s.includes(q))&&(theme==='all'||(c.dataset.themes||'').split(' ').includes(theme));c.hidden=!ok;if(ok)n++;wall.appendChild(c)});
    count.textContent=n+(n===1?' post':' posts');empty.hidden=n>0;
  }
  tools.querySelectorAll('[data-sort]').forEach(b=>b.addEventListener('click',()=>{mode=b.dataset.sort;tools.querySelectorAll('[data-sort]').forEach(x=>x.setAttribute('aria-pressed',x===b));apply()}));
  tools.querySelectorAll('[data-theme]').forEach(b=>b.addEventListener('click',()=>{theme=b.dataset.theme;tools.querySelectorAll('[data-theme]').forEach(x=>x.setAttribute('aria-pressed',x===b));apply()}));
  input.addEventListener('input',apply);
})();
</script>'''

HEAD = '''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{title}</title>
<meta name="description" content="{desc}">
<link rel="icon" type="image/png" sizes="64x64" href="{assets}favicon.png">
<link rel="apple-touch-icon" href="{assets}apple-touch-icon.png">
<meta name="theme-color" content="#D97757">
<link rel="canonical" href="{url}">
<meta property="og:type" content="{ogtype}">
<meta property="og:title" content="{ogtitle}">
<meta property="og:description" content="{desc}">
<meta property="og:url" content="{url}">
<meta property="og:site_name" content="Claude Community Bhopal">
<meta property="og:locale" content="en_IN">
<meta property="og:image" content="{ogimg}">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="630">
<meta property="og:image:alt" content="{ogalt}">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:image" content="{ogimg}">
<script>document.documentElement.className='js'</script>
{jsonld}
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Caveat:wght@700&family=Fraunces:ital,opsz,wght@0,9..144,500;0,9..144,700;1,9..144,400&family=Inter:wght@400;500;600;700&family=Space+Mono:ital,wght@0,400;0,700;1,400&display=swap" rel="stylesheet">
<style>
{css}
</style>
</head>
<body>
'''


def head(**kw):
    kw.setdefault("css", CSS)
    return tpl(HEAD, **kw)


def nav(assets, blogroot, current=False, cta_url="https://luma.com/claude-z01j", cta_text="Build Day · Sep 20 ↗"):
    """assets: path from the page to blog/assets/ (e.g. "../assets/" from a post, "assets/" from the index)."""
    return tpl(NAV, site=SITE, assets=assets, blogroot=blogroot, blogcur='aria-current="page"' if current else 'aria-current="false"',
               cta_url=cta_url, cta_text=cta_text)


def foot(assets, blogroot):
    return tpl(FOOT, site=SITE, assets=assets, blogroot=blogroot)

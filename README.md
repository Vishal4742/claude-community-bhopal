# Claude Community · Bhopal

Website for the Claude community in Bhopal — meetups, workshops, and the Impact Lab civic AI hackathon.

**Next event:** Impact Lab · Sun, Aug 23 · [Register on Luma](https://luma.com/claude-af61)

## Structure

- `index.html` — the whole site: markup, styles, and scripts in one file, no build step
- `assets/` — photos, icons, and the social share card, committed to the repo so a clone deploys as-is

Everything is hand-rolled. The rough borders are SVG turbulence filters, the mascots are inline SVG (animated with GSAP, the only dependency, loaded from a CDN with a pinned version and integrity hash), and the rest is plain HTML, CSS, and JavaScript. The page works with JavaScript disabled.

## Run it

Open `index.html` in a browser. That's the whole setup.

## Deploy

Live at **https://claude-community-bhopal.netlify.app** (Netlify project `claude-community-bhopal`).

Netlify builds straight from GitHub. The repo is the whole site — `index.html`, `assets/`, and `netlify.toml` (publish `.`, no build step) — so every push to `main` deploys on its own. To ship an update, commit and push:

```
git add -A && git commit -m "…" && git push
```

If the site ever moves to a custom domain, update the absolute URLs in `<head>` (canonical, `og:url`, `og:image`, `twitter:image`) and in the JSON-LD block.

## Update checklist for the next event

Dates and event names live in several places. When announcing a new event, update them together:

- [ ] `<title>` + `meta description` + `og:description` (head)
- [ ] JSON-LD `Event` block (head) — name, dates, Luma URL; update or remove once the event is over
- [ ] Hero badge (`.badge`)
- [ ] Ticker text (each phrase appears twice — the track is duplicated for the loop)
- [ ] `#detail` — kicker, intro copy, agenda cards, challenge chips
- [ ] FAQ answers
- [ ] `#join` — heading, event card, Luma link
- [ ] `#past` — move the finished event into the timeline, bump the stats
- [ ] `assets/og-card.jpg` — regenerate the share card with the new date

# Claude Community · Bhopal

Website for the Claude community in Bhopal — meetups, workshops, and the Impact Lab civic AI hackathon.

**Next event:** Impact Lab · Sun, Aug 23 · [Register on Luma](https://luma.com/claude-af61)

## Structure

- `index.html` — the whole site: markup, styles, and scripts in one file, no build step
- `assets/` — photos, icons, and the social share card (kept out of this repo on purpose; they live in the local working folder and on Netlify)

Everything is hand-rolled. The rough borders are SVG turbulence filters, the mascots are inline SVG (animated with GSAP, the only dependency, loaded from a CDN with a pinned version and integrity hash), and the rest is plain HTML, CSS, and JavaScript. The page works with JavaScript disabled.

## Run it

Open `index.html` in a browser. That's the whole setup.

## Deploy

Live at **https://claude-community-bhopal.netlify.app** (Netlify project `claude-community-bhopal`).

The repo has no `assets/` folder, so a bare clone is not deployable on its own. To ship an update, build a clean deploy folder from the git export plus the local `assets/`, then push it to Netlify:

```
git archive main | tar -x -C /tmp/deploy
cp -r assets /tmp/deploy/
netlify deploy --prod --dir /tmp/deploy
```

Never run `netlify deploy --dir .` from the working folder — Netlify uploads everything in the directory it's given, including files that should stay local.

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

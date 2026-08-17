# Claude Community · Bhopal

Website for the Claude community in Bhopal — meetups, workshops, and the Impact Lab civic AI hackathon.

**Next event:** Impact Lab · Sun, Aug 23 · [Register on Luma](https://luma.com/claude-af61)

## Structure

- `index.html` — the whole site: markup, styles, and scripts in one file, no build step
- `assets/` — photos, icons, and the social share card

Everything is hand-rolled. The rough borders are SVG turbulence filters, the mascots are inline SVG (animated with GSAP, the only dependency, loaded from a CDN with a pinned version and integrity hash), and the rest is plain HTML, CSS, and JavaScript. The page works with JavaScript disabled.

## Run it

Open `index.html` in a browser. That's the whole setup.

## Deploy

Any static host works. For GitHub Pages: Settings → Pages → deploy from `main`, root folder. After the site has a live URL, finish the two TODOs in `<head>`:

1. Make `og:image` / `twitter:image` absolute URLs (`https://<domain>/assets/og-card.jpg`) — social scrapers can't resolve relative paths.
2. Add `<link rel="canonical">` and `og:url` with the live URL.

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

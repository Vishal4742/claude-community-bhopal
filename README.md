# Claude Community · Bhopal

Website for the Claude community in Bhopal — meetups, workshops, and the Impact Lab civic AI hackathon.

**Next up:** Claude Code Workshop · Wed, Sep 2 · [Luma](https://luma.com/claude-hj87)
Then: Claude Conversation · Sat, Sep 12 · [Luma](https://luma.com/claude-6khk) and Claude Impact Lab · Sun, Sep 13 · [Luma](https://luma.com/claude-r61u)

## Structure

- `index.html` — the whole site: markup, styles, and scripts in one file, no build step
- `assets/` — photos, icons, and the social share card, committed to the repo so a clone deploys as-is

Everything is hand-rolled. The rough borders are SVG turbulence filters, the mascots are inline SVG (animated with GSAP, loaded from a CDN with a pinned version and integrity hash; the Tally popup embed is the only other external script), and the rest is plain HTML, CSS, and JavaScript. The page works with JavaScript disabled.

## Run it

Open `index.html` in a browser. That's the whole setup.

## Deploy

Live at **https://claude-community-bhopal.netlify.app** (Netlify project `claude-community-bhopal`).

Netlify builds straight from GitHub. The repo is the whole site — `index.html`, `assets/`, and `netlify.toml` (publish `.`, no build step) — so every push to `main` deploys on its own. To ship an update, commit and push:

```
git add -A && git commit -m "…" && git push
```

If the site ever moves to a custom domain, update the absolute URLs in `<head>` (canonical, `og:url`, `og:image`, `twitter:image`) and in the JSON-LD block.

## Tally forms for the "pick your role" section

The three role cards (Community Partner, Speaker / Mentor, Volunteer) are meant to open Tally forms. `tally/create_forms.py` builds them from code so they can be recreated or tweaked in one go:

```
python3 tally/create_forms.py --dry-run          # writes tally/payloads/*.json, creates nothing
TALLY_API_KEY=tly-… python3 tally/create_forms.py   # creates the 3 forms (PUBLISHED) and patches index.html
```

The API key comes from Tally → Settings → [API keys](https://tally.so/settings/api-keys); it is read from the environment and never stored. After a run, `tally/forms.created.json` holds the form ids/URLs and each role button on the page opens its form in a popup (`data-tally-open`) with a plain `https://tally.so/r/<id>` link as the no-JS fallback. Rerun `python3 tally/create_forms.py --patch-only tally/forms.created.json` to re-wire the page without creating new forms.

Alternative without a key: the Tally MCP server (`https://api.tally.so/mcp`) is registered for this project in Claude Code — run `/mcp`, authorize Tally, and Claude can create or edit the forms directly.

## Update checklist for the next event

Dates and event names live in several places. When announcing a new event, update them together:

- [ ] `<title>` + `meta description` + `og:description` (head)
- [ ] JSON-LD `Event` block (head) — name, dates, Luma URL; update or remove once the event is over
- [ ] Hero: the "Next up" line (`.hero-next`), the "Reserve a free seat" Luma link, and the proof line (`.hero-proof`)
- [ ] Ticker text (each phrase appears twice — the track is duplicated for the loop)
- [ ] `#upcoming` (the `#impact-lab` section) — event cards, the big question, the weekend-format card, the "flagship" recap card, chips
- [ ] FAQ answers
- [ ] `#past` — move the finished event into the timeline, bump the stats
- [ ] `assets/og-card.jpg` — regenerate the share card with the new date

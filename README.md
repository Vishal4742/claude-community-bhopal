# Claude Community · Bhopal

Website for the Claude community in Bhopal — meetups, workshops, and the Impact Lab civic AI hackathon.

**Next up:** Claude Code Workshop · Wed, Sep 2 · [Luma](https://luma.com/claude-hj87)
Then: Claude Conversation · Sat, Sep 12 · [Luma](https://luma.com/claude-6khk) and Claude Impact Lab · Sun, Sep 13 · [Luma](https://luma.com/claude-r61u)

## Structure

- `index.html` — the whole site: markup, styles, and scripts in one file, no build step
- `assets/` — photos, icons, and the social share card, committed to the repo so a clone deploys as-is
- `blog/` — the blog. `blog/index.html` lists the posts; each post lives in its own folder (`blog/<slug>/index.html` plus its `media/`, `og.jpg`, `build.py` and data files). `blog/tools/` holds the shared build code, `blog/assets/` the logo and icons the blog needs, so the folder also works as a site of its own (see below)

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

## Blog

Posts are plain HTML pages that reuse the site's styles, so they work with JavaScript disabled and need no build step. To add one, copy the folder of an existing post, replace the content, and add a card to `blog/index.html`.

**First post:** [The night Bhopal trended on X](https://claude-community-bhopal.netlify.app/blog/fable-5-1-build-days-bhopal/) (`blog/fable-5-1-build-days-bhopal/`). It archives X's trend "Claude Fable 5.1 Build Days Launch Worldwide with Bhopal Spotlight" from September 11, 2026: every post in the trend is saved in `tweets.json` (author, time, text, media and engagement counts, refreshed every few hours) and the posts about Bhopal in `tweets.csv`, with images and avatars in `media/`.

The archive was made with `blog/tools/capture_x_trend.py`, which needs no X account and no third-party packages:

```
python3 blog/tools/capture_x_trend.py https://x.com/i/trending/<trend-id> --keyword bhopal --out blog/<slug>
```

It pages through the trend's "Top" and "Latest" post timelines with a guest token and writes `tweets.json`. If the file already exists, new posts are merged in and counts are refreshed; nothing is ever dropped. GraphQL query ids change every few weeks; the script refreshes them from the community-maintained TwitterInternalAPIDocument project and falls back to the ids that worked on September 11, 2026.

X's trend timelines leave out the replies under each post, and search needs an account, so `blog/tools/expand_x_archive.py` fills in what a logged-out visitor can still see: it opens the page of every saved post that has replies, collects the reply ids X renders there, fetches each one through X's syndication endpoint (the one embedded posts use), and merges the ones that belong to the conversation into `tweets.json`. Those posts carry `in_timelines: ["conversation"]`; X does not expose their repost or view counts. It runs after the capture in the workflow, a few dozen pages per run, so threads fill in over successive runs.

Each post folder has a `build.py` that turns `tweets.json` into `index.html` (plus `tweets.csv`), fetching images and avatars into `media/` on first use. The shared page chrome, tweet cards and stylesheet live in `blog/tools/blogkit.py` and `blog/tools/blog.css`:

```
python3 blog/fable-5-1-build-days-bhopal/build.py
python3 blog/tools/build_index.py          # the post list; add new posts to POSTS in that file
```

### Automatic refresh

`.github/workflows/refresh-blog.yml` runs every 10 minutes: each run starts the next one 10 minutes after it began (GitHub's cron trigger never fired for this repo, so it is only a backup). Run it on demand from the Actions tab or with `gh workflow run refresh-blog.yml`. It fetches new posts and rebuilds the post, then commits to `main` as `github-actions[bot]` when new posts arrived, or every 3 hours so the engagement counts on the page stay fresh; Netlify deploys each push to both projects. When nothing changed, it commits nothing.

To pause the loop, disable the workflow (`gh workflow disable refresh-blog.yml`, or the Actions tab); to resume, enable it and run it once (`gh workflow enable refresh-blog.yml && gh workflow run refresh-blog.yml`). Runs share a concurrency group, so a manual run never overlaps with the loop. Pillow is installed in the job so images are resized; without it the scripts still run and just copy files as they are.

To stop the refreshes for good, disable the workflow in the Actions tab (or delete the workflow file). To point it at another trend, change the trend id and `--keyword` in the workflow and add a matching post folder with its own `build.py`.

### The blog as its own project

`blog/` is self-contained: it carries its own `assets/`, `netlify.toml`, and `404.html`, and its links back to the main site are absolute. So the same folder can be published as a second Netlify project at its own URL, fed by the same repo and the same refresh commits. Live at **https://claude-bhopal-blog.netlify.app** (Netlify project `claude-bhopal-blog`, base directory `blog`).

To recreate it: in Netlify, add a project from the GitHub repo, set the base directory to `blog`, leave the build command empty (the folder's own `netlify.toml` publishes it). Or from the CLI, logged in as the team owner:

```
netlify api createSiteInTeam --data '{"account_slug":"vishal4742","body":{"name":"claude-bhopal-blog","repo":{"provider":"github","repo_path":"Vishal4742/claude-community-bhopal","repo_url":"https://github.com/Vishal4742/claude-community-bhopal","repo_branch":"main","base":"blog","dir":"blog","cmd":"","installation_id":60811761,"public_repo":true}}}'
```

The pages keep the main site as their canonical URL, so search engines treat the standalone copy as a mirror.

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

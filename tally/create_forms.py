#!/usr/bin/env python3
"""Create the three "pick your role" Tally forms and wire them into index.html.

    TALLY_API_KEY=tly-xxxx python3 tally/create_forms.py            # create + patch index.html
    python3 tally/create_forms.py --dry-run                          # only write tally/payloads/*.json
    python3 tally/create_forms.py --patch-only tally/forms.created.json   # re-patch index.html from a saved result

Get a key at https://tally.so/settings/api-keys (Settings > API keys). The key is read from the
TALLY_API_KEY environment variable and never written to disk.
"""
import json, os, re, sys, uuid, urllib.request, urllib.error
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
INDEX = ROOT / "index.html"
OUT = ROOT / "tally"
NS = uuid.UUID("7c1f7a3e-3d1e-4f0c-9b2a-claudebhopal".replace("claudebhopal", "0c1a0de0b0a1"))

EVENTS = ["Claude Code Workshop · Wed, Sep 2", "Claude Conversation · Sat, Sep 12",
          "Claude Impact Lab · Sun, Sep 13", "Future events"]

# ---------------------------------------------------------------- block builders
def _u(form, *parts):
    return str(uuid.uuid5(NS, form + "|" + "|".join(parts)))

class Form:
    def __init__(self, key, title, intro):
        self.key, self.blocks = key, []
        self.blocks.append({"uuid": _u(key, "form-title"), "type": "FORM_TITLE",
                            "groupUuid": _u(key, "form-title-g"), "groupType": "TEXT",
                            "payload": {"title": title, "html": title}})
        self.text(intro)

    def text(self, html):
        self.blocks.append({"uuid": _u(self.key, "text", html), "type": "TEXT",
                            "groupUuid": _u(self.key, "text-g", html), "groupType": "TEXT",
                            "payload": {"html": html}})

    def _title(self, label):
        self.blocks.append({"uuid": _u(self.key, "q", label), "type": "TITLE",
                            "groupUuid": _u(self.key, "q-g", label), "groupType": "QUESTION",
                            "payload": {"html": label}})

    def _input(self, label, type_, required, placeholder, extra=None):
        self._title(label)
        payload = {"isRequired": required, "placeholder": placeholder}
        if extra: payload.update(extra)
        self.blocks.append({"uuid": _u(self.key, "in", label), "type": type_,
                            "groupUuid": _u(self.key, "in-g", label), "groupType": type_, "payload": payload})

    def short(self, label, required=False, placeholder=""):  self._input(label, "INPUT_TEXT", required, placeholder)
    def email(self, label="Email", required=True):           self._input(label, "INPUT_EMAIL", required, "you@example.com")
    def phone(self, label="Phone / WhatsApp", required=False):
        self._input(label, "INPUT_PHONE_NUMBER", required, "+91", {"internationalFormat": True, "defaultCountryCode": "IN"})
    def link(self, label, required=False, placeholder="https://"): self._input(label, "INPUT_LINK", required, placeholder)
    def long(self, label, required=False, placeholder=""):   self._input(label, "TEXTAREA", required, placeholder)

    def _options(self, label, options, type_, group_type, required, other=False, multiple=False):
        self._title(label)
        g = _u(self.key, "opt-g", label)
        n = len(options) + (1 if other else 0)
        for i, text in enumerate(options + (["Other"] if other else [])):
            payload = {"index": i, "isFirst": i == 0, "isLast": i == n - 1, "text": text, "isRequired": required}
            if other and i == n - 1: payload["isOtherOption"] = True
            if other: payload["hasOtherOption"] = True
            if multiple and type_ == "DROPDOWN_OPTION": payload["allowMultiple"] = True
            self.blocks.append({"uuid": _u(self.key, "opt", label, text), "type": type_,
                                "groupUuid": g, "groupType": group_type, "payload": payload})

    def choice(self, label, options, required=True, other=False):
        self._options(label, options, "MULTIPLE_CHOICE_OPTION", "MULTIPLE_CHOICE", required, other)
    def checkboxes(self, label, options, required=False, other=False):
        self._options(label, options, "CHECKBOX", "CHECKBOXES", required, other)
    def dropdown(self, label, options, required=False):
        self._options(label, options, "DROPDOWN_OPTION", "DROPDOWN", required)

# ---------------------------------------------------------------- the four forms
def build_forms():
    forms = {}

    f = Form("partner", "Community Partner · Claude Community Bhopal",
             "Student club, developer community, college or incubator? Let's co-host, cross-promote and bring "
             "your members to the Impact Lab.")
    f.short("Community / club / organisation", True, "e.g. AIML Club OCT")
    f.short("Your name & role", True, "Name, role")
    f.email()
    f.phone()
    f.link("Community link (website, Instagram, Telegram…)")
    f.choice("What kind of community is it?",
             ["Student club", "Developer community", "College / university", "Incubator / accelerator",
              "Co-working space"], other=True)
    f.dropdown("Roughly how many members?", ["Under 50", "50 – 200", "200 – 1,000", "1,000+"])
    f.checkboxes("How would you like to collaborate?",
                 ["Co-host a workshop", "Provide a venue", "Cross-promote events",
                  "Bring members to the Impact Lab", "Mentors from your community"], other=True)
    f.long("Anything else?", placeholder="Ideas, dates, constraints…")
    forms["partner"] = f

    f = Form("speaker", "Speaker / Mentor · Claude Community Bhopal",
             "Give a lightning talk, run a deep-dive session, or mentor and judge teams at the Impact Lab. "
             "Keep it practical — the room is builders.")
    f.short("Your name", True, "Full name")
    f.email()
    f.phone()
    f.link("LinkedIn or X profile", True)
    f.short("Organisation & role", False, "Company, role")
    f.checkboxes("I'd like to…",
                 ["Give a lightning talk (10 min)", "Run a deep-dive session (45–60 min)",
                  "Mentor teams at the Impact Lab", "Judge at the Impact Lab"], required=True)
    f.short("Talk / session title", False, "Working title is fine")
    f.long("Short abstract", False, "What will people learn or be able to do afterwards?")
    f.checkboxes("Topics", ["Claude Code", "Model Context Protocol (MCP)", "Agents & tool use",
                            "Prompting & evals", "Building products on the Claude API",
                            "AI for civic & startup problems"], other=True)
    f.checkboxes("Preferred event", EVENTS)
    f.choice("Spoken at a meetup before?", ["Yes, many times", "A few times", "This would be my first"])
    f.link("Link to a past talk or demo (optional)")
    forms["speaker"] = f

    f = Form("volunteer", "Volunteer · Claude Community Bhopal",
             "Be the heartbeat of the event — check-in, stage ops, photos, content, and making people feel welcome. "
             "Volunteers get a crew badge, food, and first pick at the next event.")
    f.short("Your name", True, "Full name")
    f.email()
    f.phone(required=True)
    f.short("College / organisation", False, "e.g. OCT, RGPV, a startup…")
    f.checkboxes("Where can you help?",
                 ["Check-in & registration", "Stage & AV ops", "Photo / video capture",
                  "Social media & content", "Venue setup & logistics", "Welcoming & attendee support",
                  "Design (posters, slides)"], required=True)
    f.checkboxes("When are you available?", EVENTS, required=True)
    f.choice("Volunteered at events before?", ["Yes", "No, first time"])
    f.long("Why do you want to volunteer?", placeholder="A line or two is enough")
    f.dropdown("T-shirt size", ["S", "M", "L", "XL", "XXL"])
    forms["volunteer"] = f
    return forms

SETTINGS = {
    "language": "en",
    "hasProgressBar": False,
    "hasSelfEmailNotifications": True,
    "styles": {"theme": "CUSTOM",
               "color": {"background": "#F0EBE1", "text": "#191714", "accent": "#D97757",
                         "buttonBackground": "#191714", "buttonText": "#F0EBE1"},
               "direction": "ltr"},
}

# ---------------------------------------------------------------- API
def create(key, payload):
    """POST /forms; on a 400 progressively drop optional settings so a strict validator can't block us."""
    attempts = [payload,
                {**payload, "settings": {k: v for k, v in payload["settings"].items() if k != "styles"}},
                {k: v for k, v in payload.items() if k != "settings"}]
    last = None
    for i, body in enumerate(attempts):
        req = urllib.request.Request("https://api.tally.so/forms", data=json.dumps(body).encode(),
                                     headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json",
                                              "Accept": "application/json", "User-Agent": "claude-bhopal-forms/1.0"},
                                     method="POST")
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                return json.loads(r.read()), i
        except urllib.error.HTTPError as e:
            last = f"{e.code} {e.read().decode()[:400]}"
            if e.code != 400: raise SystemExit(f"Tally API error: {last}")
            print(f"  400 on attempt {i + 1}: {last}\n  retrying with fewer settings…")
        except urllib.error.URLError as e:
            raise SystemExit(f"Could not reach api.tally.so: {e.reason}")
    raise SystemExit(f"Tally rejected the form even without settings: {last}")

# ---------------------------------------------------------------- page wiring
BUTTONS = {  # role key -> the exact anchor currently on the page
    "partner":   ("Collaborate", "Community Partner"),
    "speaker":   ("Submit CFP", "Speaker / Mentor"),
    "volunteer": ("Join Crew", "Volunteer"),
}
EMBED = '<script async src="https://tally.so/widgets/embed.js"></script>'

def patch_index(created):
    html = INDEX.read_text(encoding="utf-8")
    for role, (label, name) in BUTTONS.items():
        fid = created[role]["id"]
        if f'data-tally-open="{fid}"' in html:
            continue  # already wired
        pat = re.compile(r'<a href="[^"]*"( target="_blank" rel="noopener")? class="btn btn-dark" style="width:100%;justify-content:center"(?: data-tally-[a-z-]+="[^"]*")*><span>'
                         + re.escape(label) + r'</span> <span class="arrow">↗</span></a>')
        new = (f'<a href="https://tally.so/r/{fid}" target="_blank" rel="noopener" class="btn btn-dark" '
               f'style="width:100%;justify-content:center" data-tally-open="{fid}" data-tally-layout="modal" '
               f'data-tally-emoji-text="✻" data-tally-emoji-animation="wave" data-tally-auto-close="3000">'
               f'<span>{label}</span> <span class="arrow">↗</span></a>')
        html, n = pat.subn(new, html)
        if n != 1: raise SystemExit(f"could not find the {name} button ({label}) in index.html (matches: {n})")
    if EMBED not in html:
        html = html.replace("</body>", EMBED + "\n</body>", 1)
    INDEX.write_text(html, encoding="utf-8")
    print(f"index.html patched: {len(BUTTONS)} role buttons open Tally popups (with plain-link fallback)")

# ---------------------------------------------------------------- main
def main(argv):
    forms = build_forms()
    payloads = {k: {"status": "PUBLISHED", "blocks": f.blocks, "settings": SETTINGS} for k, f in forms.items()}
    (OUT / "payloads").mkdir(parents=True, exist_ok=True)
    for k, p in payloads.items():
        (OUT / "payloads" / f"{k}.json").write_text(json.dumps(p, indent=2, ensure_ascii=False), encoding="utf-8")
    print("payloads written to tally/payloads/ (" + ", ".join(f"{k}: {len(p['blocks'])} blocks" for k, p in payloads.items()) + ")")

    if "--patch-only" in argv:
        i = argv.index("--patch-only")
        created = json.loads(Path(argv[i + 1] if len(argv) > i + 1 else OUT / "forms.created.json").read_text())
        return patch_index(created)
    if "--dry-run" in argv:
        return
    key = os.environ.get("TALLY_API_KEY", "").strip()
    if not key.startswith("tly-"):
        raise SystemExit("Set TALLY_API_KEY (starts with tly-) — create one at https://tally.so/settings/api-keys — "
                         "or run with --dry-run.")
    created = {}
    for k, p in payloads.items():
        res, attempt = create(key, p)
        created[k] = {"id": res["id"], "name": res["name"], "url": f"https://tally.so/r/{res['id']}",
                      "edit": f"https://tally.so/forms/{res['id']}/edit", "settings_attempt": attempt}
        print(f"  created {k:9s} {created[k]['url']}   (edit: {created[k]['edit']})")
    (OUT / "forms.created.json").write_text(json.dumps(created, indent=2), encoding="utf-8")
    patch_index(created)

if __name__ == "__main__":
    main(sys.argv[1:])

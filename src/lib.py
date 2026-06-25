#!/usr/bin/env python3
"""Shared paths, config, and heuristic seed classifier for the screenshot pilot.

Categories / colors / hotkeys / keywords and the sensitive-term packs come from
`config.json` (user-customizable). DEFAULT_CONFIG below is the built-in fallback
used when config.json is missing or invalid, so the pipeline always runs."""
import os, re, json

HOME  = os.path.expanduser("~")
CONFIG_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "config.json")

def _path_override(key):
    """Read paths.<key> from config.json early (before the full config load). Lets each
    user point the output wherever they want without editing code; falls back to the
    defaults below. See config.example.json for the `paths` section."""
    try:
        with open(CONFIG_PATH, encoding="utf-8") as f:
            v = (json.load(f).get("paths") or {}).get(key)
        return os.path.expanduser(v) if v else None
    except Exception:
        return None

# Output locations. Override in config.json → "paths": {"vault": "...", "previews": "..."}.
VAULT = _path_override("vault")    or f"{HOME}/Documents/Obsidian Vault"
SS    = f"{VAULT}/Screenshots"
PREV  = _path_override("previews") or f"{SS}/previews"

def paths(batch):
    y = str(batch)
    work = f"{SS}/pilot/{y}"
    return {
        "year": y, "work": work,
        "export":    f"{work}/export.json",
        "fulltext":  f"{work}/fulltext.txt",
        "delete":    f"{work}/delete.txt",
        "thumbs":    f"{PREV}/pilot-{y}-thumbs",
        "thumbs_rel":f"pilot-{y}-thumbs",
        "recat":     f"{PREV}/pilot-{y}-recategorize.html",
        "decisions": f"{HOME}/Downloads/pilot-{y}-decisions.json",
        "archive":   f"{SS}/text-extract/{y}-pilot",
        "seed":      f"{work}/seed.json",   # LLM triage: uuid -> {cat, conf, why}
        "dups":      f"{work}/dups.json",   # dedup: redundant uuid -> representative uuid
        "sensitive": f"{work}/sensitive.json",  # privacy pre-filter: uuid -> {cat:PROTECT, why}
        "seed_dl":   f"{HOME}/Downloads/pilot-{y}-seed.json",  # cold-start: ~15 hand-labeled samples
        "notes":     f"{work}/notes.json",   # marker: kept items integrated into summary/*.md
    }

# ---------------------------------------------------------------------------
# Batch addressing — a batch is any group of screenshots to process together.
# `batch_unit` (config) is the default; the CLI can override per run. Every
# downstream script just receives the resulting label and namespaces paths()
# by it — only export.py turns (mode, selector) into an actual Photos query.
# ---------------------------------------------------------------------------
MODES = ("year", "date-range", "album", "folder")
_MODE_ALIAS = {"range": "date-range"}

def _slug(s):
    out = re.sub(r"[^\w.-]+", "-", str(s).strip()).strip("-").lower()
    return out or "batch"

def batch_label(mode, sel):
    """Filesystem-safe namespace label for a batch (used everywhere as <batch>)."""
    if mode == "date-range":
        return f"{_slug(sel[0])}_{_slug(sel[1])}"
    return _slug(sel[0])

def parse_batch(args, default_unit="year"):
    """(mode, selector_list, label) from CLI args, or None if insufficient.
    First arg may be a mode keyword (year/date-range/album/folder, or alias 'range');
    otherwise default_unit is assumed so `export.py 2023` keeps working unchanged."""
    if not args:
        return None
    first = _MODE_ALIAS.get(args[0], args[0])
    if first in MODES:
        mode, sel = first, list(args[1:])
    else:
        mode = _MODE_ALIAS.get(default_unit, default_unit)
        if mode not in MODES:
            mode = "year"
        sel = list(args)
    need = 2 if mode == "date-range" else 1
    if len(sel) < need:
        return None
    return mode, sel, batch_label(mode, sel)

# ---------------------------------------------------------------------------
# Config (user-customizable). Edit config.json, not this file.
# ---------------------------------------------------------------------------
DEFAULT_CONFIG = {
    "output": {"format": "markdown", "folder": f"{SS}/summary", "obsidian_links": True},
    "languages": ["en", "ko"],
    "batch_unit": "year",
    "privacy": {"no_cloud": False, "redact_pii": True},
    "categories": [
        {"name":"AI","hotkey":"a","color":"#7aa2ff","role":"note","desc":"LLMs, prompting, agents, AI/ML concepts, model news","keywords":["llm","prompt","agentic","claude","anthropic","openai","gpt"," rag","뉴럴","에이전트","인공지능","모델 학습"]},
        {"name":"PM","hotkey":"p","color":"#ffb454","role":"note","desc":"product-management craft, frameworks, interviews, planning(기획), metrics, discovery","keywords":["product manager"," pm ","north star","northstar","roadmap","prd","스프린트","프로덕트","지표"]},
        {"name":"DESIGN","hotkey":"d","color":"#5fd3a3","role":"note","desc":"UX/UI, design systems, Figma, usability, visual/interaction design","keywords":["figma","usability","hci"," ux ","피그마","인터페이스","ux research"]},
        {"name":"MINDSET","hotkey":"m","color":"#c08af7","role":"note","desc":"psychology, philosophy, self-development, reflections, money/time/discipline, quotes, life frameworks","keywords":["mindset","discipline","philosophy","habit","self-development","성과","노력","언러닝","마인드"]},
        {"name":"CAREER","hotkey":"c","color":"#4fd0e0","role":"note","desc":"job search, resume, hiring, networking, job interviews, work-craft, leadership/management","keywords":["hiring","resume","recruiter","linkedin","cover letter","이력서","채용","네트워킹","면접","커리어"]},
        {"name":"EVENTS","hotkey":"e","color":"#f78ad0","role":"note","desc":"webinars, conferences, panels, RSVPs, meetups, dated happenings","keywords":["panel discussion","webinar","conference","rsvp","세미나","컨퍼런스"]},
        {"name":"READING","hotkey":"b","color":"#d0b35f","role":"note","desc":"book titles, reading lists, book covers, \"to read\"","keywords":["book by","bestseller","goodreads","책 추천"]},
        {"name":"PLACES","hotkey":"l","color":"#8fbf7a","role":"places","desc":"travel, restaurants, maps, venue/location info worth keeping","keywords":[]},
        {"name":"PROTECT","hotkey":"s","color":"#ff5d5d","role":"protect","desc":"sensitive identity/financial docs (passport, visa, IDs, payment, account #) — NEVER delete","keywords":[]},
        {"name":"REVIEW","hotkey":"v","color":"#9aa3b2","role":"review","desc":"genuinely can't tell; needs human eyes","keywords":[]},
        {"name":"DELETE","hotkey":"x","color":"#6b7280","role":"delete","desc":"junk with no durable reusable content","keywords":[]},
    ],
    "sensitive_packs": {
        "en": ["passport","social security","ssn","routing number","account number","iban","password","verification code"," otp","cvv","card number","boarding pass","uscis","h-1b","h1b","credit line"],
        "ko": ["여권","주민등록","비자","결제","송금 ","계좌","카드번호","비밀번호","인증번호"],
    },
}

def _validate(cfg):
    """Return human-readable problems with a user config (empty list = OK)."""
    probs = []
    cats = cfg.get("categories", [])
    hk = [c.get("hotkey") for c in cats if c.get("hotkey")]
    dup = sorted({h for h in hk if hk.count(h) > 1})
    if dup: probs.append(f"duplicate hotkeys {dup}")
    roles = {c.get("role") for c in cats}
    missing = [r for r in ("note", "protect", "delete", "review") if r not in roles]
    if missing: probs.append(f"missing reserved role(s) {missing}")
    return probs

def load_config():
    """Read config.json; fall back to DEFAULT_CONFIG if missing/invalid/empty.
    Validates a user config and prints any problems to stderr (fail loud, but proceed)."""
    try:
        with open(CONFIG_PATH, encoding="utf-8") as f:
            cfg = json.load(f)
        if not cfg.get("categories"):
            return DEFAULT_CONFIG
        probs = _validate(cfg)
        if probs:
            import sys
            print("⚠ config.json: " + "; ".join(probs), file=sys.stderr)
        return cfg
    except Exception:
        return DEFAULT_CONFIG

CONFIG     = load_config()
CATEGORIES = CONFIG["categories"]
CATS       = [c["name"] for c in CATEGORIES]   # order preserved

def _role_name(role, fallback):
    return next((c["name"] for c in CATEGORIES if c.get("role") == role), fallback)

# reserved-role category names (resolved from config so categories can be renamed)
PROTECT = _role_name("protect", "PROTECT")
DELETE  = _role_name("delete",  "DELETE")
REVIEW  = _role_name("review",  "REVIEW")

# sensitive lexicon: English base pack is always on; add packs for configured languages
_packs = CONFIG.get("sensitive_packs", DEFAULT_CONFIG["sensitive_packs"])
_langs = CONFIG.get("languages", ["en"])
_SENS  = list(_packs.get("en", []))
for _lg in _langs:
    if _lg != "en":
        _SENS += _packs.get(_lg, [])

# note-category keywords drive the heuristic topic seed (order = config order)
_TOPIC = {c["name"]: c["keywords"] for c in CATEGORIES
          if c.get("role") == "note" and c.get("keywords")}

_JUNK = re.compile(r"mail\.naver|gmail\.naver|page break|home video my network|add your reply|"
                   r"enter a prompt here|summarize this file|i'm looking for\.\.\.", re.I)

# ---------------------------------------------------------------------------
# Privacy: sensitive-content detection (lexicon + always-on structural PII).
# Used by classify() AND by sensitive.py's pre-filter. Strong patterns route to
# PROTECT alone; weak signals (email / long digit run) only count when corroborated
# so we don't flag every newsletter that happens to show an email address.
# ---------------------------------------------------------------------------
_STRONG_PII = [
    ("ssn",  re.compile(r"\b\d{3}-\d{2}-\d{4}\b")),                       # US SSN
    ("iban", re.compile(r"\b[A-Z]{2}\d{2}(?:[ ]?[A-Z0-9]{4}){2,7}\b")),  # IBAN
    ("card", re.compile(r"\b(?:\d[ -]?){15,16}\b")),                     # 15-16 digit (Luhn-checked)
]
_WEAK_PII = [
    ("email",  re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.-]{2,}\b")),
    ("digits", re.compile(r"\b\d{9,}\b")),                               # account/passport-length run
]

def _luhn(s):
    d = [int(c) for c in s if c.isdigit()]
    if not (13 <= len(d) <= 19): return False
    chk = 0
    for i, n in enumerate(reversed(d)):
        if i % 2: n = n * 2 - 9 if n * 2 > 9 else n * 2
        chk += n
    return chk % 10 == 0

def sensitive_match(text):
    """Return a short reason string if text looks sensitive (-> PROTECT), else None."""
    t = text or ""; low = t.lower()
    for s in _SENS:
        if s in low: return f"term:{s.strip()}"
    for name, rx in _STRONG_PII:
        m = rx.search(t)
        if m and (name != "card" or _luhn(m.group())): return name
    weak = [name for name, rx in _WEAK_PII if rx.search(t)]
    if len(weak) >= 2: return "+".join(weak)
    return None

def redact(text):
    """Mask structural PII (emails, card/SSN/IBAN/long-digit runs) in text.
    Applied to OCR snippets before they go to the cloud when privacy.redact_pii is on."""
    t = text or ""
    for _, rx in _STRONG_PII + _WEAK_PII:
        t = rx.sub("▒", t)
    return t

# Apple Vision OCR language codes. Onboarding may write an explicit `ocr_languages`
# list into config (from the installed packs); otherwise we map `languages` here.
_OCR_MAP = {"en":"en-US","fr":"fr-FR","it":"it-IT","de":"de-DE","es":"es-ES",
            "pt":"pt-BR","zh":"zh-Hans","yue":"yue-Hant","ko":"ko-KR","ja":"ja-JP",
            "ru":"ru-RU","uk":"uk-UA","th":"th-TH","vi":"vi-VT","ar":"ar-SA",
            "tr":"tr-TR","id":"id-ID","cs":"cs-CZ","da":"da-DK","nl":"nl-NL",
            "no":"no-NO","ms":"ms-MY","pl":"pl-PL","ro":"ro-RO","sv":"sv-SE"}

def ocr_langs():
    """Vision recognition languages for export.py, in config order (en first if listed)."""
    explicit = CONFIG.get("ocr_languages")
    if explicit: return list(explicit)
    out = [_OCR_MAP.get(l, l) for l in CONFIG.get("languages", ["en"])]
    return out or ["en-US"]

def classify(x):
    """Lightweight seed only — the human re-sorts in the recategorize HTML."""
    o = x.get("ocr") or ""; low = o.lower(); wc = x.get("wc", 0)
    if sensitive_match(o):           return PROTECT
    if wc < 8 or _JUNK.search(o):    return DELETE
    for t, kws in _TOPIC.items():
        if any(k in low for k in kws): return t
    return REVIEW

"""
Shared page-decoration glyph library and smart genre/mood-aware selection.

Used by all three places that draw page decorations -- the HTML
live-preview renderer, the ReportLab PDF exporter, and the DOCX exporter --
so the option list and the "auto-pick a fitting style" logic live in one
place instead of drifting out of sync across three copies.

Decorations are rendered as a single ornamental rule in the top and bottom
margins (a glyph flanked by short line rules, like a classic book
fleuron/dinkus), not four isolated corner marks -- this reads as an actual
margin decoration rather than four unrelated dots, and it's simple enough
to render identically (same literal text) in a browser, a PDF, and Word.

All glyphs are plain Unicode (Dingbats / Miscellaneous Symbols / box-
drawing ranges), not emoji or an icon font: they render identically
everywhere without any font/CDN dependency. Every glyph here has been
checked against DejaVu Sans's cmap, which is what the PDF path falls back
to when no other Unicode-capable font is available on the system.
"""

import re
import zlib

VS15 = "\ufe0e"  # variation selector: force text (not emoji/color) presentation


def _txt(ch: str) -> str:
    """Force plain monochrome text presentation for a glyph. Several
    Unicode symbols used here (anchor, crossed swords, heart, lightning,
    snowflake, skull...) are registered emoji with *default* color
    presentation in most browsers/OSes -- rendered from a color emoji
    font that completely ignores any CSS `color` rule. Without this, a
    themed gold accent color could silently render as a plain black (or
    platform-default-colored) emoji glyph instead, which is exactly what
    "colored emoji that don't match the theme" looks like. Harmless to
    apply to glyphs that were already text-only."""
    return ch + VS15


# Each style is (primary glyph, secondary glyph). Primary appears in the
# top-margin rule, secondary in the bottom-margin rule -- distinct but
# clearly related, like a matched pair of endpapers.
DECORATION_SETS = {
    "sparkle":     (_txt("\u2726"), _txt("\u2727")),  # ✦ ✧
    "botanical":   (_txt("\u2766"), _txt("\u2767")),  # ❦ ❧
    "star":        (_txt("\u273a"), _txt("\u2736")),  # ✺ ✶
    "diamond":     (_txt("\u25c6"), _txt("\u25c7")),  # ◆ ◇
    "flourish":    (_txt("\u269c"), _txt("\u274b")),  # ⚜ ❋
    "celebration": (_txt("\u2739"), _txt("\u2738")),  # ✹ ✸
    "elegant":     (_txt("\u2743"), _txt("\u2749")),  # ❃ ❉
    "vintage":     (_txt("\u2619"), _txt("\u2767")),  # ☙ ❧
    "celestial":   (_txt("\u2606"), _txt("\u2736")),  # ☆ ✶
    "moonlit":     (_txt("\u263e"), _txt("\u263d")),  # ☾ ☽
    "nature":      (_txt("\u2740"), _txt("\u273f")),  # ❀ ✿
    "leaf":        (_txt("\u2618"), _txt("\u2766")),  # ☘ ❦
    "snow":        (_txt("\u2746"), _txt("\u2745")),  # ❆ ❅
    "holiday":     (_txt("\u2744"), _txt("\u2605")),  # ❄ ★
    "spooky":      (_txt("\u263e"), _txt("\u2620")),  # ☾ ☠
    "gothic":      (_txt("\u2020"), _txt("\u2767")),  # † ❧
    "nautical":    (_txt("\u2693"), _txt("\u2606")),  # ⚓ ☆
    "adventure":   (_txt("\u2694"), _txt("\u2726")),  # ⚔ ✦
    "royal":       (_txt("\u265b"), _txt("\u265a")),  # ♛ ♚
    "hearts":      (_txt("\u2665"), _txt("\u2740")),  # ♥ ❀
    "academic":    (_txt("\u2767"), _txt("\u2766")),  # ❧ ❦
    "minimal":     (_txt("\u2022"), _txt("\u00b7")),  # • ·
    "geometric":   (_txt("\u25c6"), _txt("\u25b2")),  # ◆ ▲
    "cosmic":      (_txt("\u2737"), _txt("\u2726")),  # ✷ ✦
    "music":       (_txt("\u266a"), _txt("\u266b")),  # ♪ ♫
    "crown":       (_txt("\u2654"), _txt("\u2655")),  # ♔ ♕
    "lightning":   (_txt("\u26a1"), _txt("\u26a1")),  # ⚡
    "infinity":    (_txt("\u221e"), _txt("\u221e")),  # ∞
    "clover":      (_txt("\u2741"), _txt("\u2741")),  # ❁
    "gem":         (_txt("\u2662"), _txt("\u2662")),  # ♢
    "scroll":      (_txt("\u274a"), _txt("\u274a")),  # ❊
    "dots":        (_txt("\u2058"), _txt("\u2059")),  # ⁘ ⁙
    "asterism":    (_txt("\u2042"), _txt("\u2042")),  # ⁂
    "target":      (_txt("\u25ce"), _txt("\u25ce")),  # ◎
    "cross":       (_txt("\u271a"), _txt("\u271a")),  # ✚
}

# One-line description for each set, shown in UI pickers.
DECORATION_LABELS = {
    "sparkle": "Sparkle", "botanical": "Botanical", "star": "Star",
    "diamond": "Diamond", "flourish": "Flourish", "celebration": "Celebration",
    "elegant": "Elegant", "vintage": "Vintage", "celestial": "Celestial",
    "moonlit": "Moonlit", "nature": "Nature", "leaf": "Autumn Leaf",
    "snow": "Snowflake", "holiday": "Holiday", "spooky": "Spooky",
    "gothic": "Gothic", "nautical": "Nautical", "adventure": "Adventure",
    "royal": "Royal", "hearts": "Hearts", "academic": "Academic",
    "minimal": "Minimal Dot", "geometric": "Geometric", "cosmic": "Cosmic",
    "music": "Music", "crown": "Crown", "lightning": "Lightning",
    "infinity": "Infinity", "clover": "Clover", "gem": "Gem",
    "scroll": "Scroll", "dots": "Dots", "asterism": "Asterism",
    "target": "Target", "cross": "Cross",
}

DEFAULT_SET = "sparkle"

RULE_CHAR = "\u2500"   # ─
RULE_REPEAT = 3        # how many rule chars flank the glyph on each side


def margin_text(glyph: str) -> str:
    """The literal ornamental-rule string drawn in the top/bottom margins:
    a short line, the glyph, a short line. Built once here and reused
    as-is by the HTML, PDF, and DOCX renderers so all three produce
    exactly the same motif instead of three separate approximations."""
    rule = RULE_CHAR * RULE_REPEAT
    return f"{rule}  {glyph}  {rule}"


# Mood keywords scanned against the document's title + opening content.
# Checked first because they catch genre/occasion signals neither a
# document-type classifier nor the active theme can (a birthday invite and
# a wedding program might use the same theme, but call for very different
# decoration).
MOOD_KEYWORDS = {
    "spooky":      ["halloween", "spooky", "ghost", "haunted", "witch", "vampire",
                     "zombie", "skeleton", "graveyard", "monster", "creepy"],
    "holiday":     ["christmas", "xmas", "santa", "snowman", "holiday season",
                     "advent", "yuletide"],
    "snow":        ["snow", "winter", "blizzard", "frost", "frozen", "icy"],
    "hearts":      ["love", "valentine", "romance", "romantic", "wedding",
                     "engagement", "anniversary", "sweetheart"],
    "celebration": ["birthday", "party", "celebration", "congratulations",
                     "festival", "graduation", "cheers"],
    "nautical":    ["ship", "sailor", "ocean", "sea voyage", "pirate", "nautical",
                     "harbor", "captain", "voyage"],
    "adventure":   ["quest", "adventure", "dungeon", "sword", "battle", "warrior",
                     "knight", "dragon"],
    "royal":       ["king", "queen", "royal", "kingdom", "throne", "crown",
                     "prince", "princess", "monarch"],
    "celestial":   ["galaxy", "cosmos", "astronomy", "planet", "universe",
                     "nebula", "starlight", "constellation"],
    "moonlit":     ["moon", "moonlight", "midnight", "lunar", "night sky"],
    "nature":      ["garden", "flower", "forest", "botanical", "blossom",
                     "bloom", "wildflower"],
    "leaf":        ["autumn", "fall harvest", "maple", "foliage"],
    "music":       ["music", "song", "concert", "band", "melody", "orchestra",
                     "playlist", "symphony"],
    "gothic":      ["gothic", "dark academia", "noir", "detective", "mystery"],
    "crown":       ["coronation", "dynasty", "empire", "reign"],
    "lightning":   ["storm", "thunder", "lightning", "electric"],
    "gem":         ["jewel", "gem", "diamond ring", "treasure"],
    "academic":    ["thesis", "curriculum", "syllabus", "dissertation",
                     "coursework", "semester", "lecture notes"],
}

# Fallback keyed by the document's already-computed project type (see
# app.structure.structure_engine) -- checked after mood keywords, since
# project type is a coarser signal, but before the theme-based fallback,
# since it's specific to this document rather than a whole theme family.
PROJECT_TYPE_DEFAULTS = {
    "Story Bible": "flourish",
    "Worldbuilding Document": "vintage",
    "Research Notes": "academic",
    "Knowledge Base": "minimal",
    "Study Notes": "academic",
    "Project Plan": "geometric",
    "Debate Prep": "minimal",
    "Competition Planning": "star",
}

# Fallback keyed by the active theme -- checked last, before the generic
# default, because a theme is *always* chosen (unlike project type, which
# is UNKNOWN for most ordinary documents), so this is what actually
# determines the common case and is why decoration used to look like it
# only ever picked one style: everything with no mood match and an
# UNKNOWN project type fell straight through to the same hardcoded
# default regardless of what the document actually looked like.
THEME_DEFAULTS = {
    "academic": "academic", "research": "infinity", "museum": "scroll",
    "magazine": "celebration", "codex": "vintage", "corporate": "geometric",
    "detective": "gothic", "cyberpunk": "lightning",
}

# Deterministic but varied final fallback, used only when nothing above
# matched at all (no mood, no classified project type, unrecognized
# theme) -- picking the same single style every time in that situation is
# exactly the "always sparkle" complaint; a small curated, broadly-
# tasteful subset keeps results looking intentional rather than random.
_FALLBACK_POOL = ["sparkle", "diamond", "minimal", "geometric", "dots", "asterism"]


def resolve_style(decoration_style: str, doc=None, theme: str = None) -> str:
    """Resolve a requested style name to an actual DECORATION_SETS key.
    "auto"/"smart" (or anything unrecognized) triggers content-aware
    selection when a document is available; otherwise falls back to the
    default set."""
    if decoration_style and decoration_style in DECORATION_SETS:
        return decoration_style
    if doc is not None:
        return pick_smart_style(doc, theme)
    return DEFAULT_SET


def pick_smart_style(doc, theme: str = None) -> str:
    """Pick a decoration set based on the document's actual content, in
    order of specificity: mood keywords in the title/opening text, then
    the document's own classified project type, then the active theme
    (always present, so this is what most ordinary documents land on),
    then a small varied fallback pool keyed off the document itself so
    otherwise-unmatched documents don't all collapse onto one style."""
    try:
        title = getattr(doc, "title", "") or ""
        blocks = getattr(doc, "all_blocks", []) or []
        sample = " ".join(b.content for b in blocks[:40] if getattr(b, "content", None))
        text = f"{title} {sample}".lower()
    except Exception:
        title, text = "", ""

    best_mood, best_score = None, 0
    for mood, words in MOOD_KEYWORDS.items():
        score = sum(len(re.findall(r"\b" + re.escape(w) + r"\b", text)) for w in words)
        if score > best_score:
            best_mood, best_score = mood, score
    if best_mood:
        return best_mood

    project_type = getattr(doc, "project_type", None)
    project_type_value = getattr(project_type, "value", project_type)
    if project_type_value in PROJECT_TYPE_DEFAULTS:
        return PROJECT_TYPE_DEFAULTS[project_type_value]

    if theme and theme in THEME_DEFAULTS:
        return THEME_DEFAULTS[theme]

    seed = title or text or theme or "ias"
    return _FALLBACK_POOL[zlib.crc32(seed.encode("utf-8")) % len(_FALLBACK_POOL)]


# ─────────────────────────────────────────────────────────────────────────
# Margin doodles: small glyphs scattered in the margins next to whichever
# passage actually mentions that concept -- a bird glyph next to a
# paragraph about a bird, an anchor next to one about a ship -- rather
# than a single repeated motif. Deliberately a much broader, more literal
# vocabulary than the mood/style keywords above, and deliberately
# many-keywords-to-one-glyph so unrelated documents don't all reach for
# the same handful of symbols.
#
# Some concepts (animals, rockets, inkwells...) have no monochrome Unicode
# symbol at all -- only full-color emoji pictographs with no text-
# presentation fallback, which is exactly the "colored emoji that don't
# match the theme" problem this whole module exists to avoid. Those
# instead get a small hand-drawn line-art SVG icon (stroke/fill:
# currentColor, so it inherits the theme accent color like everything
# else here) rather than reaching for a pictograph.
# ─────────────────────────────────────────────────────────────────────────

# Inner markup for a 0-0-24-24 viewBox SVG, stroke-based line art unless a
# path sets its own fill. Deliberately simple (circles, short paths) --
# legible at doodle size (16-40px) rather than detailed illustration.
SVG_ICONS = {
    "raven": (
        '<ellipse cx="11" cy="14" rx="6" ry="5"/>'
        '<circle cx="16" cy="9" r="3"/>'
        '<path d="M19 8 L22.5 7 L19.3 9.6 Z" fill="currentColor" stroke="none"/>'
        '<path d="M6 16 Q2 18 3 21 Q6 19 8 17"/>'
        '<circle cx="17" cy="8.2" r="0.6" fill="currentColor" stroke="none"/>'
    ),
    "owl": (
        '<ellipse cx="12" cy="14" rx="7" ry="7"/>'
        '<path d="M6 9 L4 4 M18 9 L20 4"/>'
        '<circle cx="9" cy="12" r="2.2"/><circle cx="15" cy="12" r="2.2"/>'
        '<circle cx="9" cy="12" r="0.6" fill="currentColor" stroke="none"/>'
        '<circle cx="15" cy="12" r="0.6" fill="currentColor" stroke="none"/>'
        '<path d="M11 15 L12 17 L13 15 Z" fill="currentColor" stroke="none"/>'
    ),
    "fox": (
        '<path d="M6 6 L8 11 L4 11 Z"/><path d="M18 6 L16 11 L20 11 Z"/>'
        '<path d="M4 11 Q4 18 12 20 Q20 18 20 11 Q16 9 12 12 Q8 9 4 11 Z"/>'
        '<path d="M9 11 L12 15 L15 11"/>'
    ),
    "cat": (
        '<path d="M6 8 L7 4 L9 8"/><path d="M18 8 L17 4 L15 8"/>'
        '<circle cx="12" cy="12" r="6"/>'
        '<circle cx="9.5" cy="11" r="0.7" fill="currentColor" stroke="none"/>'
        '<circle cx="14.5" cy="11" r="0.7" fill="currentColor" stroke="none"/>'
        '<path d="M11 14 L12 15 L13 14 M12 15 L12 13.5 M9 13 L11 14 M15 13 L13 14"/>'
    ),
    "ship": (
        '<path d="M4 15 L20 15 L18 20 L6 20 Z"/><path d="M12 15 L12 3"/>'
        '<path d="M12 4 L18 9 L12 9 Z"/><path d="M12 9 L7 12 L12 12 Z"/>'
    ),
    "rocket": (
        '<path d="M12 2 Q17 7 16 14 L8 14 Q7 7 12 2 Z"/>'
        '<circle cx="12" cy="9" r="1.6"/>'
        '<path d="M8 14 L5 19 L8 18 Z"/><path d="M16 14 L19 19 L16 18 Z"/>'
        '<path d="M10 18 L9 22 M14 18 L15 22"/>'
    ),
    "planet": (
        '<circle cx="12" cy="12" r="4.5"/>'
        '<ellipse cx="12" cy="12" rx="10" ry="2.6" transform="rotate(-18 12 12)"/>'
    ),
    "inkpot": (
        '<path d="M6 14 L18 14 L17 20 L7 20 Z"/><path d="M6 14 Q12 11 18 14"/>'
        '<path d="M15 14 L20 3"/><path d="M20 3 Q18 6 16 8 Q18 6 15 7"/>'
    ),
    "book": (
        '<path d="M12 5 Q8 3 3 4 L3 18 Q8 17 12 19 Q16 17 21 18 L21 4 Q16 3 12 5 Z"/>'
        '<path d="M12 5 L12 19"/>'
    ),
    "key": (
        '<circle cx="7" cy="7" r="4"/>'
        '<path d="M10 10 L20 20 M17 17 L19 15 M15 19 L17 17"/>'
    ),
    "compass": (
        '<circle cx="12" cy="12" r="9"/>'
        '<path d="M12 12 L15 7 L12 12 L9 17 Z" fill="currentColor" stroke="none"/>'
        '<circle cx="12" cy="12" r="1" fill="currentColor" stroke="none"/>'
    ),
}

_DOODLE_RAW_VOCAB = {
    # ── weather / sky ──
    "\u2600": ["sun", "sunlight", "sunrise", "sunset", "sunny", "daylight"],
    "\u2601": ["cloud", "clouds", "cloudy", "overcast"],
    "\u2602": ["rain", "umbrella", "raining", "rainy", "drizzle"],
    "\u2614": ["downpour", "rainstorm", "monsoon"],
    "\u2603": ["snowman", "snowball"],
    "\u2604": ["comet", "meteor", "asteroid"],
    "\u2746": ["frost", "ice", "icy", "frozen", "glacier"],
    "\u2744": ["winter", "cold", "chilly", "snow", "snowy", "snowing"],
    "\u26a1": ["lightning", "thunder", "storm", "electric", "electricity", "shock"],
    # ── sky / celestial ──
    "\u2606": ["star", "stars", "starlight", "starry"],
    "\u263e": ["moon", "moonlight", "lunar", "crescent"],
    "planet:svg": ["planet", "orbit", "orbiting", "solar system", "saturn", "rings"],
    "rocket:svg": ["rocket", "spaceship", "spacecraft", "launch", "launched",
                    "liftoff", "astronaut"],
    "compass:svg": ["compass", "navigation", "navigate", "bearing", "due north"],
    # ── nature ──
    "\u2740": ["flower", "bloom", "blooming", "garden", "blossomed", "petals"],
    "\u273f": ["blossom", "petal", "wildflower"],
    "\u2618": ["tree", "trees", "forest", "woods", "leaf", "leaves", "branch", "grove"],
    "\u2740\u2740": [],  # unused placeholder kept out of loop below
    # ── animals ──
    "raven:svg": ["raven", "crow", "crows", "rook", "ravens"],
    "owl:svg": ["owl", "owls", "hoot", "hooting"],
    "fox:svg": ["fox", "foxes", "vixen"],
    "cat:svg": ["cat", "cats", "kitten", "feline", "tabby"],
    # ── sea / travel ──
    "\u2693": ["ship", "sail", "sailing", "sailor", "harbor", "voyage", "anchor",
                "boat", "vessel", "captain"],
    "ship:svg": ["schooner", "galleon", "frigate", "shipwreck", "seafaring"],
    "\u2708": ["airplane", "flight", "flying", "airport", "pilot", "aircraft"],
    "\u2691": ["flag", "banner", "pennant"],
    "key:svg": ["key", "keys", "locked", "unlocked", "keyhole"],
    # ── writing / study ──
    "\u270f": ["pencil", "sketch", "sketched", "drawing", "drew", "draw"],
    "\u2712": ["pen", "signature", "signed", "wrote", "writing", "journal"],
    "inkpot:svg": ["ink", "inkwell", "quill", "parchment", "manuscript"],
    "book:svg": ["book", "books", "chapter", "novel", "diary", "library",
                  "bookshelf", "textbook", "notebook"],
    "\u2709": ["letter", "mail", "envelope", "postcard"],
    "\u260e": ["phone", "telephone", "call", "calling", "rang", "ringing"],
    # ── food / drink ──
    "\u2615": ["coffee", "tea", "brew", "brewed", "brewing", "cafe", "espresso",
                "kettle", "bread", "loaf", "baked", "baking", "dough", "oven",
                "recipe", "kitchen", "cooking", "simmer", "spice", "herbs",
                "seasoning", "ingredient", "ingredients"],
    # ── tools / science ──
    "\u2692": ["hammer", "tool", "tools", "forge", "forged", "workshop", "anvil"],
    "\u2699": ["gear", "machine", "machinery", "mechanism", "engine", "clockwork"],
    "\u2696": ["justice", "law", "lawyer", "trial", "courtroom", "verdict", "judge"],
    "\u2697": ["potion", "alchemy", "elixir", "brewed", "brewing", "concoction"],
    "\u269b": ["atom", "science", "physics", "scientist", "laboratory", "experiment"],
    "\u2695": ["medicine", "medical", "doctor", "physician", "healer", "cure"],
    "\u2702": ["scissors", "cut", "cutting", "trim", "snip"],
    # ── conflict / fantasy ──
    "\u2694": ["sword", "blade", "swords", "duel", "dueled", "sabre"],
    "\u2654": ["king", "throne", "monarch", "royal"],
    "\u2655": ["queen", "empress"],
    "\u265f": ["pawn", "foot soldier", "conscript"],
    "\u265e": ["knight", "cavalry", "steed"],
    "\u265d": ["bishop", "cleric", "priest"],
    "\u265c": ["castle", "fortress", "stronghold", "keep", "rampart"],
    "\u2620": ["skull", "danger", "poison", "poisoned", "deadly", "peril"],
    # ── emotion ──
    "\u2665": ["love", "heart", "romance", "beloved", "sweetheart", "kiss", "kissed"],
    "\u262e": ["peace", "peaceful", "truce"],
    "\u262f": ["balance", "harmony", "equilibrium"],
    # ── music / games ──
    "\u266a": ["music", "song", "melody", "sing", "singing", "tune", "hum", "humming"],
    "\u2660": ["cards", "gambling", "poker", "casino", "wager", "bet"],
    "\u2680": ["dice", "die", "gamble", "roll", "rolled", "wagered"],
    # ── money / business ──
    "\u2666": ["wealth", "treasure", "riches", "fortune", "gold coin", "coins"],
    "$": ["money", "dollar", "dollars", "revenue", "profit", "budget", "funding"],
    "\u20ac": ["euro", "euros"],
    "\u00a3": ["pound sterling", "sterling"],
    # ── astrology / zodiac (fantasy, mysticism) ──
    "\u2648": ["aries", "ram"], "\u2649": ["taurus"], "\u264a": ["gemini", "twins"],
    "\u264b": ["cancer zodiac", "crab"], "\u264c": ["leo", "lion"],
    "\u264d": ["virgo"], "\u264e": ["libra", "scales of fate"],
    "\u264f": ["scorpio", "scorpion"], "\u2650": ["sagittarius", "archer"],
    "\u2651": ["capricorn"], "\u2652": ["aquarius"], "\u2653": ["pisces"],
    "\u267b": [],  # placeholder guard, ignored below
}
del _DOODLE_RAW_VOCAB["\u2740\u2740"]
del _DOODLE_RAW_VOCAB["\u267b"]


def _resolve_doodle_value(key: str):
    """A vocab key is either a plain Unicode glyph, or "name:svg" pointing
    at SVG_ICONS. Returns ("glyph", text) or ("svg", inner_markup)."""
    if key.endswith(":svg"):
        name = key[:-4]
        return "svg", SVG_ICONS[name]
    return "glyph", _txt(key)


DOODLE_VOCAB = {}
for _key, _words in _DOODLE_RAW_VOCAB.items():
    _kind, _value = _resolve_doodle_value(_key)
    for _w in _words:
        DOODLE_VOCAB[_w] = (_kind, _value)

# Words that are frequently part of ordinary phrasing rather than a real
# reference to the concept (a document saying "we love this approach"
# isn't about romance) are deliberately left out above rather than
# filtered here -- keeping the list itself conservative is more reliable
# than trying to disambiguate usage.

# ── Density presets ──────────────────────────────────────────────────────
# How populated the margins should feel, from a bare top/bottom ornament
# only up to "deliberately cluttered" with several doodles per paragraph.
# min_gap: minimum blocks between two doodle placements.
# max_doodles: hard cap on the whole document.
# per_block: how many distinct doodles a single block can carry (only the
# highest density allows more than one, since that's what "clutter" means).
DENSITY_PRESETS = {
    "none":   {"min_gap": 0,  "max_doodles": 0,  "per_block": 0},
    "low":    {"min_gap": 3,  "max_doodles": 8,  "per_block": 1},
    "medium": {"min_gap": 1,  "max_doodles": 18, "per_block": 1},
    "high":   {"min_gap": 0,  "max_doodles": 40, "per_block": 3},
}
DEFAULT_DENSITY = "low"

_DOODLE_SIZE_RANGE = (22, 36)     # px -- bold enough to actually notice
_DOODLE_ROTATE_RANGE = (-12, 12)  # degrees


def find_doodles(doc, density: str = DEFAULT_DENSITY) -> dict:
    """Scan a document's paragraph/heading/quote blocks for concrete,
    doodle-worthy words and assign each match a margin glyph or icon,
    deterministic size and rotation (for an organic, hand-annotated feel
    that's still stable across re-renders), and alternating left/right
    side. Returns {block_index: [{"kind":..., "value":..., "side":...,
    "size":..., "rotate":...}, ...]} -- a list per block since higher
    density levels allow more than one doodle per block.
    `density` controls how populated the result is: "none" disables
    doodles entirely (still leaves the top/bottom ornament and border
    alone -- those are controlled separately), "low" is sparse and
    restrained (the default), "medium" fills in more of the document, and
    "high" deliberately allows a cluttered, multiple-doodles-per-paragraph
    feel for documents that want it."""
    preset = DENSITY_PRESETS.get(density, DENSITY_PRESETS[DEFAULT_DENSITY])
    if preset["max_doodles"] <= 0:
        return {}

    blocks = getattr(doc, "all_blocks", None) or []
    out = {}
    last_doodle_index = -preset["min_gap"]
    side = "left"
    count = 0
    prev_value = None

    for i, block in enumerate(blocks):
        if count >= preset["max_doodles"]:
            break
        block_type = getattr(getattr(block, "type", None), "value", None)
        if block_type not in ("paragraph", "heading", "quote"):
            continue
        content = getattr(block, "content", "") or ""
        if not content or i - last_doodle_index < preset["min_gap"]:
            continue

        text = content.lower()
        # Find every matching word's earliest position in this block, not
        # just the first one hit while walking the vocabulary dict --
        # otherwise an incidental early match (e.g. "captain's quarters")
        # could win out over the sentence's actual subject (e.g. "sword")
        # purely because of dict insertion order.
        candidates = []
        for word, (kind, value) in DOODLE_VOCAB.items():
            m = re.search(r"\b" + re.escape(word) + r"\b", text)
            if m:
                candidates.append((m.start(), word, kind, value))
        if not candidates:
            continue
        candidates.sort(key=lambda c: c[0])

        block_doodles = []
        for _, word, kind, value in candidates:
            if len(block_doodles) >= preset["per_block"]:
                break
            if value == prev_value and len(candidates) > len(block_doodles) + 1:
                # Variety reads as more considered than accuracy-to-the-
                # letter here, but only skip a repeat if another distinct
                # candidate is actually available.
                continue
            digest = zlib.crc32(f"{word}{i}{len(block_doodles)}".encode("utf-8"))
            size = _DOODLE_SIZE_RANGE[0] + digest % (_DOODLE_SIZE_RANGE[1] - _DOODLE_SIZE_RANGE[0] + 1)
            rotate = _DOODLE_ROTATE_RANGE[0] + (digest >> 8) % (_DOODLE_ROTATE_RANGE[1] - _DOODLE_ROTATE_RANGE[0] + 1)
            block_doodles.append({"kind": kind, "value": value, "side": side,
                                   "size": size, "rotate": rotate})
            side = "right" if side == "left" else "left"
            prev_value = value

        if not block_doodles:
            continue
        out[i] = block_doodles
        last_doodle_index = i
        count += len(block_doodles)

    return out

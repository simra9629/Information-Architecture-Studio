"""
Margin-doodle icon library and detection.

Plain Unicode symbols (see decorations.py) cover the top/bottom margin
ornament fine -- a handful of repeated glyphs -- but can't cover a real
"doodle in the margins" vocabulary: there's no classic, non-emoji Unicode
glyph for an owl, a rocket, an ink pot, or a car. This module instead
bundles a curated subset of the Lucide icon set (ISC license, see
doodle_icons/LICENSE) -- simple single-color line icons designed to be
recolored via `stroke="currentColor"`, which is exactly the "doodle"
aesthetic wanted here and lets every icon inherit the document's theme
color automatically when inlined as SVG.

Lucide doesn't have every specific animal (no owl, fox, wolf, or raven,
for instance) -- where a word has no close dedicated icon, it's mapped to
the nearest reasonable stand-in (an owl mention gets the generic `bird`
icon) rather than left undetected.
"""

import os
import re
import zlib

_ICONS_DIR = os.path.join(os.path.dirname(__file__), "doodle_icons")
_icon_cache = {}


def available_icons() -> set:
    return {f[:-4] for f in os.listdir(_ICONS_DIR) if f.endswith(".svg")}


def load_icon_svg(name: str) -> str:
    """Return the raw SVG markup for a bundled icon, cached after first
    read. Returns "" for an unknown name rather than raising, so a typo'd
    or since-removed vocabulary entry degrades to "no doodle" instead of
    crashing a render."""
    if name in _icon_cache:
        return _icon_cache[name]
    path = os.path.join(_ICONS_DIR, f"{name}.svg")
    try:
        with open(path, "r", encoding="utf-8") as f:
            svg = f.read()
    except OSError:
        svg = ""
    _icon_cache[name] = svg
    return svg


# keyword -> icon name. Many words per icon; every icon used here exists
# in doodle_icons/. Where Lucide has no dedicated icon for a specific
# animal/object, the nearest reasonable stand-in is used instead of
# leaving the word undetected (owl/raven/crow/hawk -> bird; wolf/fox ->
# no close stand-in exists, left unmapped rather than misleading).
ICON_VOCAB = {
    # Birds & small creatures
    "bird": "bird", "birds": "bird", "owl": "bird", "raven": "bird",
    "crow": "bird", "hawk": "bird", "eagle": "bird", "sparrow": "bird",
    "nest": "bird", "feathers": "feather",
    "cat": "cat", "cats": "cat", "kitten": "cat", "feline": "cat",
    "dog": "dog", "dogs": "dog", "puppy": "dog", "hound": "dog",
    "rabbit": "rabbit", "bunny": "rabbit", "hare": "rabbit",
    "squirrel": "squirrel",
    "turtle": "turtle", "tortoise": "turtle",
    "snail": "snail",
    "shrimp": "shrimp",
    "fish": "fish", "fishing": "fish", "trout": "fish", "salmon": "fish",
    "bug": "bug", "insect": "bug", "beetle": "bug", "spider": "bug",
    "paw": "paw-print", "paws": "paw-print", "pawprint": "paw-print",

    # Sky, weather, celestial
    "sun": "sun", "sunlight": "sun", "sunny": "sun", "sunrise": "sun", "sunset": "sun",
    "moon": "moon", "moonlight": "moon", "lunar": "moon", "crescent": "moon-star",
    "star": "star", "stars": "star", "starlight": "star", "starry": "star",
    "sparkle": "sparkle", "sparkling": "sparkles", "glitter": "sparkles",
    "cloud": "cloud", "clouds": "cloud", "cloudy": "cloud", "overcast": "cloud",
    "rain": "cloud-rain", "raining": "cloud-rain", "rainy": "cloud-rain", "drizzle": "cloud-rain",
    "umbrella": "umbrella",
    "snow": "cloud-snow", "snowy": "cloud-snow", "snowing": "cloud-snow", "blizzard": "snowflake",
    "frost": "snowflake", "frozen": "snowflake", "ice": "snowflake", "icy": "snowflake",
    "thunder": "cloud-lightning", "lightning": "cloud-lightning", "storm": "cloud-lightning",
    "rainbow": "rainbow",
    "earth": "earth", "world": "earth", "globe": "earth", "planet": "earth", "planets": "earth",
    "orbit": "orbit", "orbiting": "orbit", "galaxy": "orbit", "cosmos": "orbit",
    "telescope": "telescope", "astronomer": "telescope", "stargazing": "telescope",
    "satellite": "satellite",

    # Travel & vehicles
    "car": "car", "cars": "car", "drive": "car", "driving": "car", "road trip": "car",
    "ship": "ship", "sail": "sailboat", "sailing": "sailboat", "sailboat": "sailboat",
    "boat": "ship", "vessel": "ship", "captain": "ship", "voyage": "ship",
    "anchor": "anchor", "harbor": "anchor", "dock": "anchor", "port": "anchor",
    "rocket": "rocket", "spaceship": "rocket", "launch": "rocket", "astronaut": "rocket",
    "compass": "compass", "navigate": "compass", "navigation": "compass",
    "map": "map", "atlas": "map", "cartography": "map",
    "footprints": "footprints", "footsteps": "footprints", "trail": "footprints", "hike": "footprints",

    # Writing & stationery
    "pen": "pen", "ink": "pen", "inkwell": "pen", "quill": "feather",
    "pencil": "pencil", "sketch": "pencil", "sketched": "pencil", "draw": "pencil", "drawing": "pencil",
    "notebook": "notebook-pen", "journal": "notebook-pen", "diary": "notebook-pen",
    "book": "book", "books": "book", "novel": "book", "chapter": "book-open", "reading": "book-open",
    "scroll": "scroll", "parchment": "scroll", "manuscript": "scroll",
    "key": "key", "keys": "key", "unlock": "key", "lock": "key",
    "letter": "mail", "letters": "mail", "mail": "mail", "envelope": "mail", "postcard": "mail",
    "palette": "palette", "paint": "paintbrush", "painting": "paintbrush", "artist": "palette",

    # Food & drink
    "coffee": "coffee", "cafe": "coffee", "espresso": "coffee", "brew": "coffee", "brewing": "coffee",
    "tea": "coffee", "kettle": "coffee",
    "wine": "wine", "vineyard": "wine", "cellar": "wine",
    "soda": "cup-soda", "drink": "cup-soda", "beverage": "cup-soda",
    "apple": "apple", "orchard": "apple",
    "carrot": "carrot", "vegetable": "carrot", "vegetables": "carrot",
    "egg": "egg", "eggs": "egg",
    "wheat": "wheat", "grain": "wheat", "harvest": "wheat", "field": "wheat",
    "kitchen": "chef-hat", "cooking": "chef-hat", "chef": "chef-hat", "recipe": "chef-hat",
    "baking": "chef-hat", "bread": "chef-hat", "oven": "chef-hat", "dough": "chef-hat",
    "spice": "flame", "spices": "flame", "herbs": "leaf", "seasoning": "flame",

    # Fantasy & adventure
    "sword": "sword", "blade": "sword", "swords": "swords", "duel": "swords", "duels": "swords",
    "battle": "swords", "fight": "swords", "warrior": "sword", "knight": "shield",
    "shield": "shield", "armor": "shield", "defend": "shield", "guard": "shield",
    "crown": "crown", "throne": "crown", "royal": "crown", "monarch": "crown", "king": "crown",
    "queen": "crown", "kingdom": "castle", "castle": "castle", "fortress": "castle", "empire": "castle",
    "wand": "wand", "magic": "wand-sparkles", "spell": "wand-sparkles", "sorcerer": "wand-sparkles",
    "wizard": "wand-sparkles", "enchanted": "wand-sparkles", "potion": "flame",
    "flame": "flame", "fire": "flame", "burning": "flame", "torch": "flame", "blaze": "flame",
    "skull": "skull", "danger": "skull", "poison": "skull", "death": "skull", "deadly": "skull",
    "ghost": "ghost", "haunted": "ghost", "spirit": "ghost", "phantom": "ghost", "specter": "ghost",
    "drama": "drama", "theater": "drama", "tragedy": "drama", "play": "drama",
    "gem": "gem", "jewel": "gem", "treasure": "gem", "diamond": "diamond", "riches": "gem",
    "quest": "compass", "dungeon": "castle", "dragon": "flame",

    # Tools & work
    "hammer": "hammer", "hammering": "hammer", "build": "hammer", "builder": "hammer",
    "axe": "axe", "chop": "axe", "chopping": "axe", "woodcutter": "axe",
    "pickaxe": "pickaxe", "mine": "pickaxe", "mining": "pickaxe", "miner": "pickaxe",
    "shovel": "shovel", "dig": "shovel", "digging": "shovel", "garden tool": "shovel",
    "gear": "cog", "gears": "cog", "machine": "cog", "mechanism": "cog", "engine": "cog",

    # Time
    "clock": "clock", "time": "clock", "ticking": "clock",
    "hourglass": "hourglass", "sand timer": "hourglass",
    "watch": "watch", "wristwatch": "watch",
    "alarm": "alarm-clock", "wake": "alarm-clock",

    # Music
    "music": "music", "song": "music", "melody": "music", "sing": "music", "singing": "music",
    "tune": "music", "hum": "music", "humming": "music",
    "guitar": "guitar", "piano": "piano", "drum": "drum", "drums": "drum", "drumming": "drum",

    # Nature
    "tree": "tree-pine", "trees": "trees", "forest": "trees", "woods": "trees", "grove": "trees",
    "pine": "tree-pine", "oak": "tree-deciduous",
    "leaf": "leaf", "leaves": "leaf", "branch": "leaf",
    "flower": "flower", "flowers": "flower", "bloom": "flower", "blooming": "flower",
    "blossom": "flower-2", "petals": "flower-2", "garden": "flower",
    "mountain": "mountain", "mountains": "mountain", "peak": "mountain", "summit": "mountain",
    "snowy peak": "mountain-snow", "glacier": "mountain-snow",
    "wave": "waves-horizontal", "waves": "waves-horizontal", "ocean": "waves-horizontal",
    "sea": "waves-horizontal", "tide": "waves-horizontal", "shore": "shell",
    "shell": "shell", "beach": "shell", "seashell": "shell",

    # Emotion / occasion
    "heart": "heart", "love": "heart", "romance": "heart", "beloved": "heart",
    "sweetheart": "heart", "kiss": "heart", "kissed": "heart",
    "gift": "gift", "present": "gift", "wrapped": "gift", "birthday": "gift", "celebration": "gift",
    "flag": "flag", "banner": "flag",
    "tent": "tent", "camp": "tent", "camping": "tent", "campfire": "tent",
}

# Self-check: every icon name ICON_VOCAB points at must have a matching
# bundled SVG, or find_doodles() would silently degrade to "no doodle"
# for that keyword (load_icon_svg returns "" for an unknown name rather
# than raising) -- a typo here would be invisible without this check.
_missing_icons = set(ICON_VOCAB.values()) - available_icons()
if _missing_icons:
    import warnings
    warnings.warn(
        f"doodle_icons.ICON_VOCAB references icon file(s) with no matching "
        f"SVG in {_ICONS_DIR}: {sorted(_missing_icons)}. Affected keywords "
        f"will silently produce no doodle.",
        RuntimeWarning,
    )

_DENSITY_PRESETS = {
    0: {"max_doodles": 0,   "min_gap": 999, "max_per_block": 0},
    1: {"max_doodles": 10,  "min_gap": 3,   "max_per_block": 1},
    2: {"max_doodles": 30,  "min_gap": 1,   "max_per_block": 2},
    3: {"max_doodles": 80,  "min_gap": 0,   "max_per_block": 2},
    4: {"max_doodles": 250, "min_gap": 0,   "max_per_block": 3},
}
DEFAULT_DENSITY = 2

_SIZE_RANGE = (18, 58)      # px -- wide spread so doodles read as visibly varied, not samey
_ROTATE_RANGE = (-22, 22)   # degrees
_OPACITY_RANGE = (70, 92)   # percent, stored *100 for integer hashing


def _clamp_density(density) -> int:
    try:
        d = int(density)
    except (TypeError, ValueError):
        return DEFAULT_DENSITY
    return max(0, min(4, d))


def find_doodles(doc, density=DEFAULT_DENSITY) -> dict:
    """Scan a document's paragraph/heading/quote blocks for doodle-worthy
    words and assign each match an icon, deterministic size/rotation/
    opacity (stable across re-renders, varied enough to read as hand-
    placed), and side. Returns {block_index: [doodle, ...]} -- a list per
    block since higher density levels allow more than one doodle per
    block. `density` (0-4) controls how populated the result is: 0 turns
    doodles off entirely (the caller still gets the plain top/bottom
    margin ornament if decoration is otherwise on), 4 allows dense,
    multiple-per-paragraph placement for a deliberately cluttered look."""
    density = _clamp_density(density)
    preset = _DENSITY_PRESETS[density]
    if preset["max_doodles"] == 0:
        return {}

    blocks = getattr(doc, "all_blocks", None) or []
    out = {}
    last_doodle_index = -preset["min_gap"]
    side = "left"
    count = 0
    prev_icon = None

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
        candidates = []
        for word, icon in ICON_VOCAB.items():
            m = re.search(r"\b" + re.escape(word) + r"\b", text)
            if m:
                candidates.append((m.start(), word, icon))
        if not candidates:
            continue
        candidates.sort(key=lambda c: c[0])

        block_doodles = []
        used_icons_here = set()
        for _, word, icon in candidates:
            if len(block_doodles) >= preset["max_per_block"] or count >= preset["max_doodles"]:
                break
            if icon in used_icons_here or icon == prev_icon:
                continue
            digest = zlib.crc32(f"{word}{i}{len(block_doodles)}".encode("utf-8"))
            size = _SIZE_RANGE[0] + digest % (_SIZE_RANGE[1] - _SIZE_RANGE[0] + 1)
            rotate = _ROTATE_RANGE[0] + (digest >> 8) % (_ROTATE_RANGE[1] - _ROTATE_RANGE[0] + 1)
            opacity = _OPACITY_RANGE[0] + (digest >> 16) % (_OPACITY_RANGE[1] - _OPACITY_RANGE[0] + 1)
            block_doodles.append({
                "icon": icon, "side": side, "size": size,
                "rotate": rotate, "opacity": opacity / 100,
            })
            used_icons_here.add(icon)
            prev_icon = icon
            side = "right" if side == "left" else "left"
            count += 1

        if block_doodles:
            out[i] = block_doodles
            last_doodle_index = i

    return out

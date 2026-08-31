"""
Auto Designer engine — analyzes a document's actual content and generates
a bespoke visual design for it: a color palette, font pairing, capitalization
treatment, and targeted CSS, instead of picking from a fixed list of preset
themes.

This module is the only place that needs to know how genres, modifiers,
and food moods fit together. Adding a new genre, subgenre modifier, or food
mood never requires touching this file — see fiction/, nonfiction/,
modifiers/, and food/ for how those are registered.
"""

import re

from app.models.document import BlockType
from app.themes.auto_designer import palette as _palette
from app.themes.auto_designer import decor as _decor
from app.themes.auto_designer import labels as _labels
from app.themes.auto_designer import blending as _blending
from app.themes.auto_designer.seeding import seed_unit
from app.themes.auto_designer.fiction import FAMILIES as _FICTION
from app.themes.auto_designer.nonfiction import FAMILIES as _NONFICTION
from app.themes.auto_designer.schoolwork import FAMILIES as _SCHOOLWORK
from app.themes.auto_designer.food import MOODS as _FOOD_MOODS
from app.themes.auto_designer.modifiers import MODIFIERS as _MODIFIERS
from app.themes.auto_designer.modifiers._apply import apply_modifier, pick_modifier

_ALL_GENRES = {**_FICTION, **_NONFICTION, **_SCHOOLWORK}

# ── Atmosphere / dread signals ──────────────────────────────────────────
# Ghost stories and quiet horror often carry almost none of horror_gothic's
# explicit vocabulary (no "corpse," no "demon") — the dread lives in
# sensory/atmospheric phrasing instead. Scored separately and added
# directly to horror_gothic's score, so tone can be picked up even when
# the topic-word lexicon comes back empty.
_ATMOSPHERE_SIGNALS = [
    "the silence", "no one answered", "something moved", "she was alone",
    "he was alone", "flickered and died", "couldn't explain", "chill ran down",
    "goosebumps", "watched her", "watched him", "footsteps behind",
    "door creaked", "wouldn't stop staring", "empty house", "cold spot",
    "shadow shifted", "held her breath", "held his breath", "heart pounded",
    "corner of her eye", "corner of his eye", "never came back",
    "hair stood up", "something was wrong", "too quiet", "out of the dark",
    "didn't move", "wasn't alone", "went cold", "stopped breathing",
    "whispered her name", "whispered his name", "something behind",
]

# Recipes don't really have "genres" — the interesting signal is the
# character of the dish, not the fact that it's a recipe at all.
_FOOD_SIGNALS = ["recipe", "ingredients", "tablespoon", "teaspoon", "preheat",
                  "serves", "cook time", "prep time", "degrees", "the oven",
                  "simmer", "whisk", "marinate", "garnish", "season to taste",
                  "bring to a boil", "boil for", "combine", "chop the", "dice the",
                  "slice the", "roast", "grill", "blend", "pan-fry", "saute",
                  "sauté", "cup of", "cups of", "cook for", "until golden",
                  "let cool", "drizzle", "sprinkle", "toss", "knead", "fold in",
                  "cast iron", "skillet", "saucepan", "baking sheet", "batter",
                  "the dough", "the broth", "olive oil", "clove of garlic", "pinch of"]

_DEFAULT_FOOD_MOOD = {
    "hue": 60, "sat": 0.4, "energy": 0.22,
    "heading_font": "Fraunces", "body_font": "Source Sans 3", "mono_font": "DM Mono",
    "label_style": "small_caps", "decor": "rule_under",
}

_NEUTRAL_VARIANTS = [
    {"hue": 18, "sat": 0.42, "energy": 0.22,
     "heading_font": "Fraunces", "body_font": "Karla", "mono_font": "DM Mono",
     "label_style": "italic_label", "decor": "ornament_divider"},
    {"hue": 78, "sat": 0.4, "energy": 0.2,
     "heading_font": "Space Grotesk", "body_font": "Inter", "mono_font": "Roboto Mono",
     "label_style": "tracked_upper", "decor": "left_bar"},
    {"hue": 130, "sat": 0.38, "energy": 0.18,
     "heading_font": "Lora", "body_font": "Source Sans 3", "mono_font": "DM Mono",
     "label_style": "small_caps", "decor": "rule_under"},
    {"hue": 195, "sat": 0.5, "energy": 0.3,
     "heading_font": "IBM Plex Sans", "body_font": "IBM Plex Sans", "mono_font": "IBM Plex Mono",
     "label_style": "tracked_upper", "decor": "grid_lines"},
    {"hue": 255, "sat": 0.4, "energy": 0.24,
     "heading_font": "Playfair Display", "body_font": "Source Serif 4", "mono_font": "DM Mono",
     "label_style": "small_caps", "decor": "rule_under"},
    {"hue": 315, "sat": 0.4, "energy": 0.22,
     "heading_font": "Fredoka", "body_font": "Nunito", "mono_font": "DM Mono",
     "label_style": "pill", "decor": "soft_round"},
]


def _is_food_content(text: str) -> bool:
    word_count = max(len(text.split()), 1)
    mechanics_hits = sum(text.count(sig) for sig in _FOOD_SIGNALS)
    # Recipes described in menu-blurb style ("Vanilla Crème Brûlée. Fine
    # dining, refined...") often carry almost no cooking-mechanics verbs at
    # all — the food-mood vocabulary itself (chocolate, curry, birthday,
    # campfire, fine dining, ...) is corroborating evidence too. But two
    # incidental hits scattered across two *unrelated* moods is weak,
    # coincidental evidence (e.g. one horror-story word happens to overlap
    # with "cozy" and another with "fresh") — require the mood evidence to
    # either concentrate in one mood or be corroborated by a mechanics hit.
    best_single_mood_hits = 0
    total_mood_hits = 0
    for cfg in _FOOD_MOODS.values():
        this_mood_hits = sum(1 for sig in cfg["signals"] if text.count(sig))
        total_mood_hits += this_mood_hits
        best_single_mood_hits = max(best_single_mood_hits, this_mood_hits)

    coherent_mood_evidence = best_single_mood_hits >= 2 or (best_single_mood_hits >= 1 and mechanics_hits >= 1)
    hits = mechanics_hits + total_mood_hits
    if hits < 2 or not (mechanics_hits >= 2 or coherent_mood_evidence):
        # A single incidental match (e.g. "a cup of tea" in a non-food
        # story) should never be enough on its own, no matter how short
        # the document is and how much that inflates the normalized ratio.
        return False
    return (hits / max(word_count / 300.0, 0.3)) >= 2.2


def _pick_food_mood(text: str) -> tuple:
    length_factor = max(len(text.split()) / 300.0, 0.3)
    scores = {k: round(sum(text.count(s) for s in cfg["signals"]) / length_factor, 2)
              for k, cfg in _FOOD_MOODS.items()}
    ranked = sorted(scores.items(), key=lambda kv: kv[1], reverse=True)
    best_key, best_score = ranked[0]
    runner_key, runner_score = ranked[1] if len(ranked) > 1 else (None, 0)

    if best_score < 0.8:
        return "home_cooking", _DEFAULT_FOOD_MOOD, scores
    if runner_score >= best_score * 0.6 and runner_score >= 0.5:
        label, blended = _blending.blend_configs(best_key, _FOOD_MOODS[best_key], best_score,
                                                   runner_key, _FOOD_MOODS[runner_key], runner_score)
        return label, blended, scores
    return best_key, _FOOD_MOODS[best_key], scores


def _analyze_genre(all_text: str) -> tuple:
    """
    Score the document's text against every registered genre family,
    normalized by document length so long documents don't just accumulate
    incidental hits, and require the winner to clear the runner-up by a
    real margin — otherwise a handful of generic words shouldn't be enough
    to commit to a strong mood.

    horror_gothic also picks up an atmosphere/dread score independent of
    its topic-word lexicon (see _ATMOSPHERE_SIGNALS).

    When two genres score close together, they're blended into a real
    hybrid (e.g. "fantasy_epic + dark_mystery") rather than one winning
    outright.
    """
    text = all_text.lower()
    word_count = max(len(text.split()), 1)
    # Normalizing by raw word count with no ceiling meant long-form documents
    # (a full novel or play) diluted even a strong, consistent genre signal
    # into "neutral" -- capping the factor keeps the intended dampening for
    # short/medium documents (so a couple of incidental words in a short
    # piece can't fake a strong genre) without making genre detection
    # effectively impossible once a document passes ~6000 words.
    length_factor = max(min(word_count / 300.0, 20.0), 0.3)

    scores = {}
    for key, cfg in _ALL_GENRES.items():
        if key == "historical/classic_literature":
            # Single archaic words, not phrases -- plain substring counting
            # would match "thou" inside "though"/"thousand"/"although" and
            # wildly overcount in completely ordinary modern text.
            raw = sum(len(re.findall(r"\b" + re.escape(sig) + r"\b", text)) for sig in cfg["signals"])
        else:
            raw = sum(text.count(sig) for sig in cfg["signals"])
        if key == "horror_gothic":
            raw += sum(text.count(sig) for sig in _ATMOSPHERE_SIGNALS) * 0.8
        scores[key] = round(raw / length_factor, 2)

    ranked = sorted(scores.items(), key=lambda kv: kv[1], reverse=True)
    best_key, best_score = ranked[0]

    if best_score < 1.2:
        return "neutral", None, scores

    def _parent(key: str) -> str:
        return key.split("/", 1)[0]

    # If the winner is a genre's bare _base but one of its own subgenres
    # scored nearly as high, prefer the more specific subgenre — its
    # vocabulary matching at all is a stronger, more useful signal than
    # the general parent category matching.
    if "/" not in best_key:
        for key, score in ranked[1:]:
            if _parent(key) == best_key:
                if score >= best_score * 0.85:
                    best_key, best_score = key, score
                break  # first same-parent entry is the highest-scoring one; stop looking

    # Find the best-scoring genuinely different genre (not the same parent
    # family, e.g. don't blend "crime/noir_crime" with "crime" or with
    # "crime/heist_crime" — that's not a hybrid, just the same genre's own
    # vocabulary scoring on both its base and a subgenre).
    runner_key, runner_score = None, 0
    for key, score in ranked[1:]:
        if _parent(key) != _parent(best_key):
            runner_key, runner_score = key, score
            break

    if runner_key and runner_score >= best_score * 0.55:
        label, blended = _blending.blend_configs(best_key, _ALL_GENRES[best_key], best_score,
                                                   runner_key, _ALL_GENRES[runner_key], runner_score)
        return label, blended, scores

    return best_key, _ALL_GENRES[best_key], scores


def _elements_from_genre() -> dict:
    return {
        "h1": {"fg": "var(--accent)", "bg": None},
        "h2": {"fg": "var(--accent)", "bg": None},
        "h3": {"fg": "var(--text)", "bg": None},
        "body": {"fg": "var(--text)", "bg": None},
        "entity": {"fg": None, "bg": "auto"},
        "callout": {"fg": None, "bg": "auto"},
        "warning": {"fg": None, "bg": "auto"},
        "timeline": {"fg": "var(--accent)", "bg": None},
        "quote": {"fg": "var(--entity)", "bg": None},
        "th": {"fg": "var(--bg)", "bg": "var(--accent)"},
        "code": {"fg": "var(--text)", "bg": "auto"},
    }


def _lighten_hex(hex_color: str, factor: float) -> str:
    """Mix hex_color with white by factor (0=original, 1=white). Mirrors
    theme_engine._lighten_hex so tints match what the base template renders."""
    try:
        h = hex_color.lstrip("#")
        if len(h) == 3:
            h = "".join(c * 2 for c in h)
        r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
        r2 = int(r + (255 - r) * factor)
        g2 = int(g + (255 - g) * factor)
        b2 = int(b + (255 - b) * factor)
        return f"#{r2:02X}{g2:02X}{b2:02X}"
    except Exception:
        return "#F5F5F5"


# Elements whose fg/bg are 'None'/'auto' placeholders in _elements_from_genre —
# meaning "the base template already colors this, no override needed" — but
# which need a real concrete fg/bg when handed to a consumer (the Designer)
# that has no such base template to fall back on.
_ACCENT_ELEMENT_KEYS = {
    "entity": ("color_entity", 0.92),
    "callout": ("color_callout", 0.92),
    "warning": ("color_warning", 0.93),
    "code": ("color_accent", 0.92),
}


def _resolve_element_vars(elements: dict, palette: dict) -> dict:
    """Replace 'var(--x)' placeholders with this document's actual literal
    hex colors, so the elements map is safe to hand off wholesale to the
    Designer (or any other consumer that isn't rendering inside the
    auto-generated document's own <style> block, where --accent etc. are
    never defined). Also resolves the None/'auto' sentinels on
    entity/callout/warning/code to the same real fg+tinted-bg the base
    template actually renders, instead of leaving values a plain consumer
    can't render (null, or the literal string 'auto')."""
    var_map = {
        "var(--accent)": palette["color_accent"],
        "var(--text)": palette["color_text"],
        "var(--bg)": palette["color_bg"],
        "var(--entity)": palette["color_entity"],
        "var(--border)": palette["color_border"],
    }
    resolved = {}
    for key, el in elements.items():
        fg = var_map.get(el.get("fg"), el.get("fg"))
        bg = var_map.get(el.get("bg"), el.get("bg"))
        if key in _ACCENT_ELEMENT_KEYS:
            color_key, tint_factor = _ACCENT_ELEMENT_KEYS[key]
            accent_color = palette[color_key]
            if fg is None:
                fg = accent_color
            if bg in (None, "auto"):
                bg = _lighten_hex(accent_color, tint_factor)
        resolved[key] = {"fg": fg, "bg": bg}
    return resolved


def design(doc) -> dict:
    """
    Analyze `doc` and generate a bespoke design for it.
    Returns {properties, elements, custom_css, profile} — properties/elements
    match the shape the rest of the theme system already expects, so this
    can be saved as a normal preset afterward.
    """
    all_text = " ".join(b.content for b in doc.all_blocks)
    all_text_lower = all_text.lower()

    genre_key, genre_cfg, scores = _analyze_genre(all_text)
    is_schoolwork_match = genre_cfg is not None and genre_key in _SCHOOLWORK
    is_food = _is_food_content(all_text_lower)

    if is_food and not is_schoolwork_match:
        # Food-mood detection only wins when there's no confident
        # schoolwork match -- otherwise a vocational subject's notes about
        # food (Bakery & Confectionery, Food Production, Home Science...)
        # would get styled as an actual recipe/menu just because the
        # vocabulary overlaps, rather than as what it actually is: school
        # notes about that subject.
        genre_key, genre_cfg, scores = _pick_food_mood(all_text_lower)

    labels = _labels.detect_field_labels(doc)
    quote_count = _labels.detect_pull_quotes(doc)

    seed = seed_unit(doc.title + all_text)

    if genre_cfg is None:
        # No confident genre match — pick from a set of neutral-safe design
        # variants (not one fixed default) and still hue-shift it
        # per-document, so untyped documents don't all converge either.
        variant_seed = seed_unit(all_text[::-1] + doc.title)  # different hash than `seed`
        genre_cfg = _NEUTRAL_VARIANTS[int(variant_seed * len(_NEUTRAL_VARIANTS)) % len(_NEUTRAL_VARIANTS)]

    # Subgenre/aesthetic modifiers (cozy, grimdark, noir, dark academia, ...)
    # layer on top of whatever base genre was resolved — fiction only, and
    # only when a base genre actually matched (food already has its own
    # much richer mood taxonomy and doesn't need a second layer on top).
    modifier_name = None
    if not is_food and genre_key != "neutral":
        leaf = genre_key.rsplit("/", 1)[-1].lower()
        candidate_name, candidate_cfg = pick_modifier(all_text, _MODIFIERS)
        # Don't double-apply a modifier the resolved subgenre already *is*
        # (e.g. skip "[grim]" on top of "fantasy/grimdark", skip "[cozy]"
        # on top of "fantasy/cozy_fantasy") — that's redundant intensification,
        # not a genuine second signal.
        if candidate_cfg and candidate_name not in leaf:
            modifier_name, modifier_cfg = candidate_name, candidate_cfg
            genre_cfg = apply_modifier(genre_cfg, modifier_cfg)

    palette = _palette.generate_palette(genre_cfg["hue"], genre_cfg["sat"], genre_cfg["energy"], seed,
                                         secondary_hue=genre_cfg.get("secondary_hue"))
    dark_bg = palette["dark_bg"]

    properties = {
        "color_bg": palette["color_bg"],
        "color_text": palette["color_text"],
        "color_accent": palette["color_accent"],
        "color_entity": palette["color_entity"],
        "color_callout": palette["color_callout"],
        "color_warning": palette["color_warning"],
        "color_border": palette["color_border"],
        "font_heading": genre_cfg["heading_font"],
        "font_body": genre_cfg["body_font"],
        "font_mono": genre_cfg["mono_font"],
        "base_font_size": "16px",
        "line_height": "1.75" if dark_bg else "1.7",
        "border_radius": "3px" if genre_cfg["label_style"] in ("tracked_upper", "small_caps") else "8px",
        "body_max_width": "760px" if quote_count > 2 else "820px",
    }
    elements = _resolve_element_vars(_elements_from_genre(), palette)

    label_style = genre_cfg["label_style"]
    extra_css = f":root {{ --tertiary: {palette['color_tertiary']}; }}\n"
    extra_css += _decor.LABEL_CSS[label_style].format(mono=genre_cfg["mono_font"])

    def _apply_decor(decor_key, glow_color, wash_color):
        if not (decor_key and decor_key in _decor.DECOR_CSS):
            return ""
        css = _decor.DECOR_CSS[decor_key]
        css = css.replace("__ACCENT_GLOW__", _palette.hex_to_rgba(glow_color, 0.4))
        css = css.replace("__BORDER_WASH__", _palette.hex_to_rgba(wash_color, 0.6))
        return css

    extra_css += _apply_decor(genre_cfg.get("decor"), palette["color_accent"], palette["color_border"])
    # For a genuine hybrid, layer the secondary genre's decoration on top
    # too (its rules can override the primary's where they conflict) so the
    # result visibly carries both moods instead of just one recolored genre
    extra_css += _apply_decor(genre_cfg.get("decor_secondary"), palette["color_tertiary"], palette["color_border"])

    # A recurring pull-quote pattern (character-voice lines, epigraphs) earns
    # a distinct, larger, centered treatment instead of a generic blockquote
    if quote_count >= 2:
        extra_css += """
blockquote {
  text-align: center; font-style: italic; font-size: 1.25em;
  max-width: 34em; margin: 36px auto; padding: 0 20px;
  border: none; color: var(--entity); line-height: 1.5;
}
blockquote::before { content: "\\201C"; font-size: 2em; opacity: 0.5; display: block; color: var(--tertiary); }
"""

    # Character/entity-heavy documents (story bibles, dossiers) read better
    # with a stronger visual break between entities
    entity_count = sum(1 for b in doc.all_blocks if b.type == BlockType.ENTITY)
    if entity_count >= 4:
        extra_css += """
.entity-card { margin: 26px 0 18px; padding-top: 18px; border-top: 1px solid var(--border); }
.entity-card:first-of-type { border-top: none; padding-top: 0; }
.entity-name { font-size: 1.3em; letter-spacing: 0.01em; }
"""

    def _pretty(key: str) -> str:
        if "/" in key:
            parent, leaf = key.split("/", 1)
            return f"{leaf} ({parent})"
        return key

    display_label = " + ".join(_pretty(part.strip()) for part in genre_key.split(" + "))
    if modifier_name:
        display_label = f"{display_label} [{modifier_name}]"

    profile = {
        "genre": display_label,
        "base_genre": genre_key,
        "modifier": modifier_name,
        "is_food": is_food,
        "genre_scores": scores,
        "dark_bg": dark_bg,
        "field_labels_found": labels,
        "label_style": label_style,
        "pull_quote_count": quote_count,
        "entity_count": entity_count,
        "heading_font": genre_cfg["heading_font"],
        "body_font": genre_cfg["body_font"],
        "accent_color": palette["color_accent"],
    }

    return {
        "properties": properties,
        "elements": elements,
        "custom_css": extra_css,
        "field_labels": labels,
        "profile": profile,
    }


def to_pptx_palette(design_result: dict) -> dict:
    """
    Adapt this module's {properties, profile} output into the shape
    presentation_engine.PALETTES entries use (hex without '#', different key
    names) so PPTX export can also reflect the auto-generated design instead
    of silently falling back to the academic PPTX palette.
    """
    p = design_result["properties"]
    dark_bg = design_result["profile"]["dark_bg"]

    def strip(h):
        return h.lstrip("#").upper()

    return {
        "bg": strip(p["color_bg"]),
        "dark": strip(p["color_text"]) if dark_bg else "1A1A2E",
        "primary": strip(p["color_accent"]),
        "secondary": strip(p["color_entity"]),
        "accent": strip(p["color_callout"]),
        "muted": strip(p["color_border"]),
        "text_dark": "FFFFFF" if dark_bg else strip(p["color_text"]),
        "text_light": strip(p["color_text"]) if not dark_bg else "1A1A2E",
        "card": strip(p["color_bg"]),
        "card2": strip(p["color_border"]),
        "warn": strip(p["color_warning"]),
        "success": strip(p["color_callout"]),
        "font_h": design_result["profile"]["heading_font"],
        "font_b": design_result["profile"]["body_font"],
    }


def to_docx_palette(design_result: dict) -> dict:
    """
    Adapt this module's {properties, profile} output into a flat hex-color +
    font-name palette DOCXExporter can apply directly, so DOCX export can
    also reflect the auto-generated design instead of the exporter's
    hardcoded fallback colors.
    """
    p = design_result["properties"]
    prof = design_result["profile"]
    return {
        "bg": p["color_bg"],
        "accent": p["color_accent"],
        "text": p["color_text"],
        "entity": p["color_entity"],
        "callout": p["color_callout"],
        "warning": p["color_warning"],
        "border": p["color_border"],
        "heading_font": prof["heading_font"],
        "body_font": prof["body_font"],
    }


def apply_field_labels(html: str, labels: list) -> str:
    return _labels.apply_field_labels(html, labels)

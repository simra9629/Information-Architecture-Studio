"""
Color math for the auto-design engine: HSL generation, hue blending,
perceptual correction, and the dark/light decision. Kept separate from
genre/mood data so the math never has to be touched when adding a new
genre, modifier, or food mood — those are just data files elsewhere in
this package.
"""

import math
import colorsys


def hsl_to_hex(h, s, l) -> str:
    h = h % 360
    s = max(0.0, min(1.0, s))
    l = max(0.0, min(1.0, l))
    r, g, b = colorsys.hls_to_rgb(h / 360.0, l, s)
    return "#{:02X}{:02X}{:02X}".format(round(r * 255), round(g * 255), round(b * 255))


def hex_to_rgba(hexcolor: str, alpha: float) -> str:
    h = hexcolor.lstrip("#")
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return f"rgba({r}, {g}, {b}, {alpha})"


def blend_hue(h1: float, w1: float, h2: float, w2: float) -> float:
    """Circular mean of two hues (plain averaging breaks near the 0/360 wrap)."""
    a1, a2 = math.radians(h1), math.radians(h2)
    total = w1 + w2 or 1
    x = (math.cos(a1) * w1 + math.cos(a2) * w2) / total
    y = (math.sin(a1) * w1 + math.sin(a2) * w2) / total
    return math.degrees(math.atan2(y, x)) % 360


def perceptual_correction(hue: float) -> float:
    """Yellow/green hues read much lighter than blue/violet at the same L —
    nudge lightness targets so different hues still feel balanced rather
    than yellows looking washed out or blues looking muddy."""
    if 50 <= hue <= 160:
        return -0.05
    if 220 <= hue <= 280:
        return 0.03
    return 0.0


def decide_dark_bg(energy: float, seed: float) -> bool:
    """Energy (how moody/intense the mood is) drives the dark/light choice,
    but as a probability rather than a hardcoded per-genre boolean — so two
    documents with similar-but-not-identical energy can land differently."""
    if energy >= 0.6:
        return True
    if energy <= 0.28:
        return False
    threshold = (energy - 0.28) / (0.6 - 0.28)
    return seed < threshold


def generate_palette(hue: float, sat: float, energy: float, seed: float,
                      secondary_hue: float = None) -> dict:
    """Procedurally build a cohesive, genuinely varied palette from a base
    hue — not a lookup into a fixed set of preset color schemes. Two calls
    with the same mood won't produce pixel-identical results: hue and
    saturation both get a deterministic per-document jitter."""
    hue = (hue + (seed - 0.5) * 30) % 360
    sat = max(0.15, min(0.8, sat * (0.82 + seed * 0.4)))
    dark_bg = decide_dark_bg(energy, seed)
    corr = perceptual_correction(hue)
    tertiary_hue = (secondary_hue if secondary_hue is not None else hue + 195) % 360

    if dark_bg:
        bg_l = 0.07 + corr * 0.3 + seed * 0.03
        bg = hsl_to_hex(hue, min(sat * 0.55, 0.42), bg_l)
        text = hsl_to_hex(hue, min(sat * 0.18, 0.14), 0.90 + corr)
        border = hsl_to_hex(hue, min(sat * 0.4, 0.32), 0.24)
        muted = hsl_to_hex(hue, 0.12, 0.58)
        accent = hsl_to_hex(hue, min(sat + 0.2, 0.92), 0.60 + corr)
        entity = hsl_to_hex((hue + 42) % 360, min(sat + 0.15, 0.85), 0.62)
        callout = hsl_to_hex((hue + 108) % 360, min(sat + 0.1, 0.7), 0.48)
        warning = hsl_to_hex(8, 0.68, 0.58)
        tertiary = hsl_to_hex(tertiary_hue, min(sat + 0.1, 0.75), 0.58)
    else:
        bg_l = 0.955 + corr * 0.15 - seed * 0.02
        bg = hsl_to_hex(hue, min(sat * 0.4, 0.32), bg_l)
        text = hsl_to_hex(hue, min(sat * 0.25, 0.2), 0.15 - corr * 0.3)
        border = hsl_to_hex(hue, min(sat * 0.35, 0.26), 0.82)
        muted = hsl_to_hex(hue, 0.15, 0.44)
        accent = hsl_to_hex(hue, min(sat + 0.12, 0.85), 0.40 + corr * 0.5)
        entity = hsl_to_hex((hue + 42) % 360, min(sat + 0.08, 0.75), 0.36)
        callout = hsl_to_hex((hue + 108) % 360, min(sat + 0.05, 0.6), 0.30)
        warning = hsl_to_hex(8, 0.62, 0.44)
        tertiary = hsl_to_hex(tertiary_hue, min(sat + 0.08, 0.7), 0.38)

    return {
        "color_bg": bg, "color_text": text, "color_border": border,
        "color_muted": muted, "color_accent": accent, "color_entity": entity,
        "color_callout": callout, "color_warning": warning,
        "color_tertiary": tertiary, "dark_bg": dark_bg,
    }

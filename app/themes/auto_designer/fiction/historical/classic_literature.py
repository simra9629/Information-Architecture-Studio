"""Classic Literature — detected by archaic English itself (thou, hath,
wherefore...) rather than by modern descriptive phrases, since real period
prose (Shakespeare, Austen, and so on) is written IN that style rather
than describing itself as being in that style. Deliberately genre-
agnostic: a tragedy, a history, and a comedy of manners can all trigger
this the same way, since what actually identifies them at the prose level
is the period language, not the subject matter.

Matched with word-boundary matching rather than plain substring counting
(see engine.py's special-case for this key) -- "thou" as a raw substring
would also match inside "though", "thousand", "although" and silently
inflate the count in completely ordinary modern text.
"""

CONFIG = {
    "signals": [
        "thou", "thee", "thy", "thine", "hath", "doth", "dost",
        "prithee", "wherefore", "verily", "forsooth", "hither", "thither",
        "whence", "betwixt", "methinks", "mayhap", "sirrah", "alack",
        "hark", "anon", "ere", "morrow",
    ],
    "hue": 35, "sat": 0.35, "energy": 0.15,
    "heading_font": "Cormorant Garamond", "body_font": "EB Garamond", "mono_font": "DM Mono",
    "label_style": "small_caps", "decor": "ornament_divider",
}

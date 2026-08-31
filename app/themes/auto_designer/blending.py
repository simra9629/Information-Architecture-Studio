"""
Blends two close-scoring genre/mood configs into one hybrid design instead
of picking a single winner. Colors blend continuously (circular hue mean);
heading font and label style follow the dominant genre for coherence, but
body font and decoration pull from the secondary genre too whenever it has
real weight — so a hybrid actually reads and looks like a mix.
"""

from app.themes.auto_designer.palette import blend_hue

SECONDARY_WEIGHT_THRESHOLD = 0.38   # below this, secondary's font/decor don't show through
LABEL_HYBRID_THRESHOLD = 0.32       # below this, don't even show "A + B" in the label


def blend_configs(key1, cfg1, score1, key2, cfg2, score2) -> tuple:
    total = score1 + score2
    w1, w2 = score1 / total, score2 / total
    secondary_meaningful = w2 >= SECONDARY_WEIGHT_THRESHOLD

    blended = {
        "hue": blend_hue(cfg1["hue"], w1, cfg2["hue"], w2),
        "sat": cfg1["sat"] * w1 + cfg2["sat"] * w2,
        "energy": cfg1["energy"] * w1 + cfg2["energy"] * w2,
        "heading_font": cfg1["heading_font"],
        "body_font": cfg2["body_font"] if secondary_meaningful else cfg1["body_font"],
        "mono_font": cfg2["mono_font"] if secondary_meaningful and cfg2["mono_font"] != cfg1["mono_font"] else cfg1["mono_font"],
        "label_style": cfg1["label_style"],
        "decor": cfg1["decor"],
        "decor_secondary": cfg2["decor"] if secondary_meaningful and cfg2["decor"] != cfg1["decor"] else None,
        "secondary_hue": cfg2["hue"],
    }
    label = f"{key1} + {key2}" if w2 >= LABEL_HYBRID_THRESHOLD else key1
    return label, blended

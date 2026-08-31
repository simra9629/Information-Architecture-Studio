"""
Modifiers are reusable "flavor" adjustments (cozy, grim/grimdark, noir,
dark academia, cottagecore, cyberpunk aesthetic, noblebright, retro) that
layer on top of a resolved base genre. This is what makes "Cozy Mystery,"
"Grimdark Fantasy," "Noir Mystery," and "Dark Academia" flavored fiction
possible without hand-authoring a separate config for every one of the
hundreds of named subgenres — the modifier is detected independently and
applied as a delta to whatever base genre (or hybrid) was already resolved.
"""


def apply_modifier(cfg: dict, modifier_cfg: dict) -> dict:
    new_cfg = dict(cfg)
    new_cfg["hue"] = (cfg["hue"] + modifier_cfg.get("hue_shift", 0)) % 360
    new_cfg["sat"] = max(0.12, min(0.85, cfg["sat"] * modifier_cfg.get("sat_mult", 1.0)))
    new_cfg["energy"] = max(0.05, min(0.85, cfg["energy"] * modifier_cfg.get("energy_mult", 1.0)))
    if modifier_cfg.get("decor_override"):
        new_cfg["decor"] = modifier_cfg["decor_override"]
    if modifier_cfg.get("label_style_override"):
        new_cfg["label_style"] = modifier_cfg["label_style_override"]
    if modifier_cfg.get("heading_font_override"):
        new_cfg["heading_font"] = modifier_cfg["heading_font_override"]
    if modifier_cfg.get("body_font_override"):
        new_cfg["body_font"] = modifier_cfg["body_font_override"]
    return new_cfg


def pick_modifier(all_text: str, modifiers: dict, exclude_base_key: str = None):
    """
    Score the text against every registered modifier's signals; return
    (name, config) for the strongest one that clears a minimum bar, or
    (None, None) if nothing distinctive enough was found.
    """
    text = all_text.lower()
    word_count = max(len(text.split()), 1)
    length_factor = max(word_count / 300.0, 0.3)

    best_name, best_score = None, 0.0
    for name, cfg in modifiers.items():
        if name == exclude_base_key:
            continue
        raw = sum(text.count(sig) for sig in cfg["signals"])
        score = raw / length_factor
        if score > best_score:
            best_name, best_score = name, score

    if best_score < 1.0:
        return None, None
    return best_name, modifiers[best_name]

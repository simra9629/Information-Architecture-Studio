"""
Fiction genre families, one subfolder per top-level genre (adventure/,
fantasy/, horror/, ...). Each genre folder has its own _base.py (the
general config for that genre) plus one small file per named subgenre —
to add a new subgenre, add a new file to the right folder; nothing else
needs to change (see registry.py for how these get auto-discovered).
"""

from app.themes.auto_designer.registry import load_nested_configs

FAMILIES = load_nested_configs(__name__, __path__)

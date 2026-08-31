"""
Subgenre/aesthetic modifiers (cozy, grimdark, noir, dark academia,
cottagecore, cyberpunk aesthetic, noblebright, retro, ...) that layer onto
a resolved base genre. Add a new file here to support a new modifier —
_apply.py (leading underscore, skipped by auto-discovery) has the blending
logic that's shared across all of them.
"""

from app.themes.auto_designer.registry import load_configs

MODIFIERS = load_configs(__name__, __path__)

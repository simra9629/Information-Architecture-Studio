"""
Food/recipe moods. Recipes don't really have "genres" — the interesting
design signal is the character of the dish itself (cozy comfort food vs.
bold and fiery vs. elegant fine dining, etc). Same auto-discovery pattern:
add a file, it's picked up automatically.
"""

from app.themes.auto_designer.registry import load_configs

MOODS = load_configs(__name__, __path__)

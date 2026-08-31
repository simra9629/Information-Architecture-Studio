"""Non-fiction document registers, one subfolder per top-level category
(academic_educational/, business_corporate/, technology_engineering/, ...).
Same nested pattern as fiction/ — each category folder has a _base.py plus
one file per specific document type."""

from app.themes.auto_designer.registry import load_nested_configs

FAMILIES = load_nested_configs(__name__, __path__)

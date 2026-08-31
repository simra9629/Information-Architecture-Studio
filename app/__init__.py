"""
Schoolwork genre family, one subfolder per subject cluster (languages/,
humanities/, sciences/, commerce/, computing/, arts/, applied/,
vocational/) -- one file per subject, each with real subject-specific
vocabulary as its "signals" so a student's actual revision notes/schoolwork
(not just a document that describes itself as being about that subject)
gets recognized. To add a new subject, add a new file to the right
folder; nothing else needs to change (see registry.py for how these get
auto-discovered).
"""

from app.themes.auto_designer.registry import load_nested_configs

FAMILIES = load_nested_configs(__name__, __path__)

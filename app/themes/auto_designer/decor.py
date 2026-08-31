"""
Structural decoration CSS: per-mood typographic/label treatments and
larger structural flourishes (dividers, glows, grid lines, etc). These are
referenced by name (a "decor" or "label_style" string) from genre/mood
config files, so adding a new decor option here makes it available to
every genre file without touching them.
"""

LABEL_CSS = {
    "tracked_upper": """
.ias-auto-label {{
  display: inline-block; font-family: {mono}, monospace; font-size: 0.7em;
  font-weight: 700; text-transform: uppercase; letter-spacing: 0.12em;
  color: var(--accent); margin-right: 8px; vertical-align: 2px;
}}""",
    "small_caps": """
.ias-auto-label {{
  font-variant: small-caps; font-weight: 700; font-size: 1.02em;
  color: var(--accent); letter-spacing: 0.02em; margin-right: 6px;
}}""",
    "italic_label": """
.ias-auto-label {{
  font-style: italic; font-weight: 600; color: var(--entity);
  margin-right: 6px;
}}""",
    "pill": """
.ias-auto-label {{
  display: inline-block; background: var(--accent); color: var(--bg);
  font-size: 0.68em; font-weight: 700; text-transform: uppercase;
  letter-spacing: 0.06em; padding: 2px 9px; border-radius: 999px;
  margin-right: 8px; vertical-align: 2px;
}}""",
}

# Placeholders __ACCENT_GLOW__ / __BORDER_WASH__ are resolved to plain
# rgba() literals at design time (WeasyPrint doesn't support CSS
# color-mix(), so these can't be computed at CSS-parse time).
DECOR_CSS = {
    "underline_glow": """
h1 { border-bottom: 2px solid var(--accent); padding-bottom: 12px;
     text-shadow: 0 0 24px __ACCENT_GLOW__; }
h2 { border-left: 3px solid var(--accent); padding-left: 12px; }
""",
    "ornament_divider": """
h2::before { content: "\\2726\\fe0e"; color: var(--accent); margin-right: 10px; font-size: 0.8em; }
hr { border: none; text-align: center; height: 1em; }
hr::after { content: "\\2726\\fe0e \\2726\\fe0e \\2726\\fe0e"; color: var(--accent); letter-spacing: 0.5em; font-size: 0.8em; }
""",
    "grid_lines": """
body { background-image: linear-gradient(__BORDER_WASH__ 1px, transparent 1px);
       background-size: 100% 28px; }
h1 { letter-spacing: 0.02em; }
h1::after { content: ""; display: block; width: 46px; height: 3px; background: var(--accent); margin-top: 10px; }
""",
    "left_bar": """
h1, h2 { border-left: 4px solid var(--accent); padding-left: 14px; }
.entity-card { border-left: 3px solid var(--tertiary); }
""",
    "soft_round": """
h1, h2 { letter-spacing: -0.01em; }
.entity-card, .callout, .warning { border-radius: 14px; }
th { border-radius: 6px 6px 0 0; }
""",
    "rule_under": """
h1 { border-bottom: 3px double var(--border); padding-bottom: 10px; }
h2 { border-bottom: 1px solid var(--border); padding-bottom: 6px; }
""",
    "candlelit": """
h1 { text-shadow: 0 0 18px __ACCENT_GLOW__, 0 0 3px __ACCENT_GLOW__; }
body { background-image: radial-gradient(ellipse at top, __BORDER_WASH__ 0%, transparent 60%); }
""",
    "torn_edge": """
.entity-card, .callout, .warning { box-shadow: 0 1px 0 __BORDER_WASH__, 0 -1px 0 __BORDER_WASH__; }
h2 { border-bottom: 1px dashed var(--border); padding-bottom: 6px; }
""",
}

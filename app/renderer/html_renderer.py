import re
import html as html_lib
from app.models.document import Block, BlockType, Document
from app.renderer import decorations
from app.renderer import doodle_icons


# ─────────────────────────────────────────────────────────
#  Theme CSS definitions
# ─────────────────────────────────────────────────────────

TASK_LIST_CSS = """
  .task-item { margin: 10px 0; }
  .task-row { display: flex; align-items: flex-start; gap: 8px; cursor: default; }
  .task-row input[type="checkbox"] { margin-top: 3px; width: 15px; height: 15px; accent-color: var(--accent, #2B4C9B); flex-shrink: 0; }
  .task-row span { flex: 1; }
  .task-row.checked span { text-decoration: line-through; opacity: 0.6; }
  .task-subtasks { list-style: none; margin: 6px 0 0; padding-left: 26px; border-left: 2px solid var(--border, #D8DCE8); }
  .task-subtasks li { margin: 6px 0; }

  .ias-figure { margin: 24px auto; max-width: 100%; text-align: center; }
  .ias-figure img {
    max-width: 100%; height: auto; display: block; margin: 0 auto;
    border-radius: 8px; border: 1px solid var(--border, #D8DCE8);
    box-shadow: 0 2px 10px rgba(0,0,0,0.08);
  }
  .ias-figure figcaption {
    margin-top: 8px; font-size: 0.85em; color: var(--muted, #666);
    font-style: italic; line-height: 1.4;
  }
  .ias-figure-ocr {
    margin-top: 6px; font-size: 0.8em; color: var(--muted, #666);
    line-height: 1.4; text-align: left; display: inline-block;
    max-width: 90%; opacity: 0.85;
  }
  .ias-figure-ocr summary { cursor: pointer; font-style: italic; text-align: center; }
  .ias-figure.ias-figure-small { max-width: 60%; }
  .ias-figure.ias-figure-wide { max-width: 100%; }
"""

def _flatten_subtasks(subtasks: list) -> list:
    """Flatten a nested subtask tree into a flat list (for counting done/total)."""
    out = []
    for s in subtasks or []:
        out.append(s)
        out.extend(_flatten_subtasks(s.get("subtasks") or []))
    return out


THEME_CSS = {

"academic": """
  @import url('https://fonts.googleapis.com/css2?family=Lora:ital,wght@0,400;0,600;1,400&family=Source+Sans+3:wght@300;400;600&display=swap');
  :root { --accent: #2B4C9B; --accent-light: #E8EEF8; --warn: #C0392B; --warn-bg: #FDECEA;
          --call: #1A6E4A; --call-bg: #E8F5EE; --entity: #5D3A8E; --entity-bg: #F2ECF8;
          --border: #D8DCE8; --bg: #FAFAFA; --text: #1A1A2E; --muted: #666; }
  body { font-family: 'Source Sans 3', sans-serif; background: var(--bg); color: var(--text);
         max-width: 820px; margin: 0 auto; padding: 48px 40px; line-height: 1.75; font-size: 16px; }
  h1 { font-family: 'Lora', serif; font-size: 2.4em; color: var(--text); border-bottom: 2px solid var(--accent);
       padding-bottom: 12px; margin-bottom: 8px; font-weight: 600; }
  h2 { font-family: 'Lora', serif; font-size: 1.55em; color: var(--accent); margin: 36px 0 12px;
       padding-bottom: 6px; border-bottom: 1px solid var(--border); font-weight: 600; }
  h3 { font-family: 'Lora', serif; font-size: 1.2em; color: var(--text); margin: 24px 0 8px; font-weight: 600; }
  h4 { font-family: 'Source Sans 3', sans-serif; font-size: 1em; font-weight: 600; color: var(--muted);
       text-transform: uppercase; letter-spacing: 0.05em; margin: 20px 0 6px; }
  p { margin: 0 0 14px; }
  .entity-card { background: var(--entity-bg); border-left: 4px solid var(--entity);
                 border-radius: 4px; padding: 14px 18px; margin: 18px 0; }
  .entity-card .entity-name { font-family: 'Lora', serif; font-size: 1.1em; font-weight: 600;
                               color: var(--entity); margin-bottom: 4px; }
  .callout { background: var(--call-bg); border-left: 4px solid var(--call);
             border-radius: 4px; padding: 12px 16px; margin: 16px 0; }
  .callout::before { content: "ℹ Note"; font-size: 0.75em; font-weight: 600; color: var(--call);
                     display: block; margin-bottom: 4px; text-transform: uppercase; letter-spacing: 0.06em; }
  .warning { background: var(--warn-bg); border-left: 4px solid var(--warn);
             border-radius: 4px; padding: 12px 16px; margin: 16px 0; }
  .warning::before { content: "⚠ Warning"; font-size: 0.75em; font-weight: 600; color: var(--warn);
                     display: block; margin-bottom: 4px; text-transform: uppercase; letter-spacing: 0.06em; }
  .timeline-event { display: flex; gap: 14px; margin: 10px 0; align-items: flex-start; }
  .timeline-event .dot { width: 10px; height: 10px; border-radius: 50%; background: var(--accent);
                          margin-top: 6px; flex-shrink: 0; }
  .relationship { font-style: italic; color: var(--muted); margin: 6px 0 6px 16px; }
  .definition { background: var(--accent-light); padding: 10px 14px; border-radius: 4px; margin: 12px 0; }
  blockquote { border-left: 3px solid var(--border); padding: 8px 20px; margin: 16px 0;
               color: var(--muted); font-style: italic; }
  ul, ol { margin: 8px 0 14px 22px; }
  li { margin-bottom: 4px; }
  code { background: #F0F0F0; padding: 2px 6px; border-radius: 3px; font-size: 0.9em; }
  pre { background: #F5F5F5; border: 1px solid var(--border); border-radius: 6px;
        padding: 16px; overflow-x: auto; margin: 16px 0; }
  table { width: 100%; border-collapse: collapse; margin: 16px 0; }
  th { background: var(--accent-light); color: var(--accent); font-weight: 600;
       padding: 10px 14px; text-align: left; border-bottom: 2px solid var(--accent); }
  td { padding: 9px 14px; border-bottom: 1px solid var(--border); }
  .importance-high .entity-name { font-size: 1.25em; }
  .doc-meta { font-size: 0.85em; color: var(--muted); margin-bottom: 32px; }
  hr { border: none; border-top: 1px solid var(--border); margin: 32px 0; }
""",

"magazine": """
  @import url('https://fonts.googleapis.com/css2?family=Bebas+Neue&family=Libre+Baskerville:ital,wght@0,400;0,700;1,400&family=Inter:wght@300;400;500;600&display=swap');
  :root { --accent: #E63946; --bg: #FFFFFF; --text: #111; --muted: #555; --border: #E0E0E0;
          --entity-bg: #FFF8F8; --call-bg: #F0FFF4; --warn-bg: #FFF5F5; }
  body { font-family: 'Inter', sans-serif; background: var(--bg); color: var(--text);
         max-width: 900px; margin: 0 auto; padding: 48px 40px; font-size: 16px; line-height: 1.7; }
  h1 { font-family: 'Bebas Neue', sans-serif; font-size: 4em; letter-spacing: 0.02em;
       color: var(--text); line-height: 1; margin-bottom: 6px; text-transform: uppercase; }
  h2 { font-family: 'Bebas Neue', sans-serif; font-size: 2em; color: var(--accent);
       text-transform: uppercase; letter-spacing: 0.05em; margin: 40px 0 12px; border-top: 3px solid var(--text);
       padding-top: 10px; }
  h3 { font-family: 'Libre Baskerville', serif; font-size: 1.2em; font-style: italic;
       color: var(--text); margin: 24px 0 8px; }
  p { margin: 0 0 16px; }
  .entity-card { border: 1px solid var(--border); padding: 20px; margin: 20px 0;
                 display: flex; gap: 16px; align-items: flex-start; }
  .entity-card .entity-icon { font-size: 2.2em; line-height: 1; flex-shrink: 0; }
  .entity-card .entity-name { font-family: 'Bebas Neue', sans-serif; font-size: 1.5em;
                               color: var(--text); letter-spacing: 0.03em; }
  .entity-card .entity-body { font-size: 0.9em; color: var(--muted); margin-top: 4px; }
  .callout { background: var(--call-bg); border: 1px solid #A8D5B5; padding: 14px 18px; margin: 18px 0; }
  .callout::before { content: "KEY POINT"; font-size: 0.7em; font-weight: 700; color: #2E7D32;
                     display: block; margin-bottom: 4px; letter-spacing: 0.1em; }
  .warning { background: var(--warn-bg); border: 1px solid #F5A0A0; padding: 14px 18px; margin: 18px 0; }
  .warning::before { content: "WARNING"; font-size: 0.7em; font-weight: 700; color: var(--accent);
                     display: block; margin-bottom: 4px; letter-spacing: 0.1em; }
  .pull-quote { font-family: 'Libre Baskerville', serif; font-size: 1.5em; font-style: italic;
                color: var(--accent); border-top: 2px solid var(--accent); border-bottom: 2px solid var(--accent);
                padding: 18px 0; margin: 28px 0; text-align: center; }
  .timeline-event { padding: 8px 0 8px 20px; border-left: 3px solid var(--accent); margin: 8px 0; }
  .relationship { font-size: 0.9em; color: var(--muted); font-style: italic; margin: 4px 0; }
  blockquote { font-family: 'Libre Baskerville', serif; font-style: italic; font-size: 1.1em;
               color: var(--muted); border-left: 4px solid var(--accent); padding: 8px 20px; margin: 16px 0; }
  ul, ol { margin: 8px 0 14px 22px; }
  li { margin-bottom: 5px; }
  table { width: 100%; border-collapse: collapse; margin: 16px 0; }
  th { background: var(--text); color: white; padding: 10px 14px; text-align: left; font-size: 0.8em;
       text-transform: uppercase; letter-spacing: 0.06em; }
  td { padding: 9px 14px; border-bottom: 1px solid var(--border); }
  .doc-meta { font-size: 0.8em; color: var(--muted); margin-bottom: 32px; letter-spacing: 0.03em; text-transform: uppercase; }
  hr { border: none; border-top: 3px solid var(--text); margin: 36px 0; }
  code { background: #F5F5F5; padding: 2px 6px; font-size: 0.9em; }
  pre { background: #F5F5F5; padding: 16px; overflow-x: auto; margin: 16px 0; }
""",

"codex": """
  @import url('https://fonts.googleapis.com/css2?family=IM+Fell+English:ital@0;1&family=Cinzel:wght@400;600&family=Crimson+Text:ital,wght@0,400;0,600;1,400&display=swap');
  :root { --bg: #F7F0DC; --bg2: #EEE4C4; --text: #2C1810; --accent: #7B4F1E; --accent2: #C4952A;
          --border: #C8A96A; --entity-bg: #EDE0C4; --call-bg: #E8F0E0; --warn-bg: #F5E8DC; }
  body { font-family: 'Crimson Text', serif; background: var(--bg); color: var(--text);
         max-width: 780px; margin: 0 auto; padding: 52px 48px; font-size: 17px; line-height: 1.8;
         background-image: repeating-linear-gradient(0deg, transparent, transparent 27px, rgba(200,169,106,0.12) 28px); }
  h1 { font-family: 'Cinzel', serif; font-size: 2.2em; color: var(--accent); text-align: center;
       margin-bottom: 8px; letter-spacing: 0.04em;
       border-bottom: double 4px var(--border); padding-bottom: 16px; font-weight: 600; }
  h2 { font-family: 'Cinzel', serif; font-size: 1.35em; color: var(--accent); margin: 36px 0 12px;
       letter-spacing: 0.06em; font-weight: 600;
       border-bottom: 1px solid var(--border); padding-bottom: 6px; }
  h3 { font-family: 'IM Fell English', serif; font-size: 1.2em; color: var(--accent); margin: 22px 0 8px; }
  p { margin: 0 0 14px; text-indent: 1.5em; }
  p:first-of-type { text-indent: 0; }
  .entity-card { background: var(--entity-bg); border: 1px solid var(--border); padding: 16px 20px;
                 margin: 20px 0; position: relative; }
  .entity-card::before { content: "✦"; position: absolute; top: -10px; left: 50%; transform: translateX(-50%);
                          background: var(--entity-bg); padding: 0 8px; color: var(--accent2); font-size: 1.2em; }
  .entity-card .entity-name { font-family: 'Cinzel', serif; font-size: 1.05em; color: var(--accent);
                               font-weight: 600; margin-bottom: 6px; }
  .callout { background: var(--call-bg); border: 1px solid #A8B89A; padding: 12px 18px; margin: 16px 0;
             font-style: italic; }
  .callout::before { content: "~ Note ~"; font-style: normal; font-family: 'Cinzel', serif;
                     font-size: 0.75em; color: #4A6640; display: block; margin-bottom: 4px; letter-spacing: 0.08em; }
  .warning { background: var(--warn-bg); border: 1px solid #C0885A; padding: 12px 18px; margin: 16px 0; }
  .warning::before { content: "⚔ Heed This Warning"; font-family: 'Cinzel', serif;
                     font-size: 0.75em; color: var(--accent); display: block; margin-bottom: 4px; letter-spacing: 0.06em; }
  .timeline-event { padding: 8px 12px 8px 24px; border-left: 2px solid var(--accent2); margin: 8px 0;
                    font-style: italic; }
  .relationship { color: var(--accent); font-style: italic; margin: 6px 0 6px 16px; }
  blockquote { border: 1px solid var(--border); background: var(--bg2); padding: 14px 22px;
               margin: 20px 12px; font-style: italic; text-align: center; }
  ul, ol { margin: 8px 0 14px 24px; }
  li { margin-bottom: 5px; }
  table { width: 100%; border-collapse: collapse; margin: 16px 0; }
  th { background: var(--bg2); color: var(--accent); font-family: 'Cinzel', serif; font-size: 0.85em;
       padding: 10px 14px; text-align: left; border-bottom: 2px solid var(--border); }
  td { padding: 9px 14px; border-bottom: 1px solid var(--border); }
  .doc-meta { text-align: center; font-style: italic; color: var(--accent); margin-bottom: 36px; font-size: 0.9em; }
  hr { border: none; text-align: center; margin: 30px 0; color: var(--accent2); }
  hr::after { content: "⸻ ✦ ⸻"; font-size: 1em; }
  code { background: var(--bg2); padding: 2px 6px; font-size: 0.9em; }
  pre { background: var(--bg2); border: 1px solid var(--border); padding: 14px; overflow-x: auto; margin: 16px 0; }
""",

"corporate": """
  @import url('https://fonts.googleapis.com/css2?family=DM+Sans:ital,wght@0,300;0,400;0,500;0,700;1,400&family=DM+Mono:wght@400;500&display=swap');
  :root { --accent: #1E3A5F; --accent2: #2E86AB; --bg: #F8F9FC; --card-bg: #FFFFFF;
          --text: #1A1A2E; --muted: #6B7280; --border: #E2E8F0; --success: #059669; --warn: #D97706; }
  body { font-family: 'DM Sans', sans-serif; background: var(--bg); color: var(--text);
         max-width: 900px; margin: 0 auto; padding: 40px; font-size: 15px; line-height: 1.65; }
  h1 { font-size: 1.9em; font-weight: 700; color: var(--accent); border-left: 5px solid var(--accent2);
       padding-left: 16px; margin-bottom: 6px; }
  h2 { font-size: 1.3em; font-weight: 700; color: var(--accent); margin: 32px 0 10px;
       padding-bottom: 6px; border-bottom: 2px solid var(--accent2); text-transform: uppercase;
       letter-spacing: 0.04em; font-size: 0.95em; }
  h3 { font-size: 1.1em; font-weight: 700; color: var(--text); margin: 20px 0 6px; }
  p { margin: 0 0 12px; }
  .entity-card { background: var(--card-bg); border: 1px solid var(--border); border-radius: 6px;
                 padding: 16px 20px; margin: 14px 0; box-shadow: 0 1px 3px rgba(0,0,0,0.05); }
  .entity-card .entity-name { font-weight: 700; color: var(--accent); margin-bottom: 4px; font-size: 1.05em; }
  .callout { background: #EFF6FF; border: 1px solid #BFDBFE; border-radius: 6px; padding: 12px 16px; margin: 14px 0; }
  .callout::before { content: "ℹ INFO"; font-size: 0.7em; font-weight: 700; color: #1D4ED8;
                     display: block; margin-bottom: 4px; letter-spacing: 0.08em; }
  .warning { background: #FFFBEB; border: 1px solid #FDE68A; border-radius: 6px; padding: 12px 16px; margin: 14px 0; }
  .warning::before { content: "⚠ ACTION REQUIRED"; font-size: 0.7em; font-weight: 700; color: var(--warn);
                     display: block; margin-bottom: 4px; letter-spacing: 0.08em; }
  .timeline-event { display: flex; gap: 12px; padding: 8px 0; border-bottom: 1px solid var(--border); }
  .timeline-event::before { content: "▸"; color: var(--accent2); font-size: 0.9em; }
  .relationship { color: var(--muted); font-size: 0.9em; margin: 4px 0 4px 12px; }
  blockquote { border-left: 4px solid var(--accent2); padding: 8px 18px; margin: 16px 0;
               color: var(--muted); background: var(--card-bg); }
  ul, ol { margin: 6px 0 12px 20px; }
  li { margin-bottom: 4px; }
  table { width: 100%; border-collapse: collapse; margin: 14px 0; font-size: 0.9em; }
  th { background: var(--accent); color: white; padding: 10px 14px; text-align: left;
       font-size: 0.8em; text-transform: uppercase; letter-spacing: 0.06em; }
  td { padding: 9px 14px; border-bottom: 1px solid var(--border); }
  tr:hover td { background: #F8FAFF; }
  .doc-meta { font-size: 0.8em; color: var(--muted); margin-bottom: 28px; }
  hr { border: none; border-top: 1px solid var(--border); margin: 28px 0; }
  code { font-family: 'DM Mono', monospace; background: #F1F5F9; padding: 2px 6px;
         border-radius: 3px; font-size: 0.88em; }
  pre { font-family: 'DM Mono', monospace; background: #F1F5F9; border: 1px solid var(--border);
        border-radius: 6px; padding: 16px; overflow-x: auto; margin: 14px 0; }
""",

"detective": """
  @import url('https://fonts.googleapis.com/css2?family=Special+Elite&family=Courier+Prime:ital,wght@0,400;0,700;1,400&family=Oswald:wght@400;600&display=swap');
  :root { --bg: #C8B99A; --paper: #D4C5A9; --dark: #1A1008; --accent: #8B1A1A; --muted: #5A4A3A;
          --border: #8B7355; --stamp: #B22222; --blue-ink: #1A3A6A; }
  body { font-family: 'Courier Prime', monospace; background: var(--bg); color: var(--dark);
         max-width: 820px; margin: 0 auto; padding: 48px 44px;
         background-image: repeating-linear-gradient(45deg, transparent, transparent 10px, rgba(0,0,0,0.015) 10px, rgba(0,0,0,0.015) 20px);
         font-size: 15px; line-height: 1.7; }
  h1 { font-family: 'Special Elite', cursive; font-size: 2.2em; color: var(--dark);
       border-top: 3px solid var(--dark); border-bottom: 3px solid var(--dark);
       padding: 10px 0; text-align: center; margin-bottom: 8px; letter-spacing: 0.04em; }
  h2 { font-family: 'Oswald', sans-serif; font-size: 1.2em; font-weight: 600; color: var(--dark);
       text-transform: uppercase; letter-spacing: 0.1em; margin: 32px 0 10px;
       border-bottom: 2px solid var(--dark); padding-bottom: 4px; }
  h3 { font-family: 'Special Elite', cursive; font-size: 1.1em; color: var(--accent); margin: 20px 0 8px; }
  p { margin: 0 0 14px; }
  .entity-card { background: var(--paper); border: 1px solid var(--border); padding: 14px 18px;
                 margin: 16px 0; position: relative; box-shadow: 2px 2px 0 rgba(0,0,0,0.15); }
  .entity-card::before { content: "SUBJECT FILE"; position: absolute; top: -1px; right: 12px;
                          font-family: 'Oswald', sans-serif; font-size: 0.65em; letter-spacing: 0.1em;
                          color: var(--stamp); font-weight: 600; padding: 2px 6px;
                          border-bottom: 2px solid var(--stamp); }
  .entity-card .entity-name { font-family: 'Special Elite', cursive; font-size: 1.1em;
                               color: var(--blue-ink); margin-bottom: 4px; }
  .callout { background: #FFFFCC; border: 1px solid #CCCC66; padding: 12px 16px; margin: 14px 0;
             box-shadow: 2px 2px 0 rgba(0,0,0,0.12); transform: rotate(-0.3deg); }
  .callout::before { content: "★ NOTE"; font-size: 0.7em; font-weight: 700; color: #666600;
                     display: block; margin-bottom: 4px; letter-spacing: 0.08em; font-family: 'Oswald', sans-serif; }
  .warning { background: #FFEEEE; border: 2px solid var(--stamp); padding: 12px 16px; margin: 14px 0;
             transform: rotate(0.4deg); box-shadow: 2px 2px 0 rgba(0,0,0,0.12); }
  .warning::before { content: "⚠ RED FLAG"; font-family: 'Oswald', sans-serif;
                     font-size: 0.7em; font-weight: 700; color: var(--stamp);
                     display: block; margin-bottom: 4px; letter-spacing: 0.1em; }
  .timeline-event { padding: 6px 0 6px 20px; border-left: 2px solid var(--dark); margin: 6px 0; }
  .relationship { color: var(--blue-ink); font-style: italic; margin: 4px 0 4px 12px; }
  blockquote { border: 1px dashed var(--border); padding: 10px 18px; margin: 16px 8px;
               background: rgba(255,255,255,0.3); font-style: italic; }
  ul, ol { margin: 8px 0 14px 22px; }
  li { margin-bottom: 5px; }
  li::marker { color: var(--accent); }
  table { width: 100%; border-collapse: collapse; margin: 14px 0; }
  th { background: var(--dark); color: var(--paper); padding: 9px 14px; text-align: left;
       font-family: 'Oswald', sans-serif; font-size: 0.8em; letter-spacing: 0.06em; text-transform: uppercase; }
  td { padding: 9px 14px; border-bottom: 1px solid var(--border); }
  .doc-meta { text-align: center; font-size: 0.85em; color: var(--muted); margin-bottom: 32px;
              font-family: 'Oswald', sans-serif; letter-spacing: 0.06em; text-transform: uppercase; }
  hr { border: none; border-top: 1px dashed var(--border); margin: 28px 0; }
  code { background: rgba(0,0,0,0.08); padding: 2px 5px; font-size: 0.9em; }
  pre { background: rgba(0,0,0,0.06); border: 1px solid var(--border); padding: 14px; overflow-x: auto; margin: 14px 0; }
""",

"cyberpunk": """
  @import url('https://fonts.googleapis.com/css2?family=Share+Tech+Mono&family=Rajdhani:wght@400;500;600;700&family=Orbitron:wght@400;600&display=swap');
  :root { --bg: #0A0A12; --bg2: #0F0F1A; --text: #C8D8E8; --cyan: #00E5FF; --magenta: #FF00AA;
          --green: #39FF14; --border: #1E3050; --muted: #4A6080; --warn: #FF6600; }
  body { font-family: 'Share Tech Mono', monospace; background: var(--bg); color: var(--text);
         max-width: 860px; margin: 0 auto; padding: 40px;
         background-image: linear-gradient(rgba(0,229,255,0.03) 1px, transparent 1px),
                           linear-gradient(90deg, rgba(0,229,255,0.03) 1px, transparent 1px);
         background-size: 40px 40px;
         font-size: 14px; line-height: 1.75; }
  h1 { font-family: 'Orbitron', monospace; font-size: 1.9em; font-weight: 600; color: var(--cyan);
       text-shadow: 0 0 10px rgba(0,229,255,0.5); border-bottom: 1px solid var(--cyan);
       padding-bottom: 10px; margin-bottom: 6px; letter-spacing: 0.05em; text-transform: uppercase; }
  h2 { font-family: 'Rajdhani', sans-serif; font-size: 1.2em; font-weight: 700; color: var(--magenta);
       text-transform: uppercase; letter-spacing: 0.12em; margin: 36px 0 12px;
       border-left: 3px solid var(--magenta); padding-left: 12px; }
  h3 { font-family: 'Rajdhani', sans-serif; font-size: 1.1em; font-weight: 600; color: var(--cyan);
       letter-spacing: 0.06em; margin: 22px 0 8px; text-transform: uppercase; }
  p { margin: 0 0 14px; color: var(--text); }
  .entity-card { background: var(--bg2); border: 1px solid var(--cyan); padding: 14px 18px;
                 margin: 16px 0; position: relative; }
  .entity-card::before { content: "// ENTITY //"; position: absolute; top: -10px; left: 12px;
                          background: var(--bg); padding: 0 8px; font-size: 0.7em;
                          color: var(--cyan); letter-spacing: 0.1em; }
  .entity-card .entity-name { font-family: 'Orbitron', monospace; font-size: 0.95em; font-weight: 600;
                               color: var(--cyan); margin-bottom: 6px; text-transform: uppercase; }
  .callout { background: rgba(0,229,255,0.05); border: 1px solid rgba(0,229,255,0.3);
             padding: 12px 16px; margin: 14px 0; }
  .callout::before { content: "> SYSTEM NOTE"; font-size: 0.7em; color: var(--cyan);
                     display: block; margin-bottom: 4px; letter-spacing: 0.1em; }
  .warning { background: rgba(255,102,0,0.08); border: 1px solid var(--warn); padding: 12px 16px; margin: 14px 0; }
  .warning::before { content: "!! WARNING ALERT"; font-size: 0.7em; color: var(--warn);
                     display: block; margin-bottom: 4px; letter-spacing: 0.1em; }
  .timeline-event { padding: 6px 0 6px 16px; border-left: 2px solid var(--green); margin: 6px 0; color: var(--green); }
  .relationship { color: var(--magenta); font-style: italic; margin: 4px 0 4px 12px; font-size: 0.9em; }
  blockquote { border-left: 2px solid var(--magenta); padding: 8px 18px; margin: 14px 0;
               color: var(--muted); }
  ul, ol { margin: 8px 0 14px 22px; }
  li { margin-bottom: 4px; }
  li::marker { color: var(--cyan); }
  table { width: 100%; border-collapse: collapse; margin: 14px 0; }
  th { background: rgba(0,229,255,0.1); color: var(--cyan); padding: 10px 14px; text-align: left;
       border-bottom: 1px solid var(--cyan); font-family: 'Rajdhani', sans-serif;
       font-size: 0.8em; letter-spacing: 0.1em; text-transform: uppercase; }
  td { padding: 9px 14px; border-bottom: 1px solid var(--border); }
  .doc-meta { font-size: 0.8em; color: var(--muted); margin-bottom: 32px; letter-spacing: 0.06em; }
  hr { border: none; border-top: 1px solid var(--border); margin: 28px 0; }
  code { color: var(--green); background: rgba(57,255,20,0.06); padding: 2px 6px; font-size: 0.92em; }
  pre { background: var(--bg2); border: 1px solid var(--border); padding: 16px; overflow-x: auto; margin: 14px 0; }
""",

"noir": """
  @import url('https://fonts.googleapis.com/css2?family=Playfair+Display:ital,wght@0,400;0,700;1,400&family=Libre+Baskerville:wght@400;700&family=Special+Elite&display=swap');
  :root { --bg:#111111; --bg2:#1A1A1A; --text:#E8E0D4; --accent:#C9A96E; --muted:#8A7F72;
          --entity:#D4B896; --entity-bg:#1F1B17; --call:#8BAF8E; --call-bg:#141A14;
          --warn:#C97B6E; --warn-bg:#1E1411; --border:#2E2A26; }
  body { font-family: 'Libre Baskerville', serif; background: var(--bg); color: var(--text);
         max-width: 800px; margin: 0 auto; padding: 52px 44px; font-size: 16px; line-height: 1.8; }
  h1 { font-family: 'Playfair Display', serif; font-size: 2.6em; font-weight: 700; color: var(--text);
       letter-spacing: -0.02em; border-bottom: 1px solid var(--accent); padding-bottom: 14px;
       margin-bottom: 8px; }
  h2 { font-family: 'Playfair Display', serif; font-size: 1.4em; font-weight: 700; color: var(--accent);
       font-style: italic; margin: 36px 0 12px; }
  h3 { font-family: 'Special Elite', cursive; font-size: 1.05em; color: var(--text); margin: 22px 0 8px;
       letter-spacing: 0.04em; }
  p { margin: 0 0 16px; }
  .entity-card { background: var(--entity-bg); border: 1px solid var(--border); border-left: 3px solid var(--accent);
                 padding: 14px 20px; margin: 18px 0; }
  .entity-card .entity-name { font-family: 'Playfair Display', serif; font-size: 1.1em; font-style: italic;
                               color: var(--accent); margin-bottom: 4px; }
  .callout { background: var(--call-bg); border: 1px solid #2A3A2A; border-left: 3px solid var(--call);
             padding: 12px 18px; margin: 16px 0; }
  .callout::before { content: "◆ Note"; font-size: 0.7em; font-weight: 700; color: var(--call);
                     display: block; margin-bottom: 4px; letter-spacing: 0.1em; text-transform: uppercase; }
  .warning { background: var(--warn-bg); border: 1px solid #3A2018; border-left: 3px solid var(--warn);
             padding: 12px 18px; margin: 16px 0; }
  .warning::before { content: "⚠ Warning"; font-size: 0.7em; font-weight: 700; color: var(--warn);
                     display: block; margin-bottom: 4px; letter-spacing: 0.1em; text-transform: uppercase; }
  .timeline-event { padding: 7px 0 7px 18px; border-left: 2px solid var(--accent); margin: 7px 0; color: var(--muted); }
  .relationship { font-style: italic; color: var(--muted); margin: 5px 0 5px 14px; }
  blockquote { border-left: 2px solid var(--border); padding: 8px 20px; margin: 16px 0;
               color: var(--muted); font-style: italic; }
  ul, ol { margin: 8px 0 14px 22px; } li { margin-bottom: 5px; } li::marker { color: var(--accent); }
  table { width: 100%; border-collapse: collapse; margin: 16px 0; }
  th { background: var(--bg2); color: var(--accent); font-family: 'Special Elite', cursive;
       font-size: 0.85em; padding: 10px 14px; text-align: left; border-bottom: 1px solid var(--accent); }
  td { padding: 9px 14px; border-bottom: 1px solid var(--border); color: var(--muted); }
  code { color: var(--accent); background: var(--bg2); padding: 2px 5px; font-size: 0.9em; }
  pre { background: var(--bg2); border: 1px solid var(--border); padding: 16px; overflow-x: auto; margin: 14px 0; }
  .doc-meta { font-size: 0.85em; color: var(--muted); margin-bottom: 32px; font-style: italic; }
  hr { border: none; border-top: 1px solid var(--border); margin: 32px 0; }
""",

"newspaper": """
  @import url('https://fonts.googleapis.com/css2?family=UnifrakturMaguntia&family=Libre+Baskerville:ital,wght@0,400;0,700;1,400&family=Source+Sans+3:wght@300;400;600&display=swap');
  :root { --bg:#F5F0E8; --bg2:#EDE8E0; --text:#111111; --accent:#8B0000; --muted:#555;
          --border:#CCCCCC; --entity-bg:#EDE8E0; }
  body { font-family: 'Libre Baskerville', serif; background: var(--bg); color: var(--text);
         max-width: 860px; margin: 0 auto; padding: 40px 44px; font-size: 15px; line-height: 1.7;
         column-gap: 24px; }
  h1 { font-family: 'UnifrakturMaguntia', cursive; font-size: 3.2em; text-align: center;
       border-top: 3px double var(--text); border-bottom: 3px double var(--text);
       padding: 10px 0; margin-bottom: 6px; line-height: 1.1; }
  h2 { font-family: 'Libre Baskerville', serif; font-size: 1.15em; font-weight: 700;
       text-transform: uppercase; letter-spacing: 0.06em; border-top: 2px solid var(--text);
       padding-top: 6px; margin: 32px 0 10px; }
  h3 { font-family: 'Libre Baskerville', serif; font-size: 1.05em; font-weight: 700;
       font-style: italic; margin: 20px 0 6px; }
  p { margin: 0 0 12px; text-align: justify; hyphens: auto; }
  .entity-card { background: var(--entity-bg); border: 1px solid var(--border); padding: 12px 16px; margin: 14px 0; }
  .entity-card .entity-name { font-weight: 700; font-size: 1.05em; }
  .callout { border: 1px solid var(--border); background: var(--bg2); padding: 10px 16px; margin: 14px 0;
             font-style: italic; text-align: center; }
  .callout::before { content: "— Note —"; font-size: 0.75em; font-weight: 700; display: block; margin-bottom: 4px;
                     letter-spacing: 0.08em; font-style: normal; }
  .warning { border: 2px solid var(--accent); padding: 10px 16px; margin: 14px 0; background: #FFF5F5; }
  .warning::before { content: "NOTICE"; font-size: 0.7em; font-weight: 700; color: var(--accent);
                     display: block; margin-bottom: 4px; letter-spacing: 0.1em; }
  .timeline-event { padding: 5px 0 5px 14px; border-left: 2px solid var(--text); margin: 5px 0; font-style: italic; }
  .relationship { color: var(--muted); font-style: italic; margin: 4px 0 4px 10px; }
  blockquote { border-left: 3px solid var(--text); padding: 6px 18px; margin: 14px 0; font-style: italic; }
  ul, ol { margin: 8px 0 12px 20px; } li { margin-bottom: 3px; }
  table { width: 100%; border-collapse: collapse; margin: 14px 0; font-size: 0.9em; }
  th { border-top: 2px solid var(--text); border-bottom: 1px solid var(--text); padding: 8px 12px;
       text-align: left; font-size: 0.8em; text-transform: uppercase; letter-spacing: 0.06em; }
  td { padding: 7px 12px; border-bottom: 1px solid var(--border); }
  .doc-meta { text-align: center; font-size: 0.8em; color: var(--muted); margin-bottom: 28px;
              border-bottom: 1px solid var(--border); padding-bottom: 8px;
              text-transform: uppercase; letter-spacing: 0.06em; }
  hr { border: none; border-top: 1px solid var(--border); margin: 24px 0; }
  code { font-family: monospace; background: var(--bg2); padding: 1px 5px; font-size: 0.9em; }
  pre { background: var(--bg2); border: 1px solid var(--border); padding: 14px; overflow-x: auto; margin: 12px 0; }
""",

"scientific": """
  @import url('https://fonts.googleapis.com/css2?family=Source+Serif+4:ital,wght@0,300;0,400;0,600;1,400&family=Source+Sans+3:wght@300;400;600&family=Source+Code+Pro:wght@400;500&display=swap');
  :root { --bg:#FFFFFF; --bg2:#F7F8FA; --text:#111827; --accent:#1D4ED8; --muted:#6B7280;
          --entity:#7C3AED; --entity-bg:#F5F3FF; --call:#065F46; --call-bg:#ECFDF5;
          --warn:#92400E; --warn-bg:#FFFBEB; --border:#E5E7EB; }
  body { font-family: 'Source Serif 4', serif; background: var(--bg); color: var(--text);
         max-width: 780px; margin: 0 auto; padding: 48px 44px; font-size: 16px; line-height: 1.75; }
  h1 { font-family: 'Source Sans 3', sans-serif; font-size: 1.9em; font-weight: 600; color: var(--text);
       border-bottom: 2px solid var(--accent); padding-bottom: 10px; margin-bottom: 6px; }
  h2 { font-family: 'Source Sans 3', sans-serif; font-size: 1.2em; font-weight: 600; color: var(--text);
       counter-increment: section; margin: 32px 0 10px;
       border-bottom: 1px solid var(--border); padding-bottom: 6px; }
  h2::before { content: counter(section) ". "; color: var(--accent); }
  h3 { font-family: 'Source Sans 3', sans-serif; font-size: 1.05em; font-weight: 600;
       color: var(--muted); margin: 20px 0 6px; }
  body { counter-reset: section; }
  p { margin: 0 0 14px; text-align: justify; }
  .entity-card { background: var(--entity-bg); border: 1px solid #DDD6FE; border-radius: 4px;
                 padding: 12px 18px; margin: 16px 0; }
  .entity-card .entity-name { font-family: 'Source Sans 3', sans-serif; font-weight: 600;
                               color: var(--entity); font-size: 1em; }
  .callout { background: var(--call-bg); border-left: 4px solid var(--call); padding: 12px 16px; margin: 16px 0; }
  .callout::before { content: "Definition"; font-size: 0.72em; font-weight: 700; color: var(--call);
                     display: block; margin-bottom: 4px; letter-spacing: 0.08em; text-transform: uppercase; }
  .warning { background: var(--warn-bg); border-left: 4px solid #D97706; padding: 12px 16px; margin: 16px 0; }
  .warning::before { content: "Caution"; font-size: 0.72em; font-weight: 700; color: var(--warn);
                     display: block; margin-bottom: 4px; letter-spacing: 0.08em; text-transform: uppercase; }
  .timeline-event { padding: 6px 0 6px 16px; border-left: 2px solid var(--accent); margin: 6px 0; font-size: 0.95em; }
  .relationship { color: var(--muted); font-style: italic; margin: 5px 0 5px 12px; font-size: 0.95em; }
  blockquote { border-left: 3px solid var(--border); padding: 6px 18px; margin: 14px 4px;
               color: var(--muted); font-size: 0.95em; }
  ul, ol { margin: 8px 0 14px 20px; } li { margin-bottom: 4px; }
  table { width: 100%; border-collapse: collapse; margin: 16px 0; font-size: 0.9em; }
  th { background: var(--bg2); color: var(--text); font-family: 'Source Sans 3', sans-serif;
       font-weight: 600; padding: 9px 12px; text-align: left; border-bottom: 2px solid var(--border); }
  td { padding: 8px 12px; border-bottom: 1px solid var(--border); }
  code { font-family: 'Source Code Pro', monospace; background: var(--bg2); padding: 2px 5px;
         border-radius: 3px; font-size: 0.88em; }
  pre { font-family: 'Source Code Pro', monospace; background: var(--bg2); border: 1px solid var(--border);
        border-radius: 4px; padding: 14px; overflow-x: auto; margin: 14px 0; }
  .doc-meta { font-family: 'Source Sans 3', sans-serif; font-size: 0.82em; color: var(--muted); margin-bottom: 30px; }
  hr { border: none; border-top: 1px solid var(--border); margin: 28px 0; }
""",

"minimalist": """
  @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500&family=DM+Serif+Display:ital@0;1&display=swap');
  :root { --bg:#FFFFFF; --text:#0A0A0A; --accent:#0A0A0A; --muted:#999;
          --border:#F0F0F0; --border2:#E0E0E0; --entity-bg:#FAFAFA; }
  body { font-family: 'Inter', sans-serif; font-weight: 300; background: var(--bg); color: var(--text);
         max-width: 700px; margin: 0 auto; padding: 80px 40px; font-size: 17px; line-height: 1.8; }
  h1 { font-family: 'DM Serif Display', serif; font-size: 2.8em; color: var(--text);
       font-weight: 400; letter-spacing: -0.02em; margin-bottom: 12px; line-height: 1.1; }
  h2 { font-family: 'Inter', sans-serif; font-size: 0.75em; font-weight: 500; color: var(--muted);
       text-transform: uppercase; letter-spacing: 0.14em; margin: 52px 0 20px; }
  h3 { font-family: 'DM Serif Display', serif; font-size: 1.3em; font-weight: 400;
       font-style: italic; margin: 28px 0 10px; }
  p { margin: 0 0 20px; color: #1A1A1A; }
  .entity-card { background: var(--entity-bg); border: 1px solid var(--border2); padding: 20px 24px; margin: 24px 0; }
  .entity-card .entity-name { font-family: 'DM Serif Display', serif; font-size: 1.15em; margin-bottom: 6px; }
  .callout { border-top: 1px solid var(--border2); border-bottom: 1px solid var(--border2);
             padding: 16px 0; margin: 24px 0; color: var(--muted); font-style: italic; font-size: 0.95em; }
  .callout::before { display: none; }
  .warning { border-left: 2px solid #0A0A0A; padding: 12px 20px; margin: 20px 0; color: var(--muted); font-size: 0.9em; }
  .warning::before { content: "Note —"; font-style: normal; font-weight: 500; color: var(--text);
                     display: inline; margin-right: 5px; }
  .timeline-event { padding: 6px 0; border-bottom: 1px solid var(--border); margin: 0; color: var(--muted); font-size: 0.9em; }
  .relationship { color: var(--muted); font-size: 0.9em; margin: 6px 0; }
  blockquote { border-left: 2px solid var(--border2); padding: 4px 24px; margin: 20px 0;
               color: var(--muted); font-style: italic; font-size: 1.05em; }
  ul, ol { margin: 8px 0 20px 18px; } li { margin-bottom: 6px; color: #1A1A1A; }
  li::marker { color: var(--muted); }
  table { width: 100%; border-collapse: collapse; margin: 20px 0; font-size: 0.9em; }
  th { font-size: 0.7em; text-transform: uppercase; letter-spacing: 0.1em; font-weight: 500;
       color: var(--muted); padding: 8px 0; text-align: left; border-bottom: 1px solid var(--border2); }
  td { padding: 10px 0; border-bottom: 1px solid var(--border); color: #1A1A1A; }
  code { font-size: 0.88em; background: var(--entity-bg); padding: 2px 6px; border-radius: 2px; font-weight: 400; }
  pre { background: var(--entity-bg); padding: 20px; margin: 20px 0; overflow-x: auto; border-radius: 2px; }
  .doc-meta { font-size: 0.8em; color: var(--muted); margin-bottom: 52px; }
  hr { border: none; border-top: 1px solid var(--border); margin: 40px 0; }
""",

"startup": """
  @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:ital,wght@0,300;0,400;0,600;0,700;0,800;1,400&family=Fira+Code:wght@400;500&display=swap');
  :root { --bg:#0F172A; --bg2:#1E293B; --bg3:#334155; --text:#F1F5F9; --accent:#6366F1;
          --accent2:#A78BFA; --muted:#94A3B8; --entity:#38BDF8; --entity-bg:#0C1A2E;
          --call:#34D399; --call-bg:#022C22; --warn:#FB923C; --warn-bg:#1F1005; --border:#334155; }
  body { font-family: 'Plus Jakarta Sans', sans-serif; background: var(--bg); color: var(--text);
         max-width: 880px; margin: 0 auto; padding: 48px 44px; font-size: 15px; line-height: 1.7; }
  h1 { font-size: 2.4em; font-weight: 800; background: linear-gradient(135deg, #6366F1, #A78BFA, #38BDF8);
       -webkit-background-clip: text; -webkit-text-fill-color: transparent; background-clip: text;
       margin-bottom: 8px; letter-spacing: -0.03em; line-height: 1.1; }
  h2 { font-size: 1.1em; font-weight: 700; color: var(--accent2); text-transform: uppercase;
       letter-spacing: 0.08em; margin: 36px 0 12px; display: flex; align-items: center; gap: 8px; }
  h2::before { content: "//"; color: var(--accent); font-size: 0.9em; }
  h3 { font-size: 1.05em; font-weight: 600; color: var(--text); margin: 20px 0 8px; }
  p { margin: 0 0 14px; color: #CBD5E1; }
  .entity-card { background: var(--entity-bg); border: 1px solid #1E3A5F; border-radius: 8px;
                 padding: 16px 20px; margin: 16px 0; position: relative; overflow: hidden; }
  .entity-card::before { content: ''; position: absolute; top: 0; left: 0; right: 0; height: 2px;
                          background: linear-gradient(90deg, var(--entity), var(--accent)); }
  .entity-card .entity-name { font-weight: 700; color: var(--entity); font-size: 1.05em; margin-bottom: 4px; }
  .callout { background: var(--call-bg); border: 1px solid #064E3B; border-radius: 8px;
             padding: 12px 18px; margin: 14px 0; }
  .callout::before { content: "✦ Insight"; font-size: 0.7em; font-weight: 700; color: var(--call);
                     display: block; margin-bottom: 4px; letter-spacing: 0.1em; text-transform: uppercase; }
  .warning { background: var(--warn-bg); border: 1px solid #7C2D12; border-radius: 8px;
             padding: 12px 18px; margin: 14px 0; }
  .warning::before { content: "⚡ Alert"; font-size: 0.7em; font-weight: 700; color: var(--warn);
                     display: block; margin-bottom: 4px; letter-spacing: 0.1em; text-transform: uppercase; }
  .timeline-event { padding: 8px 0 8px 18px; border-left: 2px solid var(--accent); margin: 6px 0; color: var(--muted); }
  .relationship { color: var(--muted); margin: 4px 0 4px 12px; font-size: 0.9em; }
  blockquote { border-left: 3px solid var(--accent); padding: 8px 18px; margin: 14px 0; color: var(--muted); }
  ul, ol { margin: 8px 0 14px 20px; } li { margin-bottom: 5px; color: #CBD5E1; }
  li::marker { color: var(--accent); }
  table { width: 100%; border-collapse: collapse; margin: 14px 0; }
  th { background: var(--bg2); color: var(--accent2); font-weight: 700; font-size: 0.78em;
       text-transform: uppercase; letter-spacing: 0.08em; padding: 10px 14px;
       text-align: left; border-bottom: 1px solid var(--border); }
  td { padding: 9px 14px; border-bottom: 1px solid var(--border); color: var(--muted); }
  code { font-family: 'Fira Code', monospace; color: var(--entity); background: var(--bg2);
         padding: 2px 7px; border-radius: 4px; font-size: 0.88em; }
  pre { font-family: 'Fira Code', monospace; background: var(--bg2); border: 1px solid var(--border);
        border-radius: 8px; padding: 16px; overflow-x: auto; margin: 14px 0; }
  .doc-meta { font-size: 0.82em; color: var(--muted); margin-bottom: 30px; }
  hr { border: none; border-top: 1px solid var(--border); margin: 28px 0; }
""",

"manuscript": """
  @import url('https://fonts.googleapis.com/css2?family=Cormorant+Garamond:ital,wght@0,400;0,500;0,600;1,400;1,500&family=Cormorant+SC:wght@400;500&display=swap');
  :root { --bg:#FAF7F2; --bg2:#F2EDE6; --text:#1C1610; --accent:#5C3D1E; --muted:#8A7060;
          --entity:#3D2B0E; --entity-bg:#EDE4D8; --call:#2D4A2D; --call-bg:#E4EDE4;
          --warn:#5C2D2D; --warn-bg:#EDE4E4; --border:#D4C4B0; }
  body { font-family: 'Cormorant Garamond', serif; background: var(--bg); color: var(--text);
         max-width: 720px; margin: 0 auto; padding: 72px 60px; font-size: 18px; line-height: 1.9; }
  h1 { font-family: 'Cormorant SC', serif; font-size: 2.4em; font-weight: 500; color: var(--text);
       text-align: center; letter-spacing: 0.05em; margin-bottom: 10px;
       border-top: 1px solid var(--border); border-bottom: 1px solid var(--border); padding: 16px 0; }
  h2 { font-family: 'Cormorant SC', serif; font-size: 1.1em; font-weight: 500; color: var(--accent);
       text-align: center; letter-spacing: 0.12em; margin: 48px 0 20px; }
  h3 { font-family: 'Cormorant Garamond', serif; font-size: 1.15em; font-weight: 600;
       font-style: italic; color: var(--text); margin: 28px 0 10px; }
  p { margin: 0 0 0; text-indent: 2em; }
  p + p { margin-top: 0; }
  p:first-of-type, h2 + p, h3 + p, .entity-card + p { text-indent: 0; }
  .entity-card { background: var(--entity-bg); border: 1px solid var(--border); padding: 16px 22px;
                 margin: 24px 0; text-align: center; }
  .entity-card .entity-name { font-family: 'Cormorant SC', serif; font-size: 1.05em;
                               color: var(--entity); margin-bottom: 6px; letter-spacing: 0.06em; }
  .callout { background: var(--call-bg); border: 1px solid #B8CCB8; padding: 14px 20px; margin: 20px 0; font-style: italic; }
  .callout::before { content: "Note — "; font-style: normal; font-weight: 600; color: var(--call); }
  .warning { background: var(--warn-bg); border: 1px solid #CCB8B8; padding: 14px 20px; margin: 20px 0; }
  .warning::before { content: "Caution — "; font-weight: 600; color: var(--warn); }
  .timeline-event { font-style: italic; color: var(--muted); padding: 5px 0 5px 16px;
                    border-left: 1px solid var(--border); margin: 5px 0; }
  .relationship { font-style: italic; color: var(--muted); margin: 6px 0; text-indent: 0; }
  blockquote { margin: 24px 40px; font-style: italic; color: var(--muted); font-size: 1.05em; }
  ul, ol { margin: 10px 0 16px 28px; } li { margin-bottom: 6px; }
  table { width: 100%; border-collapse: collapse; margin: 20px 0; font-size: 0.9em; }
  th { font-family: 'Cormorant SC', serif; font-size: 0.85em; letter-spacing: 0.08em;
       padding: 8px 12px; text-align: left; border-bottom: 1px solid var(--border); color: var(--accent); }
  td { padding: 9px 12px; border-bottom: 1px solid var(--bg2); }
  code { font-family: monospace; font-size: 0.85em; background: var(--bg2); padding: 1px 5px; }
  pre { background: var(--bg2); border: 1px solid var(--border); padding: 16px; overflow-x: auto; margin: 16px 0; font-size: 0.85em; }
  .doc-meta { text-align: center; font-style: italic; color: var(--muted); margin-bottom: 40px; font-size: 0.9em; }
  hr { border: none; text-align: center; margin: 32px 0; color: var(--border); }
  hr::after { content: "· · ·"; font-size: 1.2em; letter-spacing: 0.3em; color: var(--muted); }
""",
}


class HTMLRenderer:
    """Converts a Document model into a complete, self-contained HTML page."""

    def _is_manuscript(self, doc: Document) -> bool:
        """Prose-heavy documents (novels, narrative nonfiction -- almost
        entirely paragraphs/headings, no structured-note block types) read
        far better with book typesetting (indented paragraphs, a fresh page
        per chapter) than the dense note-taking layout the themes are
        designed for."""
        blocks = doc.all_blocks
        if len(blocks) < 20:
            return False
        prose_types = {BlockType.PARAGRAPH, BlockType.HEADING, BlockType.QUOTE, BlockType.DIVIDER}
        prose_count = sum(1 for b in blocks if b.type in prose_types)
        return prose_count / len(blocks) > 0.9

    def render(self, doc: Document, theme: str = "academic", mode: str = "document",
               custom_css: str = "", icon_style: str = "unicode",
               decorate: bool = False, border: bool = False,
               decoration_style: str = "auto", doodle_density: int = None) -> str:
        if icon_style not in ("unicode", "fontawesome", "none"):
            icon_style = "unicode"
        raw_css, body_html, has_doodles = self._get_css_and_body(
            doc, theme, mode, custom_css, icon_style, decorate, doodle_density)

        if decorate or border:
            raw_css += self._decoration_css(has_doodles)
            resolved_style = decorations.resolve_style(decoration_style, doc, theme)
            body_html = self._wrap_page_frame(body_html, decorate, border, resolved_style)

        scoped_css = self._scope_css(raw_css, ".ias-doc")

        fa_link = (
            '<link rel="stylesheet" '
            'href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.1/css/all.min.css">\n'
        ) if icon_style == "fontawesome" else ""

        full_html = (
            "<!DOCTYPE html>\n<html lang=\"en\">\n<head>\n"
            "<meta charset=\"UTF-8\">\n"
            "<meta name=\"viewport\" content=\"width=device-width, initial-scale=1.0\">\n"
            f"<title>{html_lib.escape(doc.title)}</title>\n"
            f"{fa_link}"
            f"<style>\n{raw_css}\n</style>\n"
            "</head>\n<body>\n"
            f"{body_html}\n"
            "</body>\n</html>"
        )

        import json as _json
        fragment = _json.dumps({"css": scoped_css, "html": body_html, "fa": icon_style == "fontawesome"})
        return full_html + "\n<!--IAS_FRAGMENT:" + fragment + ":IAS_FRAGMENT-->"

    # ── Page decoration (margin ornaments + optional border) ──────────
    # Purely decorative, off by default -- meant for lighter, "not so
    # serious" documents. A single ornamental rule (line -- glyph -- line)
    # sits in the top margin and a matching one in the bottom margin, like
    # a classic book fleuron, rather than isolated corner marks. HTML has
    # no real notion of pages, so -- like the border -- this decorates the
    # document as a whole; a paginated PDF export (via the PDF exporter,
    # which renders this same HTML) will only show it once, at the very
    # start and end, rather than repeating on every page.
    def _wrap_page_frame(self, body_html: str, decorate: bool, border: bool,
                          decoration_style: str = "sparkle") -> str:
        classes = ["ias-page-frame"]
        if border:
            classes.append("ias-page-frame-border")
        top_html, bottom_html = "", ""
        if decorate:
            primary, secondary = decorations.DECORATION_SETS.get(
                decoration_style, decorations.DECORATION_SETS[decorations.DEFAULT_SET])
            top_html = (
                f'<div class="ias-margin-ornament ias-margin-top" aria-hidden="true">'
                f'{html_lib.escape(decorations.margin_text(primary))}</div>'
            )
            bottom_html = (
                f'<div class="ias-margin-ornament ias-margin-bottom" aria-hidden="true">'
                f'{html_lib.escape(decorations.margin_text(secondary))}</div>'
            )
        return f'<div class="{" ".join(classes)}">{top_html}{body_html}{bottom_html}</div>'

    def _decoration_css(self, has_doodles: bool = False) -> str:
        side_pad = 120 if has_doodles else 44
        return (
            f"\n.ias-page-frame {{ position: relative; padding: 8px {side_pad}px 26px; }}\n"
            ".ias-page-frame-border { border: 4px double var(--accent, #333); "
            "border-radius: 4px; margin: 8px; padding-top: 28px; }\n"
            ".ias-margin-ornament { text-align: center; font-size: 20px; "
            "letter-spacing: 2px; color: var(--accent, #333); opacity: 0.85; "
            "user-select: none; }\n"
            ".ias-margin-top { margin-bottom: 26px; }\n"
            ".ias-margin-bottom { margin-top: 26px; }\n"
        )

    def _get_css_and_body(self, doc, theme, mode, custom_css, icon_style="unicode", decorate=False, doodle_density=None):
        has_doodles = False
        if theme.startswith("custom:"):
            # Designer CSS is the complete stylesheet — use it alone
            css = (custom_css or THEME_CSS["academic"]) + TASK_LIST_CSS
        else:
            base_css = THEME_CSS.get(theme, THEME_CSS["academic"]) + TASK_LIST_CSS
            if custom_css:
                # Layer the user's CSS on top of the full base theme stylesheet
                # (not just its :root block) so that:
                #  - variable-only overrides (":root { --accent: #e63946; }")
                #    still have the base h1/h2/.entity-card/etc rules around
                #    to consume var(--accent) — otherwise the doc would render
                #    completely unstyled.
                #  - full selector overrides (e.g. "h1 { color: ... }") simply
                #    win the cascade because they come after the base rules.
                css = base_css + "\n" + custom_css
                # Built-in preset themes bake their fonts in as literal
                # font-family values (e.g. h1 { font-family: 'Lora', serif })
                # rather than var(--font-heading) — unlike the Designer's
                # "custom:" stylesheets, which are fully variable-driven. So
                # a person writing ":root { --font-heading: 'Fraunces'; }" in
                # the Custom CSS box (exactly what its own placeholder text
                # suggests) would silently do nothing on a preset theme: the
                # variable is defined but nothing reads it. Detect that case
                # and force the standard heading/body/mono selectors to the
                # requested font, so the override actually takes effect no
                # matter which preset is active.
                font_override_css = self._font_override_from_custom_css(custom_css)
                if font_override_css:
                    css += "\n" + font_override_css
            else:
                css = base_css

            if icon_style != "unicode":
                # Neutralize the CSS-based ::before icon labels baked into every
                # theme (they're plain unicode text baked per-theme) — the actual
                # icon markup is instead rendered inline in Python below so it can
                # switch between unicode / Font Awesome / none uniformly.
                css += (
                    "\n.callout::before, .warning::before { content: none !important; }\n"
                    ".ias-icon-label { font-size: 0.75em; font-weight: 700; "
                    "text-transform: uppercase; letter-spacing: 0.06em; margin-bottom: 4px; "
                    "display: flex; align-items: center; gap: 6px; }\n"
                )

        if mode == "slides":
            body_html = self._render_slides(doc, theme, custom_css=custom_css)
        elif mode == "brief":
            body_html = self._render_brief(doc, theme, custom_css=custom_css)
        else:
            if decorate:
                density = doodle_icons.DEFAULT_DENSITY if doodle_density is None else doodle_density
            else:
                density = 0
            doodles = doodle_icons.find_doodles(doc, density=density)
            body_html = self._render_document(doc, theme, icon_style=icon_style, doodles=doodles)
            has_doodles = bool(doodles)
            if doodles:
                css += self._doodle_css()
            if self._is_manuscript(doc):
                css += (
                    "\nh1 { page-break-before: always !important; break-before: page !important; }"
                    "\nh1:first-of-type { page-break-before: avoid !important; break-before: avoid !important; }"
                    "\np { text-indent: 1.5em !important; margin-top: 0 !important; margin-bottom: 0 !important; }"
                    "\nh1 + p, h2 + p, h3 + p, p.doc-meta { text-indent: 0 !important; }\n"
                )

        return css, body_html, has_doodles

    def _scope_css(self, css, scope):
        import re
        # Extract font URLs — URL may contain semicolons so match by paren not semicolon
        font_urls = []
        for m in re.finditer(r'@import\s+url\(([^)]+)\)', css):
            u = m.group(1).strip().strip("'\"")
            font_urls.append(u)
        # Remove @import lines — match up to closing ); including semicolons inside url()
        css = re.sub(r'@import\s+url\([^)]*\)\s*;', '', css)
        # Scope top-level selectors
        result = []
        depth = 0
        sel_buf = ''
        for ch in css:
            if ch == '{':
                if depth == 0:
                    sel = sel_buf.strip()
                    sel_buf = ''
                    if sel.startswith('@'):
                        result.append(sel + ' {')
                    elif sel:
                        parts = [p.strip() for p in sel.split(',') if p.strip()]
                        scoped = []
                        for p in parts:
                            if p in ('html', 'body', ':root'):
                                scoped.append(scope)
                            elif p.startswith(':root'):
                                scoped.append(scope + p[5:])
                            else:
                                scoped.append(scope + ' ' + p)
                        result.append(', '.join(scoped) + ' {')
                    else:
                        result.append('{')
                    depth = 1
                else:
                    result.append(ch)
                    depth += 1
            elif ch == '}':
                depth = max(0, depth - 1)
                result.append('}')
            else:
                if depth == 0:
                    sel_buf += ch
                else:
                    result.append(ch)
        fc = ('/* FONT_URLS:' + '|'.join(font_urls) + ':FONT_URLS */\n') if font_urls else ''
        return fc + ''.join(result)


    # ── Document mode ────────────────────────────────────────────────
    def _render_document(self, doc: Document, theme: str, icon_style: str = "unicode", doodles: dict = None) -> str:
        doodles = doodles or {}
        parts = []
        parts.append(f'<h1>{html_lib.escape(doc.title)}</h1>')
        if doc.project_type and doc.project_type.value != "Document":
            parts.append(f'<p class="doc-meta">{html_lib.escape(doc.project_type.value)} &mdash; {len(doc.all_blocks)} blocks detected</p>')

        title_norm = doc.title.strip().lower()
        for i, block in enumerate(doc.all_blocks):
            # Skip any heading that exactly duplicates the document title —
            # the <h1> above already renders it, no need to repeat it
            if block.type == BlockType.HEADING and block.content.strip().lower() == title_norm:
                continue
            block_html = self._render_block(block, theme, icon_style)
            if i in doodles:
                block_html = self._wrap_doodle(block_html, doodles[i])
            parts.append(block_html)

        return "\n".join(parts)

    # ── Margin doodles ──────────────────────────────────────────────────
    # Small icons placed next to whichever passage actually mentions that
    # concept (see doodle_icons.find_doodles), not a repeated fixed motif --
    # meant to read like considered marginalia, e.g. in a recipe or a
    # story, rather than clip-art scattered at random. Rendered as inline
    # SVG (stroke="currentColor" in the source icons) so each one inherits
    # the document's theme accent color automatically.
    def _wrap_doodle(self, block_html: str, doodles: list) -> str:
        spans = []
        for doodle in doodles:
            svg = doodle_icons.load_icon_svg(doodle["icon"])
            if not svg:
                continue
            size = doodle["size"]
            svg = svg.replace('width="24"', f'width="{size}"').replace('height="24"', f'height="{size}"')
            # Bolder stroke than Lucide's default 2 -- thin lines at doodle
            # size (and against a busy page background) read as barely
            # visible rather than as a deliberate decoration.
            svg = svg.replace('stroke-width="2"', 'stroke-width="2.5"')
            side = "left" if doodle["side"] == "left" else "right"
            style = f'opacity:{doodle["opacity"]}; transform: rotate({doodle["rotate"]}deg);'
            spans.append(
                f'<span class="ias-doodle ias-doodle-{side}" style="{style}" '
                f'aria-hidden="true">{svg}</span>'
            )
        if not spans:
            return block_html
        return f'<div class="ias-doodle-anchor">{"".join(spans)}{block_html}</div>'

    def _doodle_css(self) -> str:
        return (
            "\n.ias-doodle-anchor { position: relative; }\n"
            ".ias-doodle { position: absolute; top: 0.1em; line-height: 0; "
            "color: var(--accent, #333); pointer-events: none; user-select: none; }\n"
            ".ias-doodle svg { display: block; }\n"
            ".ias-doodle-left { left: -58px; }\n"
            ".ias-doodle-right { right: -58px; }\n"
            "@media (max-width: 760px) { .ias-doodle { display: none; } }\n"
        )

    # ── Slides mode ───────────────────────────────────────────────────
    def _render_slides(self, doc: Document, theme: str, custom_css: str = "") -> str:
        """
        Presentation mode: proper slide deck layout.
        Each H2 section = one slide. Entities/callouts/warnings get visual cards.
        Title slide + content slides + summary slide.
        """
        vars_ = self._vars_from_custom_css(custom_css, theme) if custom_css else self._get_theme_vars(theme)
        bg     = vars_["bg"]
        text   = vars_["text"]
        accent = vars_["accent"]
        accent2= vars_["accent2"]
        border = vars_["border"]
        fh     = vars_["font_heading"]
        fb     = vars_["font_body"]

        slide_css = f"""<style>
* {{ box-sizing: border-box; margin: 0; padding: 0; }}
body {{ background: {bg}; color: {text}; font-family: '{fb}', sans-serif;
        margin: 0; padding: 0; }}
.deck {{ display: flex; flex-direction: column; }}
.slide {{
  min-height: 100vh; padding: 64px 72px;
  display: flex; flex-direction: column; justify-content: center;
  border-bottom: 1px solid {border}; position: relative;
  page-break-after: always;
}}
.slide-num {{
  position: absolute; bottom: 24px; right: 32px;
  font-size: 0.75em; opacity: 0.35; font-family: monospace;
}}
/* Title slide */
.slide-title {{
  align-items: center; text-align: center;
  background: {bg};
}}
.slide-title::before {{
  content: ''; position: absolute; inset: 0;
  background: linear-gradient(135deg, {self._alpha(accent, 0.08)} 0%, transparent 60%);
  pointer-events: none;
}}
.slide-title h1 {{
  font-family: '{fh}', serif; font-size: 3.2em; font-weight: 700;
  color: {text}; line-height: 1.1; letter-spacing: -0.02em;
  border: none; padding: 0; margin-bottom: 16px;
}}
.slide-kicker {{
  font-size: 0.9em; color: {accent}; font-weight: 600;
  letter-spacing: 0.12em; text-transform: uppercase; margin-bottom: 20px;
}}
.slide-type-tag {{
  display: inline-block; padding: 6px 18px;
  border: 1px solid {border}; border-radius: 99px;
  font-size: 0.8em; opacity: 0.6; margin-top: 12px;
}}
/* Content slides */
.slide h2 {{
  font-family: '{fh}', serif; font-size: 1.9em; font-weight: 700;
  color: {accent}; margin-bottom: 28px; border: none; padding: 0;
  letter-spacing: -0.01em; line-height: 1.2;
}}
.slide h3 {{
  font-family: '{fh}', serif; font-size: 1.25em; font-weight: 600;
  color: {text}; margin: 20px 0 8px;
}}
.slide p {{ font-size: 1.05em; line-height: 1.7; margin-bottom: 14px; opacity: 0.9; }}
/* Cards for entities/callouts */
.slide-cards {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 14px; margin-top: 8px; }}
.slide-entity-card {{
  background: {self._alpha(accent, 0.06)}; border: 1px solid {self._alpha(accent, 0.2)};
  border-radius: 8px; padding: 16px 20px;
}}
.slide-entity-card .ename {{
  font-family: '{fh}', serif; font-size: 1.05em; font-weight: 700;
  color: {accent}; margin-bottom: 6px;
}}
.slide-callout {{
  background: {self._alpha(accent, 0.07)}; border-left: 4px solid {accent};
  border-radius: 6px; padding: 14px 18px; margin: 10px 0;
  font-size: 0.95em;
}}
.slide-callout-label {{
  font-size: 0.7em; font-weight: 700; color: {accent}; text-transform: uppercase;
  letter-spacing: 0.09em; margin-bottom: 5px;
}}
.slide-warning {{
  background: rgba(192,57,43,0.07); border-left: 4px solid #C0392B;
  border-radius: 6px; padding: 14px 18px; margin: 10px 0; font-size: 0.95em;
}}
.slide-warning-label {{
  font-size: 0.7em; font-weight: 700; color: #C0392B; text-transform: uppercase;
  letter-spacing: 0.09em; margin-bottom: 5px;
}}
.slide-list {{ list-style: none; padding: 0; margin: 10px 0; }}
.slide-list li {{
  padding: 8px 0 8px 20px; border-bottom: 1px solid {border};
  position: relative; font-size: 1em; line-height: 1.5;
}}
.slide-list li::before {{
  content: ''; position: absolute; left: 0; top: 50%;
  transform: translateY(-50%); width: 6px; height: 6px;
  border-radius: 50%; background: {accent};
}}
.slide-task {{
  font-size: 1em; line-height: 1.6; padding: 6px 0; display: flex; gap: 10px; align-items: baseline;
}}
.slide-task .box {{ color: {accent}; flex-shrink: 0; }}
.slide-task.sub {{ margin-left: 28px; font-size: 0.9em; opacity: 0.85; }}
.slide-task.checked {{ opacity: 0.5; text-decoration: line-through; }}
.slide-timeline {{ display: flex; flex-direction: column; gap: 8px; margin: 10px 0; }}
.slide-te {{
  display: flex; gap: 16px; align-items: baseline;
  padding: 8px 0; border-bottom: 1px solid {border};
}}
.slide-te-year {{
  font-weight: 700; color: {accent2}; font-size: 0.9em;
  white-space: nowrap; min-width: 80px;
}}
.slide-quote {{
  border-left: 3px solid {accent2}; padding: 12px 20px; margin: 16px 0;
  font-style: italic; opacity: 0.75; font-size: 1.05em; line-height: 1.6;
}}
/* Summary slide */
.slide-summary h2 {{ color: {text}; font-size: 1.5em; }}
.summary-grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 20px; margin-top: 20px; }}
.summary-stat {{
  background: {self._alpha(accent, 0.06)}; border: 1px solid {self._alpha(accent, 0.15)};
  border-radius: 8px; padding: 18px; text-align: center;
}}
.summary-stat .stat-val {{
  font-family: '{fh}', serif; font-size: 2.2em; font-weight: 700; color: {accent};
}}
.summary-stat .stat-lbl {{ font-size: 0.8em; opacity: 0.6; margin-top: 4px; }}
</style>"""

        parts = [slide_css, '<div class="deck">']

        # ── Title slide ──────────────────────────────────────────────
        parts.append(f'''<div class="slide slide-title">
  <div class="slide-kicker">{html_lib.escape(doc.project_type.value)}</div>
  <h1>{html_lib.escape(doc.title)}</h1>
  <div class="slide-type-tag">{len(doc.all_blocks)} blocks · {len(doc.sections)} sections</div>
  <div class="slide-num">1</div>
</div>''')

        # ── Content slides (one per H2 section) ─────────────────────
        sections = doc.sections
        slide_n = 2

        for section in sections:
            # Gather all blocks for this section (including subsections)
            all_section_blocks = list(section.blocks)
            for sub in section.subsections:
                all_section_blocks.extend(sub.blocks)

            if not all_section_blocks and not section.subsections:
                continue

            slide_content = []
            slide_content.append(f'<h2>{html_lib.escape(section.title)}</h2>')

            # Collect entities into a card grid
            entity_blocks = [b for b in all_section_blocks if b.type == BlockType.ENTITY]
            other_blocks   = [b for b in all_section_blocks
                              if b.type != BlockType.ENTITY and b.type != BlockType.HEADING]

            if entity_blocks:
                slide_content.append('<div class="slide-cards">')
                for eb in entity_blocks[:6]:
                    # Find paragraphs right after this entity
                    idx = all_section_blocks.index(eb)
                    desc_blocks = []
                    for nb in all_section_blocks[idx+1:idx+4]:
                        if nb.type in (BlockType.PARAGRAPH, BlockType.RELATIONSHIP):
                            desc_blocks.append(nb)
                        else:
                            break
                    desc = " ".join(b.content for b in desc_blocks)[:120]
                    entity_desc = (f'<div style="font-size:0.88em;opacity:0.8;line-height:1.5">'
                                   f'{self._md_inline(html_lib.escape(desc))}</div>') if desc else ""
                    slide_content.append(f'''<div class="slide-entity-card">
  <div class="ename">◆ {self._md_inline(html_lib.escape(eb.content))}</div>
  {entity_desc}
</div>''')
                slide_content.append('</div>')

            # Render other important blocks
            timeline_blocks = []
            rendered_count = 0
            MAX_BLOCKS = 6

            for b in other_blocks:
                if rendered_count >= MAX_BLOCKS:
                    break
                if b.type == BlockType.LIST:
                    items = b.content.split("\n")[:5]
                    slide_content.append('<ul class="slide-list">')
                    for item in items:
                        t = item.lstrip("- ").strip()
                        if t:
                            slide_content.append(f'<li>{self._md_inline(html_lib.escape(t))}</li>')
                    slide_content.append('</ul>')
                    rendered_count += 1
                elif b.type == BlockType.TIMELINE_EVENT:
                    timeline_blocks.append(b)
                elif b.type == BlockType.CALLOUT:
                    slide_content.append(f'<div class="slide-callout"><div class="slide-callout-label">ℹ Note</div>{self._md_inline(html_lib.escape(b.content))}</div>')
                    rendered_count += 1
                elif b.type == BlockType.WARNING:
                    slide_content.append(f'<div class="slide-warning"><div class="slide-warning-label">⚠ Warning</div>{self._md_inline(html_lib.escape(b.content))}</div>')
                    rendered_count += 1
                elif b.type == BlockType.PARAGRAPH and b.importance_score >= 40:
                    slide_content.append(f'<p>{self._md_inline(html_lib.escape(b.content[:200]))}</p>')
                    rendered_count += 1
                elif b.type == BlockType.QUOTE:
                    slide_content.append(f'<div class="slide-quote">"{self._md_inline(html_lib.escape(b.content))}"</div>')
                    rendered_count += 1
                elif b.type == BlockType.TASK:
                    checked = bool(b.metadata.get("checked"))
                    box = "☑" if checked else "☐"
                    row = (f'<div class="slide-task{" checked" if checked else ""}">'
                           f'<span class="box">{box}</span>{self._md_inline(html_lib.escape(b.content))}</div>')
                    subtasks = b.metadata.get("subtasks") or []
                    if subtasks:
                        sub_rows = "".join(
                            f'<div class="slide-task sub{" checked" if s.get("checked") else ""}">'
                            f'<span class="box">{"☑" if s.get("checked") else "☐"}</span>'
                            f'{self._md_inline(html_lib.escape(s["text"]))}</div>'
                            for s in subtasks[:4]
                        )
                        row += sub_rows
                    slide_content.append(row)
                    rendered_count += 1

            if timeline_blocks:
                slide_content.append('<div class="slide-timeline">')
                for tb in timeline_blocks[:6]:
                    # Split "Year NNN: event" pattern. Skip the split
                    # entirely if this block carries a color marker --
                    # {{c:HEXCODE}} contains its own colon, which would
                    # otherwise be mistaken for the year/event separator.
                    if "{{c:" in tb.content:
                        parts_t = [tb.content]
                    else:
                        parts_t = tb.content.split(":", 1)
                    if len(parts_t) == 2:
                        slide_content.append(f'<div class="slide-te"><span class="slide-te-year">{self._md_inline(html_lib.escape(parts_t[0].strip()))}</span><span>{self._md_inline(html_lib.escape(parts_t[1].strip()))}</span></div>')
                    else:
                        slide_content.append(f'<div class="slide-te"><span>{self._md_inline(html_lib.escape(tb.content))}</span></div>')
                slide_content.append('</div>')

            parts.append(f'<div class="slide">\n{"".join(slide_content)}\n<div class="slide-num">{slide_n}</div>\n</div>')
            slide_n += 1

        # ── Summary slide ───────────────────────────────────────────
        entities = doc.get_top_entities(4)
        warnings = doc.get_blocks_by_type(BlockType.WARNING)
        callouts = doc.get_blocks_by_type(BlockType.CALLOUT)
        timelines= doc.get_blocks_by_type(BlockType.TIMELINE_EVENT)

        sum_parts = [f'<div class="slide slide-summary">\n<h2>Summary — {html_lib.escape(doc.title)}</h2>']
        sum_parts.append('<div class="summary-grid">')
        stats = [
            (len(doc.all_blocks), "Total blocks"),
            (len(entities), "Key entities"),
            (len(warnings), "Warnings"),
            (len(callouts), "Callouts"),
            (len(timelines), "Timeline events"),
        ]
        for val, lbl in stats:
            sum_parts.append(f'<div class="summary-stat"><div class="stat-val">{val}</div><div class="stat-lbl">{lbl}</div></div>')
        sum_parts.append('</div>')
        if entities:
            sum_parts.append(f'<p style="margin-top:20px;opacity:0.7;font-size:0.9em">Key entities: {", ".join(html_lib.escape(e.content) for e in entities)}</p>')
        sum_parts.append(f'<div class="slide-num">{slide_n}</div>\n</div>')
        parts.append("".join(sum_parts))
        parts.append('</div>')  # /deck

        return "\n".join(parts)

    def _alpha(self, hex_color: str, alpha: float) -> str:
        """Convert hex to rgba."""
        try:
            h = hex_color.lstrip("#")
            if len(h) == 3: h = "".join(c*2 for c in h)
            r, g, b = int(h[0:2],16), int(h[2:4],16), int(h[4:6],16)
            return f"rgba({r},{g},{b},{alpha})"
        except Exception:
            return f"rgba(0,0,0,{alpha})"

    def _font_override_from_custom_css(self, css: str) -> str:
        """
        If the user's custom CSS declares --font-heading / --font-body /
        --font-mono (in a :root {} block, the natural way to write "just
        change the font"), or a direct body{font-family} / h1{font-family}
        rule, force the theme's actual heading/body/mono selectors to that
        font with !important. Built-in preset themes hardcode their fonts
        as literal values rather than reading these variables, so without
        this the variables would just sit there unused. Returns "" if the
        custom CSS doesn't touch fonts at all, so themes are left untouched
        by default.
        """
        import re
        root_match = re.search(r':root\s*\{([^}]+)\}', css)
        found = {}
        var_names = {
            "font_heading": ["--font-heading", "--font-head", "--heading-font"],
            "font_body": ["--font-body", "--font-base", "--body-font"],
            "font_mono": ["--font-mono", "--mono-font", "--code-font"],
        }
        if root_match:
            root_body = root_match.group(1)
            for key, names in var_names.items():
                for name in names:
                    m = re.search(re.escape(name) + r'\s*:\s*([^;]+);', root_body)
                    if m:
                        val = m.group(1).strip().strip("'\"")
                        if val:
                            found[key] = val
                        break

        # Direct selector overrides win over :root vars, same precedence as
        # the rest of the custom-CSS layering.
        m = re.search(r"body\s*\{[^}]*font-family\s*:\s*'?([^;'\"]+)'?\s*;", css)
        if m:
            found["font_body"] = m.group(1).strip()
        m = re.search(r"h1\s*\{[^}]*font-family\s*:\s*'?([^;'\"]+)'?\s*;", css)
        if m:
            found["font_heading"] = m.group(1).strip()
        m = re.search(r"(?:code|pre)\s*\{[^}]*font-family\s*:\s*'?([^;'\"]+)'?\s*;", css)
        if m:
            found["font_mono"] = m.group(1).strip()

        if not found:
            return ""

        rules = []
        if "font_heading" in found:
            f = found["font_heading"]
            rules.append(
                f"h1, h2, h3, .entity-card .entity-name {{ font-family: '{f}', serif !important; }}"
            )
        if "font_body" in found:
            f = found["font_body"]
            rules.append(f"body {{ font-family: '{f}', sans-serif !important; }}")
        if "font_mono" in found:
            f = found["font_mono"]
            rules.append(f"code, pre {{ font-family: '{f}', monospace !important; }}")
        return "\n".join(rules)

    def _vars_from_custom_css(self, css: str, theme: str) -> dict:
        """Parse designer/user CSS to extract theme vars, falling back to base theme values."""
        import re
        base = self._get_theme_vars(theme)
        if not css:
            return base
        v = dict(base)  # start from base, override with designer/user values

        # ── 1. CSS custom properties in :root { --name: value; } ──────────
        # This is the natural way someone writes "just CSS" to reskin things,
        # e.g. :root { --accent: #e63946; --font-body: 'Fraunces'; }
        root_match = re.search(r':root\s*\{([^}]+)\}', css)
        var_map = {
            "bg": ["--bg", "--background", "--color-bg"],
            "text": ["--text", "--color-text", "--fg"],
            "accent": ["--accent", "--accent1", "--color-accent", "--primary"],
            "accent2": ["--accent2", "--accent-2", "--secondary"],
            "border": ["--border", "--color-border"],
            "font_heading": ["--font-heading", "--font-head", "--heading-font"],
            "font_body": ["--font-body", "--font-base", "--body-font"],
        }
        if root_match:
            root_body = root_match.group(1)
            for key, names in var_map.items():
                for name in names:
                    m = re.search(re.escape(name) + r'\s*:\s*([^;]+);', root_body)
                    if m:
                        val = m.group(1).strip().strip("'\"")
                        if val:
                            v[key] = val
                        break

        def _find(pattern, default=''):
            m = re.search(pattern, css)
            return m.group(1).strip() if m else default

        # ── 2. Direct selector rules — body {...}, h1 {...} etc. ──────────
        # These win over :root vars above since they're explicit overrides.
        bg = _find(r'body\s*\{[^}]*background\s*:\s*(#[A-Fa-f0-9]{3,6})')
        if bg: v['bg'] = bg

        col = _find(r'body\s*\{[^}]*color\s*:\s*(#[A-Fa-f0-9]{3,6})')
        if col: v['text'] = col

        acc = _find(r'h1\s*\{[^}]*color\s*:\s*(#[A-Fa-f0-9]{3,6})')
        if acc: v['accent'] = acc

        acc2 = _find(r'h2\s*\{[^}]*color\s*:\s*(#[A-Fa-f0-9]{3,6})')
        if acc2: v['accent2'] = acc2

        brd = _find(r'hr\s*\{[^}]*border-top\s*:[^#]*(#[A-Fa-f0-9]{3,6})')
        if brd: v['border'] = brd

        fh = _find(r"h1\s*\{[^}]*font-family\s*:\s*'([^']+)'")
        if fh: v['font_heading'] = fh

        fb = _find(r"body\s*\{[^}]*font-family\s*:\s*'([^']+)'")
        if fb: v['font_body'] = fb

        return v

    def _get_theme_vars(self, theme: str) -> dict:
        """Extract key CSS vars from a theme for use in slides/brief."""
        defaults = {
            "academic":   {"bg":"#FAFAFA","text":"#1A1A2E","accent":"#2B4C9B","accent2":"#5D3A8E","border":"#D8DCE8","font_heading":"Lora","font_body":"Source Sans 3"},
            "magazine":   {"bg":"#FFFFFF","text":"#111111","accent":"#E63946","accent2":"#111","border":"#E0E0E0","font_heading":"Bebas Neue","font_body":"Inter"},
            "codex":      {"bg":"#F7F0DC","text":"#2C1810","accent":"#7B4F1E","accent2":"#C4952A","border":"#C8A96A","font_heading":"Cinzel","font_body":"Crimson Text"},
            "corporate":  {"bg":"#F8F9FC","text":"#1A1A2E","accent":"#1E3A5F","accent2":"#2E86AB","border":"#E2E8F0","font_heading":"DM Sans","font_body":"DM Sans"},
            "detective":  {"bg":"#C8B99A","text":"#1A1008","accent":"#8B1A1A","accent2":"#1A3A6A","border":"#8B7355","font_heading":"Oswald","font_body":"Courier Prime"},
            "cyberpunk":  {"bg":"#0A0A12","text":"#C8D8E8","accent":"#00E5FF","accent2":"#FF00AA","border":"#1E3050","font_heading":"Orbitron","font_body":"Share Tech Mono"},
            "noir":       {"bg":"#111111","text":"#E8E0D4","accent":"#C9A96E","accent2":"#D4B896","border":"#2E2A26","font_heading":"Playfair Display","font_body":"Libre Baskerville"},
            "newspaper":  {"bg":"#F5F0E8","text":"#111111","accent":"#8B0000","accent2":"#333","border":"#CCCCCC","font_heading":"Libre Baskerville","font_body":"Libre Baskerville"},
            "scientific": {"bg":"#FFFFFF","text":"#111827","accent":"#1D4ED8","accent2":"#7C3AED","border":"#E5E7EB","font_heading":"Source Sans 3","font_body":"Source Serif 4"},
            "minimalist": {"bg":"#FFFFFF","text":"#0A0A0A","accent":"#0A0A0A","accent2":"#666","border":"#F0F0F0","font_heading":"DM Serif Display","font_body":"Inter"},
            "startup":    {"bg":"#0F172A","text":"#F1F5F9","accent":"#6366F1","accent2":"#38BDF8","border":"#334155","font_heading":"Plus Jakarta Sans","font_body":"Plus Jakarta Sans"},
            "manuscript": {"bg":"#FAF7F2","text":"#1C1610","accent":"#5C3D1E","accent2":"#3D2B0E","border":"#D4C4B0","font_heading":"Cormorant Garamond","font_body":"Cormorant Garamond"},
        }
        return defaults.get(theme, defaults["academic"])

    # ── Brief mode ────────────────────────────────────────────────────
    def _render_brief(self, doc: Document, theme: str, custom_css: str = "") -> str:
        """
        Executive Summary — NotebookLM-quality structured brief.
        Sections:
          1. Title + meta ribbon
          2. TL;DR lead paragraph (highest-importance content)
          3. At-a-glance stat bar
          4. Key themes (top 3 sections distilled to 1-2 sentences each)
          5. Key entities with relationship context
          6. Alerts & critical information
          7. Timeline (if present)
          8. Relationships & connections
          9. Definitions glossary (if present)
         10. Section index / table of contents
        """
        v = self._vars_from_custom_css(custom_css, theme) if custom_css else self._get_theme_vars(theme)
        acc   = v["accent"]
        acc2  = v["accent2"]
        brd   = v["border"]
        bg    = v["bg"]

        # ── helpers ──────────────────────────────────────────────────
        def esc(s): return self._md_inline(html_lib.escape(str(s)))
        def card(content, style=""):
            return (f'<div style="background:{bg};border:1px solid {brd};' +
                    f'border-radius:8px;padding:18px 22px;margin:0 0 14px;{style}">' +
                    content + '</div>')

        def section_head(label, icon=""):
            return (f'<div style="display:flex;align-items:center;gap:8px;' +
                    f'margin:28px 0 12px;border-bottom:2px solid {acc};' +
                    f'padding-bottom:6px;">' +
                    (f'<span style="font-size:1.15em">{icon}</span>' if icon else '') +
                    f'<h2 style="margin:0;font-size:1.05em;letter-spacing:.04em;' +
                    f'text-transform:uppercase;color:{acc}">{label}</h2></div>')

        def pill(text, color=None):
            c = color or acc
            return (f'<span style="display:inline-block;background:{c}18;' +
                    f'color:{c};border:1px solid {c}44;border-radius:20px;' +
                    f'padding:2px 10px;font-size:.78em;font-weight:600;' +
                    f'margin:0 4px 4px 0">{esc(text)}</span>')

        def importance_dot(score):
            pct = min(int(score), 100)
            color = acc if pct >= 70 else (acc2 if pct >= 40 else brd)
            return (f'<span title="Importance: {pct}" style="display:inline-block;' +
                    f'width:8px;height:8px;border-radius:50%;' +
                    f'background:{color};margin-right:6px;vertical-align:middle"></span>')

        # ── gather content ───────────────────────────────────────────
        all_blocks = doc.all_blocks
        entities   = doc.get_top_entities(12)
        warnings   = doc.get_blocks_by_type(BlockType.WARNING)
        callouts   = [b for b in doc.get_critical_blocks(65) if b.type == BlockType.CALLOUT]
        timeline   = doc.get_blocks_by_type(BlockType.TIMELINE_EVENT)
        rels       = doc.get_blocks_by_type(BlockType.RELATIONSHIP)
        defs       = doc.get_blocks_by_type(BlockType.DEFINITION)
        quotes     = [b for b in doc.get_blocks_by_type(BlockType.QUOTE) if b.importance_score >= 40]

        # Sort paragraphs by importance
        ranked_paras = sorted(
            [b for b in all_blocks if b.type in (BlockType.PARAGRAPH, BlockType.CALLOUT)],
            key=lambda b: b.importance_score, reverse=True
        )

        parts = []

        # ── 1. Title + meta ribbon ───────────────────────────────────
        parts.append(
            f'<div style="margin-bottom:8px">' +
            f'<h1 style="margin:0 0 8px;font-size:2em;line-height:1.2">{esc(doc.title)}</h1>' +
            f'<div style="display:flex;flex-wrap:wrap;gap:8px;align-items:center;' +
            f'font-size:.82em;opacity:.7;margin-bottom:4px">' +
            pill(doc.project_type.value, acc) +
            pill("Executive Summary", acc2) +
            pill(f"{len(all_blocks)} blocks") +
            pill(f"{len(entities)} entities") +
            (pill(f"⚠ {len(warnings)} alerts", "#C0392B") if warnings else "") +
            (pill(f"📅 {len(timeline)} events") if timeline else "") +
            f'</div></div>'
        )

        # ── 2. TL;DR ────────────────────────────────────────────────
        if ranked_paras:
            # Take first 3 high-importance blocks for a richer lead
            lead_texts = []
            for b in ranked_paras[:3]:
                t = b.content.strip()
                if t and t not in lead_texts:
                    lead_texts.append(t)
            combined_lead = " ".join(t[:200] for t in lead_texts[:2])[:380]

            parts.append(section_head("TL;DR", "📌"))
            parts.append(
                f'<div style="font-size:1.08em;line-height:1.8;' +
                f'border-left:4px solid {acc};padding:14px 20px;' +
                f'background:{acc}08;border-radius:0 8px 8px 0;' +
                f'margin-bottom:20px;font-style:italic;">' +
                esc(combined_lead) + '</div>'
            )

        # ── 3. At-a-glance stat bar ──────────────────────────────────
        stats = []
        if entities:       stats.append((str(len(entities)), "Entities"))
        if warnings:       stats.append((str(len(warnings)), "Alerts"))
        if timeline:       stats.append((str(len(timeline)), "Timeline Events"))
        if rels:           stats.append((str(len(rels)), "Relationships"))
        if defs:           stats.append((str(len(defs)), "Definitions"))

        if stats:
            stat_items = "".join(
                f'<div style="text-align:center;padding:12px 20px;' +
                f'border-right:1px solid {brd}">' +
                f'<div style="font-size:1.7em;font-weight:800;color:{acc}">{v}</div>' +
                f'<div style="font-size:.76em;opacity:.6;margin-top:2px">{l}</div></div>'
                for v, l in stats
            )
            parts.append(
                f'<div style="display:flex;border:1px solid {brd};' +
                f'border-radius:8px;overflow:hidden;margin:0 0 24px">{stat_items}</div>'
            )

        # ── 4. Key themes (section summaries) ───────────────────────
        section_summaries = []
        for section in doc.sections[:6]:
            sec_blocks = list(section.blocks)
            for sub in section.subsections:
                sec_blocks.extend(sub.blocks)
            # Best paragraph for this section
            best = sorted(
                [b for b in sec_blocks if b.type in (BlockType.PARAGRAPH, BlockType.CALLOUT)],
                key=lambda b: b.importance_score, reverse=True
            )
            summary_text = best[0].content[:220] if best else ""
            # Count entities in section
            sec_ents = [b for b in sec_blocks if b.type == BlockType.ENTITY]
            section_summaries.append({
                "title": section.title,
                "summary": summary_text,
                "entities": [e.content for e in sec_ents[:3]],
                "block_count": len(sec_blocks),
            })

        if section_summaries:
            parts.append(section_head("Key Themes", "🧭"))
            parts.append('<div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(280px,1fr));gap:12px;margin-bottom:8px">')
            for i, s in enumerate(section_summaries):
                accent_for_card = acc if i % 2 == 0 else acc2
                ent_pills = "".join(pill(e, accent_for_card) for e in s["entities"][:3])
                parts.append(
                    f'<div style="border:1px solid {brd};border-top:3px solid {accent_for_card};' +
                    f'border-radius:8px;padding:16px 18px;">' +
                    f'<div style="font-weight:700;font-size:.95em;margin-bottom:6px">{esc(s["title"])}</div>' +
                    (f'<div style="font-size:.88em;line-height:1.6;opacity:.8;margin-bottom:8px">{esc(s["summary"])}</div>' if s["summary"] else '') +
                    (f'<div style="margin-top:6px">{ent_pills}</div>' if ent_pills else '') +
                    '</div>'
                )
            parts.append('</div>')

        # ── 5. Key entities ──────────────────────────────────────────
        if entities:
            parts.append(section_head("Key Entities", "👤"))
            parts.append('<div style="display:flex;flex-direction:column;gap:10px;margin-bottom:4px">')
            for e in entities:
                try:
                    idx = all_blocks.index(e)
                    desc_blocks = [b for b in all_blocks[idx+1:idx+5]
                                   if b.type in (BlockType.PARAGRAPH, BlockType.RELATIONSHIP,
                                                  BlockType.DEFINITION)]
                    desc = " ".join(b.content for b in desc_blocks[:2])[:200]
                    rels_for_e = [b for b in all_blocks[idx+1:idx+8]
                                  if b.type == BlockType.RELATIONSHIP]
                except ValueError:
                    desc = ""
                    rels_for_e = []

                rel_text = ""
                if rels_for_e:
                    rel_text = (
                        f'<div style="font-size:.8em;margin-top:6px;opacity:.65;' +
                        f'border-top:1px dashed {brd};padding-top:6px">' +
                        " · ".join(esc(r.content[:80]) for r in rels_for_e[:2]) +
                        '</div>'
                    )

                imp_pct = min(int(e.importance_score), 100)
                bar_w = imp_pct
                icon = self._entity_icon(e.content)

                parts.append(
                    f'<div style="display:flex;align-items:flex-start;gap:14px;' +
                    f'padding:12px 16px;border:1px solid {brd};' +
                    f'border-radius:8px;position:relative;overflow:hidden">' +
                    f'<div style="position:absolute;bottom:0;left:0;height:3px;' +
                    f'width:{bar_w}%;background:{acc};opacity:.4"></div>' +
                    f'<div style="font-size:1.4em;line-height:1;padding-top:2px">{icon}</div>' +
                    f'<div style="flex:1;min-width:0">' +
                    f'<div style="font-weight:700;font-size:1em;display:flex;' +
                    f'align-items:center;gap:8px">{esc(e.content)}' +
                    importance_dot(e.importance_score) +
                    f'</div>' +
                    (f'<div style="font-size:.87em;opacity:.72;margin-top:4px;line-height:1.55">{esc(desc)}</div>' if desc else '') +
                    rel_text +
                    '</div></div>'
                )
            parts.append('</div>')

        # ── 6. Alerts & critical ─────────────────────────────────────
        if warnings or callouts:
            parts.append(section_head("Alerts &amp; Critical Information", "⚠️"))
            for b in warnings[:5]:
                parts.append(
                    f'<div style="border:1px solid #C0392B44;border-left:4px solid #C0392B;' +
                    f'background:#C0392B0A;border-radius:0 8px 8px 0;' +
                    f'padding:12px 18px;margin-bottom:10px;">' +
                    f'<span style="color:#C0392B;font-weight:700;margin-right:6px">⚠</span>' +
                    esc(b.content) + '</div>'
                )
            for b in callouts[:4]:
                parts.append(
                    f'<div style="border:1px solid {acc2}44;border-left:4px solid {acc2};' +
                    f'background:{acc2}0A;border-radius:0 8px 8px 0;' +
                    f'padding:12px 18px;margin-bottom:10px;">' +
                    esc(b.content) + '</div>'
                )

        # ── 6.5. Action items (tasks) ─────────────────────────────────
        tasks = doc.get_blocks_by_type(BlockType.TASK)
        if tasks:
            done = sum(1 for t in tasks if t.metadata.get("checked"))
            parts.append(section_head(f"Action Items ({done}/{len(tasks)})", "✅"))
            parts.append('<div style="margin-bottom:8px">')
            for t in tasks[:10]:
                checked = bool(t.metadata.get("checked"))
                subtasks = t.metadata.get("subtasks") or []
                sub_done = sum(1 for s in _flatten_subtasks(subtasks) if s.get("checked"))
                sub_total = len(_flatten_subtasks(subtasks))
                sub_note = f' <span style="opacity:.55">({sub_done}/{sub_total} subtasks)</span>' if sub_total else ''
                box = "☑" if checked else "☐"
                parts.append(
                    f'<div style="display:flex;gap:8px;align-items:flex-start;' +
                    f'padding:6px 0;{"opacity:.55;text-decoration:line-through" if checked else ""}">' +
                    f'<span style="color:{acc};flex-shrink:0">{box}</span>' +
                    f'<span>{esc(t.content)}{sub_note}</span></div>'
                )
            parts.append('</div>')

        # ── 7. Notable quote ─────────────────────────────────────────
        if quotes:
            q = quotes[0]
            raw = q.content
            author = ""
            for sep in [" — ", " - ", " ~ "]:
                if sep in raw:
                    raw, author = raw.rsplit(sep, 1)
                    break
            raw = raw.strip(chr(39) + chr(34) + chr(32))
            parts.append(section_head("Notable Quote", "💬"))
            parts.append(
                f'<blockquote style="border-left:4px solid {acc};' +
                f'padding:14px 20px;margin:0 0 20px;' +
                f'background:{acc}06;border-radius:0 8px 8px 0;' +
                f'font-size:1.05em;font-style:italic;line-height:1.75">' +
                f'\u201c{esc(raw)}\u201d' +
                (f'<footer style="font-size:.85em;font-style:normal;' +
                 f'opacity:.7;margin-top:8px">&mdash; {esc(author)}</footer>' if author else '') +
                '</blockquote>'
            )

        # ── 8. Timeline ──────────────────────────────────────────────
        if timeline:
            parts.append(section_head("Timeline", "📅"))
            parts.append('<div style="position:relative;padding-left:24px;margin-bottom:8px">')
            # Vertical line
            parts.append(f'<div style="position:absolute;left:7px;top:4px;' +
                         f'bottom:4px;width:2px;background:{brd}"></div>')
            for i, b in enumerate(timeline[:12]):
                raw = b.content
                split = raw.split(":", 1)
                year_label = split[0].strip() if len(split) == 2 else ""
                event_text = split[1].strip() if len(split) == 2 else raw
                dot_color  = acc if i % 2 == 0 else acc2
                parts.append(
                    f'<div style="position:relative;display:flex;gap:14px;' +
                    f'padding:10px 0;align-items:flex-start">' +
                    f'<div style="position:absolute;left:-20px;top:14px;' +
                    f'width:10px;height:10px;border-radius:50%;' +
                    f'background:{dot_color};border:2px solid {bg}"></div>' +
                    (f'<div style="min-width:80px;font-weight:700;font-size:.85em;' +
                     f'color:{dot_color};white-space:nowrap;padding-top:1px">{esc(year_label)}</div>' if year_label else '') +
                    f'<div style="flex:1;font-size:.9em;line-height:1.55">{esc(event_text)}</div>' +
                    '</div>'
                )
            parts.append('</div>')

        # ── 9. Relationships ─────────────────────────────────────────
        if rels:
            parts.append(section_head("Relationships &amp; Connections", "🔗"))
            parts.append('<div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(300px,1fr));gap:8px;margin-bottom:8px">')
            for r in rels[:10]:
                parts.append(
                    f'<div style="font-size:.88em;line-height:1.55;' +
                    f'padding:10px 14px;border:1px solid {brd};' +
                    f'border-radius:6px;display:flex;gap:8px;align-items:flex-start">' +
                    f'<span style="color:{acc};font-size:1.1em;flex-shrink:0">↔</span>' +
                    f'<span>{esc(r.content[:160])}</span></div>'
                )
            parts.append('</div>')

        # ── 10. Definitions glossary ──────────────────────────────────
        if defs:
            parts.append(section_head("Definitions", "📖"))
            parts.append('<dl style="display:grid;grid-template-columns:auto 1fr;' +
                         'gap:4px 16px;margin:0 0 8px">')
            for d in defs[:12]:
                # Skip the split if a color marker is present -- {{c:HEXCODE}}
                # contains its own colon, which would otherwise be mistaken
                # for the term/definition separator.
                if ":" in d.content and "{{c:" not in d.content:
                    term, defn = d.content.split(":", 1)
                    parts.append(
                        f'<dt style="font-weight:700;font-size:.9em;' +
                        f'color:{acc};white-space:nowrap;padding:4px 0">{esc(term.strip())}</dt>' +
                        f'<dd style="font-size:.9em;line-height:1.55;margin:0;' +
                        f'padding:4px 0;border-bottom:1px solid {brd}44">{esc(defn.strip())}</dd>'
                    )
                else:
                    parts.append(
                        f'<dt style="grid-column:1/-1;font-size:.9em;' +
                        f'padding:4px 0;border-bottom:1px solid {brd}44">{esc(d.content)}</dt>'
                    )
            parts.append('</dl>')

        # ── 11. Section index ─────────────────────────────────────────
        if doc.sections:
            parts.append(section_head("Contents", "🗂️"))
            parts.append('<div style="columns:2;gap:20px;margin-bottom:8px">')
            for i, section in enumerate(doc.sections):
                sub_names = [s.title for s in section.subsections[:4]]
                all_sec_blocks = list(section.blocks)
                for sub in section.subsections:
                    all_sec_blocks.extend(sub.blocks)
                count = len(all_sec_blocks)
                sec_ents = [b for b in all_sec_blocks if b.type == BlockType.ENTITY]
                ent_names = [e.content for e in sec_ents[:3]]
                num_color = acc if i % 2 == 0 else acc2

                parts.append(
                    f'<div style="break-inside:avoid;margin-bottom:12px;' +
                    f'padding:10px 14px;border:1px solid {brd};' +
                    f'border-radius:6px">' +
                    f'<div style="display:flex;align-items:center;' +
                    f'gap:8px;margin-bottom:4px">' +
                    f'<span style="background:{num_color};color:white;' +
                    f'border-radius:50%;width:20px;height:20px;font-size:.75em;' +
                    f'font-weight:700;display:flex;align-items:center;' +
                    f'justify-content:center;flex-shrink:0">{i+1}</span>' +
                    f'<span style="font-weight:700;font-size:.95em">{esc(section.title)}</span>' +
                    f'<span style="font-size:.75em;opacity:.5;margin-left:auto">{count} blocks</span>' +
                    '</div>' +
                    ('<div style="font-size:.78em;opacity:.55;line-height:1.5;margin-left:28px">' +
                     ", ".join(esc(s) for s in sub_names) + '</div>' if sub_names else '') +
                    ('<div style="margin-top:6px;margin-left:28px">' +
                     "".join(pill(n, num_color) for n in ent_names) + '</div>' if ent_names else '') +
                    '</div>'
                )
            parts.append('</div>')

        return "\n".join(parts)


    # ── Block renderer ────────────────────────────────────────────────
    def _render_block(self, block: Block, theme: str, icon_style: str = "unicode") -> str:
        if block.type == BlockType.IMAGE:
            return self._render_image_block(block)

        c = self._md_inline(html_lib.escape(block.content))
        imp = block.importance_score
        imp_class = "importance-high" if imp >= 70 else "importance-med" if imp >= 40 else ""

        if block.type == BlockType.HEADING:
            level = min(max(block.level, 1), 6)
            return f'<h{level}>{c}</h{level}>'

        elif block.type == BlockType.PARAGRAPH:
            return f'<p class="{imp_class}">{c}</p>'

        elif block.type == BlockType.ENTITY:
            icon = self._entity_icon(block.content, icon_style)
            icon_html = f'{icon} ' if icon else ''
            # "entity" alias alongside "entity-card" so custom CSS can target
            # either name — .entity-card is the theme-internal name, .entity
            # is the shorter, more guessable name most people write by hand.
            return (f'<div class="entity-card entity {imp_class}">'
                    f'<div class="entity-name">{icon_html}{c}</div>'
                    f'</div>')

        elif block.type == BlockType.CALLOUT:
            label = self._icon_label("callout", "Note", icon_style)
            return f'<div class="callout {imp_class}">{label}{c}</div>'

        elif block.type == BlockType.WARNING:
            label = self._icon_label("warning", "Warning", icon_style)
            return f'<div class="warning {imp_class}">{label}{c}</div>'

        elif block.type == BlockType.TIMELINE_EVENT:
            # "timeline" alias alongside "timeline-event" for the same reason
            return f'<div class="timeline-event timeline">{c}</div>'

        elif block.type == BlockType.TASK:
            checked = bool(block.metadata.get("checked"))
            subtasks = block.metadata.get("subtasks") or []
            return (f'<div class="task-item {imp_class}">'
                    f'{self._render_task_node(block.content, checked, subtasks)}'
                    f'</div>')

        elif block.type == BlockType.RELATIONSHIP:
            return f'<p class="relationship">{c}</p>'

        elif block.type == BlockType.DEFINITION:
            return f'<div class="definition">{c}</div>'

        elif block.type == BlockType.QUOTE:
            return f'<blockquote>{c}</blockquote>'

        elif block.type == BlockType.CODE:
            lang = block.metadata.get("language", "")
            return f'<pre><code class="language-{lang}">{html_lib.escape(block.content)}</code></pre>'

        elif block.type == BlockType.LIST:
            items = block.content.split("\n")
            li_html = "".join(f'<li>{self._md_inline(html_lib.escape(item.strip()))}</li>'
                              for item in items if item.strip())
            return f'<ul>{li_html}</ul>'

        elif block.type == BlockType.TABLE:
            return self._render_table(block.content)

        elif block.type == BlockType.REFERENCE:
            return f'<p class="reference" style="font-size:0.88em;opacity:0.75;">↗ {c}</p>'

        elif block.type == BlockType.DIVIDER:
            return '<hr>'

        return f'<p>{c}</p>'

    def _resolve_image(self, block: Block):
        """Extract (src, alt, caption) from an IMAGE block regardless of which
        parser produced it: docx_parser stores the resolved caption directly
        in `content` with the data URI in metadata['src']; markdown_parser
        (and anything reconstructed via pipeline._blocks_to_markdown) stores
        the src in `content` with an explicit metadata['caption']/['alt'].
        Falls back gracefully so a block missing one or the other still
        renders something reasonable instead of breaking."""
        meta = block.metadata or {}
        src = meta.get("src") or block.content or ""
        alt = meta.get("alt") or ""
        caption = meta.get("caption") or ""
        # docx_parser convention: block.content IS the caption, not the src
        if block.content and block.content != src and not caption:
            caption = block.content
        if not alt:
            alt = caption or "Image"
        return src, alt, caption

    def _render_image_block(self, block: Block) -> str:
        src, alt, caption = self._resolve_image(block)
        if not src:
            return ""
        ocr_text = (block.metadata or {}).get("ocr_text", "").strip()
        size_class = ""
        hint = (caption + " " + alt).lower()
        if any(w in hint for w in ("icon", "logo", "thumbnail")):
            size_class = " ias-figure-small"
        elif any(w in hint for w in ("diagram", "chart", "screenshot", "panorama", "map")):
            size_class = " ias-figure-wide"
        cap_html = f'<figcaption>{self._md_inline(html_lib.escape(caption))}</figcaption>' if caption else ""
        ocr_html = ""
        if ocr_text:
            ocr_html = (
                '<details class="ias-figure-ocr"><summary>Text in image</summary>'
                f'<div>{html_lib.escape(ocr_text)}</div></details>'
            )
        return (
            f'<figure class="ias-figure{size_class}">'
            f'<img src="{html_lib.escape(src, quote=True)}" alt="{html_lib.escape(alt, quote=True)}" loading="lazy">'
            f'{cap_html}{ocr_html}'
            f'</figure>'
        )

    def _md_inline(self, text: str) -> str:
        """Process inline markdown: **bold**, *italic*, `code`, and
        {{c:HEXCOLOR}}...{{/c}} (an inline color marker emitted by
        docx_parser.py for runs that were deliberately colored in the
        source document -- e.g. a script's color-coded speaker labels --
        so that per-run color survives import instead of collapsing to
        one flat text color). DOTALL so a span can contain an embedded
        newline (e.g. a manual line break inside a bold run from a Word
        doc) without silently failing to match and leaving literal
        ** / * / ` in the rendered text."""
        text = re.sub(
            r'\{\{c:([0-9A-Fa-f]{6})\}\}(.+?)\{\{/c\}\}',
            r'<span style="color:#\1">\2</span>', text, flags=re.DOTALL
        )
        text = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', text, flags=re.DOTALL)
        text = re.sub(r'\*(.+?)\*', r'<em>\1</em>', text, flags=re.DOTALL)
        text = re.sub(r'`(.+?)`', r'<code>\1</code>', text, flags=re.DOTALL)
        return text

    def _render_table(self, raw: str) -> str:
        rows = [r for r in raw.strip().splitlines() if r.strip()]
        if not rows:
            return ""
        html_parts = ['<table>']
        for i, row in enumerate(rows):
            cells = [c.strip() for c in row.strip("|").split("|")]
            if i == 0:
                html_parts.append('<thead><tr>' +
                    "".join(f'<th>{html_lib.escape(c)}</th>' for c in cells) +
                    '</tr></thead><tbody>')
            else:
                html_parts.append('<tr>' +
                    "".join(f'<td>{html_lib.escape(c)}</td>' for c in cells) +
                    '</tr>')
        html_parts.append('</tbody></table>')
        return "\n".join(html_parts)

    def _render_task_node(self, text: str, checked: bool, subtasks: list) -> str:
        """Recursively render a task and any nested subtasks as a checklist."""
        state_class = "checked" if checked else ""
        checked_attr = " checked" if checked else ""
        label = self._md_inline(html_lib.escape(text))
        html = (f'<label class="task-row {state_class}">'
                f'<input type="checkbox" disabled{checked_attr}>'
                f'<span>{label}</span></label>')
        if subtasks:
            children = "".join(
                f'<li>{self._render_task_node(st["text"], bool(st.get("checked")), st.get("subtasks") or [])}</li>'
                for st in subtasks
            )
            html += f'<ul class="task-subtasks">{children}</ul>'
        return html

    def _entity_icon(self, name: str, icon_style: str = "unicode") -> str:
        """Heuristic icon based on common entity types."""
        if icon_style == "none":
            return ""

        n = name.lower()
        if icon_style == "fontawesome":
            if any(w in n for w in ["king", "queen", "prince", "princess", "lord", "duke", "earl"]):
                return '<i class="fa-solid fa-chess-king"></i>'
            if any(w in n for w in ["city", "town", "village", "kingdom", "empire", "palace", "castle"]):
                return '<i class="fa-solid fa-chess-rook"></i>'
            if any(w in n for w in ["mountain", "river", "forest", "sea", "ocean", "plain"]):
                return '<i class="fa-solid fa-map"></i>'
            if any(w in n for w in ["guild", "order", "faction", "clan", "tribe", "house"]):
                return '<i class="fa-solid fa-shield-halved"></i>'
            return '<i class="fa-solid fa-diamond"></i>'

        # default: unicode
        if any(w in n for w in ["king", "queen", "prince", "princess", "lord", "duke", "earl"]):
            return "♔"
        if any(w in n for w in ["city", "town", "village", "kingdom", "empire", "palace", "castle"]):
            return "🏰"
        if any(w in n for w in ["mountain", "river", "forest", "sea", "ocean", "plain"]):
            return "🗺"
        if any(w in n for w in ["guild", "order", "faction", "clan", "tribe", "house"]):
            return "⚔"
        return "◆"

    def _icon_label(self, kind: str, text: str, icon_style: str) -> str:
        """
        Inline label markup for callout/warning blocks. Only used when
        icon_style isn't 'unicode' — the default unicode look comes from the
        theme's own CSS ::before rule and is left untouched for zero regression.
        """
        if icon_style == "unicode":
            return ""
        if icon_style == "none":
            return ""
        # fontawesome
        fa_icon = "fa-circle-info" if kind == "callout" else "fa-triangle-exclamation"
        return f'<div class="ias-icon-label"><i class="fa-solid {fa_icon}"></i>{html_lib.escape(text)}</div>'

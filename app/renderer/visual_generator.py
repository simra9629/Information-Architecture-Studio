"""
Visual Generator
----------------
Produces themed placeholder images (PNG bytes via matplotlib) for PPTX slides.
Each image is generated procedurally — no external assets required.

Image types:
  abstract_geo   — geometric shapes composition (default)
  icon_cluster   — large central icon with orbiting mini-icons
  wave_pattern   — flowing wave / organic background
  grid_pattern   — structured dot/grid pattern
  data_glyph     — bar/scatter glyph that feels like a chart
  topic_art      — keyword-driven abstract art
"""

import io
import math
import hashlib
import random
from typing import Dict, Tuple


def _seed(text: str) -> int:
    return int(hashlib.md5(text.encode()).hexdigest()[:8], 16)


def _hex_to_rgb_f(h: str) -> Tuple[float, float, float]:
    h = h.lstrip("#").upper().ljust(6, "0")[:6]
    return (int(h[0:2], 16) / 255, int(h[2:4], 16) / 255, int(h[4:6], 16) / 255)


def _lighten(h: str, amt: float) -> Tuple[float, float, float]:
    r, g, b = _hex_to_rgb_f(h)
    return (min(1, r + (1 - r) * amt), min(1, g + (1 - g) * amt), min(1, b + (1 - b) * amt))


def _alpha(rgb: Tuple, a: float) -> Tuple:
    return (*rgb, a)


def generate(
    visual_type: str,
    topic_title: str,
    pal: Dict,
    width_in: float = 5.5,
    height_in: float = 6.5,
    seed_extra: str = "",
) -> bytes:
    """Return PNG bytes for the requested visual type."""
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        import numpy as np

        rng = random.Random(_seed(topic_title + seed_extra))
        np.random.seed(_seed(topic_title + seed_extra) % (2**31))

        P   = pal["primary"]
        S   = pal["secondary"]
        A   = pal["accent"]
        BG  = pal["bg"]

        Pr  = _hex_to_rgb_f(P)
        Sr  = _hex_to_rgb_f(S)
        Ar  = _hex_to_rgb_f(A)
        BGr = _hex_to_rgb_f(BG)

        fig, ax = plt.subplots(figsize=(width_in, height_in), facecolor=BGr)
        ax.set_facecolor(BGr)
        ax.set_xlim(0, 10)
        ax.set_ylim(0, 10)
        ax.axis("off")
        ax.set_aspect("equal")

        fn = {
            "abstract_geo": _draw_abstract_geo,
            "icon_cluster":  _draw_icon_cluster,
            "wave_pattern":  _draw_wave_pattern,
            "grid_pattern":  _draw_grid_pattern,
            "data_glyph":    _draw_data_glyph,
            "topic_art":     _draw_topic_art,
        }.get(visual_type, _draw_abstract_geo)

        fn(ax, Pr, Sr, Ar, BGr, topic_title, rng)

        # Subtle watermark label
        ax.text(5, 0.35, topic_title[:40], ha="center", va="center",
                fontsize=7, color=(*Pr[:3], 0.22), style="italic")

        plt.tight_layout(pad=0)
        buf = io.BytesIO()
        plt.savefig(buf, format="png", dpi=144, bbox_inches="tight",
                    facecolor=BGr, transparent=False)
        plt.close(fig)
        return buf.getvalue()

    except Exception:
        return b""


# ── Drawing functions ─────────────────────────────────────────────────────────

def _draw_abstract_geo(ax, P, S, A, BG, title, rng):
    """Overlapping translucent circles and polygons."""
    import matplotlib.patches as mpatches

    colors = [P, S, A, _lighten("".join(f"{int(c*255):02X}" for c in P[:3]), 0.4)]

    # Large background circle
    ax.add_patch(mpatches.Circle((5, 5.5), 3.8, color=(*P, 0.07), zorder=1))

    # Medium circles
    for i in range(5):
        cx  = rng.uniform(1.5, 8.5)
        cy  = rng.uniform(1.5, 8.5)
        r   = rng.uniform(0.8, 2.4)
        col = colors[i % len(colors)]
        alpha = rng.uniform(0.08, 0.18)
        ax.add_patch(mpatches.Circle((cx, cy), r, color=(*col, alpha), zorder=2))

    # Polygons (triangles, hexagons)
    for i in range(4):
        cx   = rng.uniform(1, 9)
        cy   = rng.uniform(1, 9)
        n    = rng.choice([3, 4, 6])
        r    = rng.uniform(0.6, 1.8)
        rot  = rng.uniform(0, math.pi)
        col  = colors[i % len(colors)]
        alpha= rng.uniform(0.10, 0.22)
        pts  = [(cx + r * math.cos(2 * math.pi * k / n + rot),
                 cy + r * math.sin(2 * math.pi * k / n + rot))
                for k in range(n)]
        poly = mpatches.Polygon(pts, closed=True, color=(*col, alpha), zorder=3)
        ax.add_patch(poly)

    # Accent dots
    for i in range(8):
        cx  = rng.uniform(0.5, 9.5)
        cy  = rng.uniform(0.5, 9.5)
        r   = rng.uniform(0.06, 0.18)
        col = A if i % 3 == 0 else P
        ax.add_patch(mpatches.Circle((cx, cy), r, color=(*col, 0.55), zorder=5))

    # Two bold accent lines
    for i in range(2):
        x1, y1 = rng.uniform(0, 3), rng.uniform(2, 8)
        x2, y2 = rng.uniform(7, 10), rng.uniform(2, 8)
        ax.plot([x1, x2], [y1, y2], color=(*A, 0.18), linewidth=1.2, zorder=4)


def _draw_icon_cluster(ax, P, S, A, BG, title, rng):
    """Central large icon + radiating accent dots."""
    import matplotlib.patches as mpatches

    # Central glow
    for r, alpha in [(3.5, 0.05), (2.5, 0.08), (1.5, 0.12), (0.9, 0.18)]:
        ax.add_patch(mpatches.Circle((5, 5), r, color=(*P, alpha), zorder=1))

    # Central shape (large hexagon)
    n = 6
    r = 2.1
    pts = [(5 + r * math.cos(math.pi / 2 + 2 * math.pi * k / n),
            5 + r * math.sin(math.pi / 2 + 2 * math.pi * k / n))
           for k in range(n)]
    ax.add_patch(mpatches.Polygon(pts, closed=True, facecolor=(*P, 0.18), zorder=2,
                                   linewidth=1.5, edgecolor=(*P, 0.5), fill=True))

    # Inner shape
    r2 = 1.1
    pts2 = [(5 + r2 * math.cos(math.pi / 2 + 2 * math.pi * k / n),
             5 + r2 * math.sin(math.pi / 2 + 2 * math.pi * k / n))
            for k in range(n)]
    ax.add_patch(mpatches.Polygon(pts2, closed=True, color=(*A, 0.30), zorder=3))

    # Orbiting dots
    for i in range(8):
        angle = 2 * math.pi * i / 8 + rng.uniform(-0.2, 0.2)
        dist  = rng.uniform(3.0, 4.2)
        cx    = 5 + dist * math.cos(angle)
        cy    = 5 + dist * math.sin(angle)
        r     = rng.uniform(0.15, 0.35)
        col   = A if i % 2 == 0 else S
        ax.add_patch(mpatches.Circle((cx, cy), r, color=(*col, 0.45), zorder=4))
        # Line to center
        ax.plot([5, cx], [5, cy], color=(*P, 0.10), linewidth=0.8, zorder=2)

    # Corner accents
    for (cx, cy) in [(0.8, 0.8), (9.2, 0.8), (0.8, 9.2), (9.2, 9.2)]:
        ax.add_patch(mpatches.Circle((cx, cy), 0.4, color=(*S, 0.25), zorder=3))


def _draw_wave_pattern(ax, P, S, A, BG, title, rng):
    """Flowing sine waves stacked vertically."""
    import numpy as np
    import matplotlib.patches as mpatches

    x = np.linspace(0, 10, 300)
    colors = [(*P, 0.12), (*S, 0.10), (*A, 0.14), (*P, 0.08)]

    for i, col in enumerate(colors):
        freq  = rng.uniform(0.5, 1.5)
        phase = rng.uniform(0, math.pi * 2)
        amp   = rng.uniform(0.4, 1.0)
        base  = 2.5 + i * 1.7
        y     = base + amp * np.sin(freq * x + phase)
        y2    = base + amp * 1.4 * np.sin(freq * x * 0.7 + phase + 0.5)
        ax.fill_between(x, y, y2, color=col, zorder=i + 1)
        line_col = P if i % 2 == 0 else S
        ax.plot(x, y, color=(*line_col, 0.25), linewidth=0.8)

    # Accent dots along top wave
    for i in range(12):
        xp = rng.uniform(0.5, 9.5)
        yp = rng.uniform(5, 9)
        ax.add_patch(mpatches.Circle((xp, yp), rng.uniform(0.04, 0.12),
                                      color=(*A, rng.uniform(0.3, 0.6))))


def _draw_grid_pattern(ax, P, S, A, BG, title, rng):
    """Structured dot grid with highlighted cells."""
    import matplotlib.patches as mpatches

    cols, rows = 10, 10
    for r in range(rows):
        for c in range(cols):
            cx = 0.5 + c
            cy = 0.5 + r
            seed_val = (r * cols + c + _seed(title)) % 17
            if seed_val < 2:
                col, alpha, rad = A, 0.55, 0.22
            elif seed_val < 5:
                col, alpha, rad = P, 0.30, 0.15
            elif seed_val < 9:
                col, alpha, rad = S, 0.15, 0.10
            else:
                col, alpha, rad = P, 0.06, 0.06
            ax.add_patch(mpatches.Circle((cx, cy), rad, color=(*col, alpha), zorder=2))

    # Connecting lines between highlighted dots
    highlights = [(0.5 + c, 0.5 + r) for r in range(rows) for c in range(cols)
                  if (r * cols + c + _seed(title)) % 17 < 2][:6]
    for i in range(len(highlights) - 1):
        x1, y1 = highlights[i]
        x2, y2 = highlights[i + 1]
        ax.plot([x1, x2], [y1, y2], color=(*A, 0.22), linewidth=0.9, zorder=1)

    # Large faint square
    sq = mpatches.Polygon([(2, 2), (8, 2), (8, 8), (2, 8)], closed=True,
                           fill=False, edgecolor=(*P, 0.10), linewidth=1.5, zorder=3)
    ax.add_patch(sq)


def _draw_data_glyph(ax, P, S, A, BG, title, rng):
    """Abstract data glyph — looks like a dashboard widget."""
    import numpy as np
    import matplotlib.patches as mpatches

    # Faint background card
    ax.add_patch(mpatches.FancyBboxPatch((0.6, 0.6), 8.8, 8.8,
                 boxstyle="round,pad=0.1", color=(*P, 0.06), zorder=1))

    # Bar chart glyph (bottom half)
    n_bars = rng.randint(5, 8)
    bar_w  = 6.5 / n_bars
    for i in range(n_bars):
        h    = rng.uniform(1.0, 4.5)
        x    = 1.8 + i * bar_w
        col  = P if i % 2 == 0 else S
        alpha= 0.35 if i % 2 == 0 else 0.25
        ax.add_patch(mpatches.Rectangle((x, 1.0), bar_w * 0.72, h,
                     color=(*col, alpha), zorder=2))
        # Accent cap
        ax.add_patch(mpatches.Rectangle((x, 1.0 + h - 0.12), bar_w * 0.72, 0.12,
                     color=(*A, 0.6), zorder=3))

    # Line chart overlay (top)
    x_pts = np.linspace(1.8, 8.3, 12)
    y_pts = np.array([rng.uniform(5.5, 8.5) for _ in range(12)])
    # Smooth
    from scipy.ndimage import gaussian_filter1d
    try:
        y_smooth = gaussian_filter1d(y_pts, sigma=1.5)
    except Exception:
        y_smooth = y_pts
    ax.plot(x_pts, y_smooth, color=(*A, 0.75), linewidth=2.0, zorder=5)
    ax.fill_between(x_pts, 5.2, y_smooth, color=(*A, 0.08), zorder=4)

    # Dots on line
    for xp, yp in zip(x_pts[::3], y_smooth[::3]):
        ax.add_patch(mpatches.Circle((xp, yp), 0.15, color=(*A, 0.85), zorder=6))

    # Axis lines
    ax.plot([1.6, 8.5], [1.0, 1.0], color=(*P, 0.20), linewidth=0.8)
    ax.plot([1.6, 1.6], [1.0, 9.0], color=(*P, 0.20), linewidth=0.8)


def _draw_topic_art(ax, P, S, A, BG, title, rng):
    """Abstract composition inspired by the topic title's character."""
    import matplotlib.patches as mpatches

    # Use title length and char codes to vary shape
    char_sum = sum(ord(c) for c in title) % 4

    if char_sum == 0:
        _draw_abstract_geo(ax, P, S, A, BG, title, rng)
    elif char_sum == 1:
        _draw_wave_pattern(ax, P, S, A, BG, title, rng)
    elif char_sum == 2:
        _draw_grid_pattern(ax, P, S, A, BG, title, rng)
    else:
        _draw_icon_cluster(ax, P, S, A, BG, title, rng)

    # Extra: floating title-character circles
    for i, ch in enumerate(title.upper()[:6]):
        angle = 2 * math.pi * i / 6
        cx    = 5 + 3.5 * math.cos(angle)
        cy    = 5 + 3.5 * math.sin(angle)
        col   = P if i % 2 == 0 else A
        ax.add_patch(mpatches.Circle((cx, cy), 0.28, color=(*col, 0.25), zorder=8))

"""
PDF Import — Layout-Aware Text Reconstruction
-----------------------------------------------
Plain `pypdf` text extraction is unusable for prose PDFs (novels,
narrative nonfiction) because it just concatenates every visual line with
a newline. Print books don't use blank lines between paragraphs -- they
use first-line indentation instead -- so a naive dump turns every
wrapped line into what looks like its own tiny "paragraph," which is
exactly what confuses downstream heading/entity/quote detection.

This module instead reads each word's position and font size (via
pdfplumber) and reconstructs the document the way a human would read it:

  * Paragraph breaks are inferred from first-line indentation, not from
    blank lines that don't exist in the source.
  * Chapter/section titles are detected by font size (meaningfully larger
    than body text) and promoted to real "# " headings.
  * Drop caps -- a chapter's oversized decorative first letter, extracted
    as its own tiny "word" (e.g. "I" + "t was" instead of "It was") --
    are merged back into the word they belong to.
  * Line-end hyphenation ("hyphen-\\nated") is undone.
  * Running footer page numbers are detected and stripped, including
    pages that consist of nothing but a folio number.
  * Two-column layouts (papers, magazines) are detected per page and
    reconstructed in real reading order -- straight down the left column,
    then straight down the right -- instead of interleaving both columns'
    text by raw vertical position, which previously scrambled every
    two-column page into unrelated sentences spliced together.

Falls back to pypdf's plain extraction (tabs coerced to spaces) if
pdfplumber isn't installed or the layout pass fails outright.
"""
import re
import io
from collections import Counter

HEADING_SIZE_RATIO = 1.3   # word >= 1.3x body size, len > 2 chars -> heading
DROPCAP_SIZE_RATIO = 1.6   # word >= 1.6x body size, len <= 2 chars -> drop cap
FOOTER_GAP_RATIO = 1.6     # vertical gap before a trailing number > 1.6x normal line gap -> footer
LINE_TOP_TOLERANCE = 3     # points; words within this of each other are "the same line"
MARGIN_TOLERANCE = 3       # points; x0 values this close are "the same margin"
INDENT_MARGIN_DELTA = 8    # points beyond the margin that counts as an indented (new-paragraph) line

COLUMN_GUTTER_MIN_PT = 10       # minimum empty-gutter width to call it a real column break
COLUMN_BAND_MIN = 0.25          # a gutter only counts within this fraction of the page width...
COLUMN_BAND_MAX = 0.75          # ...so a ragged-right margin at the page edge isn't mistaken for one
COLUMN_MIN_ROWS = 12            # need this many text rows on the page before trusting a column split
COLUMN_MIN_SIDE_FRACTION = 0.15 # each side must hold at least this fraction of the page's rows
COLUMN_ROW_DENSITY_THRESHOLD = 0.05  # row-coverage fraction below which a bin counts as "empty"


def extract_text(filepath: str) -> str:
    """Extract text from a PDF, reconstructed into markdown-ish structure
    (chapter headings + real paragraphs) suitable for the raw-text/markdown
    pipeline."""
    try:
        return _extract_with_layout(filepath)
    except Exception:
        pass
    try:
        return _extract_plain_fallback(filepath)
    except RuntimeError as e:
        if "password-protected" in str(e):
            raise
        # Neither pdfplumber's layout pass nor pypdf's plain extraction
        # found any text layer at all -- this is a scanned book/document
        # with no embedded OCR text, which both of the above always
        # treated as a hard failure. Fall back to rendering each page as
        # an image and running it through the same vision OCR pipeline
        # already used for embedded figures, so the document can still be
        # imported instead of being rejected outright.
        return _extract_scanned_fallback(filepath)


# ---------------------------------------------------------------- layout ---

def _extract_with_layout(filepath: str) -> str:
    import pdfplumber

    with pdfplumber.open(filepath) as pdf:
        pages_words = []
        pages_images = []
        size_counter = Counter()
        for page in pdf.pages:
            words = page.extract_words(extra_attrs=["size", "fontname"])
            pages_words.append(words)
            pages_images.append(_extract_page_images(page))
            for w in words:
                size_counter[round(w["size"], 1)] += max(len(w["text"]), 1)

        if not size_counter:
            raise RuntimeError(
                "No extractable text found in this PDF (it may be a scanned "
                "image without OCR text)."
            )

        body_size = size_counter.most_common(1)[0][0]

        # Group each page into lines once, up front, purely for the running
        # header/footer detection below -- a header/footer sits in its own
        # vertical space above/below any column content, so plain grouping
        # (even on a two-column page) still isolates it correctly as the
        # page's first/last line.
        pages_lines = [_group_into_lines(w) if w else [] for w in pages_words]
        header_text = _detect_repeated_edge_line(pages_lines, "first")
        footer_text = _detect_repeated_edge_line(pages_lines, "last")

        # Flatten every page into one continuous stream of lines, dropping
        # blank/footer-only pages, a detected running header/footer, and
        # stray trailing footer page numbers.
        all_lines = []
        for page, words, images in zip(pdf.pages, pages_words, pages_images):
            # Column detection + reordering happens on this page's raw
            # words (see _assemble_page_lines), not the plain grouping
            # above -- two-column text is almost always baseline-aligned
            # across columns, so plain top-proximity grouping merges both
            # columns' same-row words into one line before column logic
            # ever gets a chance to run on them.
            lines = _assemble_page_lines(words, images, page.width)
            if header_text and lines and _line_text(lines[0]) == header_text:
                lines = lines[1:]
            if footer_text and lines and _line_text(lines[-1]) == footer_text:
                lines = lines[:-1]
            if not lines:
                continue
            if len(lines) == 1 and _is_bare_number(lines[0]):
                continue  # whole page is just a folio number
            if len(lines) > 1 and _is_bare_number(lines[-1]):
                gap = lines[-1]["top"] - lines[-2]["top"]
                normal_gap = _median_line_gap(lines)
                if normal_gap is None or gap > normal_gap * FOOTER_GAP_RATIO:
                    lines = lines[:-1]

            all_lines.extend(lines)

        if not all_lines:
            raise RuntimeError("No extractable body text found in this PDF.")

        _dehyphenate_lines(all_lines)
        _merge_dropcaps(all_lines, body_size)

        # Margins are detected per column rather than once globally -- a
        # two-column page's right column starts at a completely different
        # x-position than the left, and a single global margin would treat
        # every right-column line as an indented, forced new paragraph.
        margins = _detect_margins_by_column(all_lines)
        indent_thresholds = {col: m + INDENT_MARGIN_DELTA for col, m in margins.items()}
        heading_min_size = body_size * HEADING_SIZE_RATIO

        return _render_markdown(all_lines, indent_thresholds, heading_min_size)


def _extract_page_images(page) -> list:
    """Extract this page's embedded images as sentinel line-dicts (same
    {"words", "x0", "top"} shape as real text lines, plus an 'is_image'
    marker) so they can be merged into reading order alongside the text.
    Images are cropped from the rendered page and re-encoded as PNG rather
    than parsed from the raw PDF XObject stream -- PDFs embed images in a
    long tail of encodings (DCT/JPEG, FlateDecode raw RGB, indexed palette,
    CMYK, ...) and rendering the region is far more robust than decoding
    each of those by hand. Never raises -- a page whose images can't be
    extracted just contributes no image lines rather than failing the
    whole document parse. Tiny regions (rules, bullets, decorative dashes)
    are skipped since they aren't meaningful embedded pictures."""
    from app.parser.image_pipeline import process_image

    out = []
    try:
        images = page.images
    except Exception:
        return out

    for img in images:
        try:
            width_pt = img["x1"] - img["x0"]
            height_pt = img["bottom"] - img["top"]
            if width_pt < 20 or height_pt < 20:
                continue  # decorative rule/bullet/icon, not a real figure
            bbox = (
                max(0, img["x0"]), max(0, img["top"]),
                min(page.width, img["x1"]), min(page.height, img["bottom"]),
            )
            if bbox[2] <= bbox[0] or bbox[3] <= bbox[1]:
                continue
            cropped = page.crop(bbox)
            pil_img = cropped.to_image(resolution=150).original
            buf = io.BytesIO()
            pil_img.save(buf, format="PNG")
            # Route through the same normalize+caption/OCR pipeline DOCX
            # images use, instead of embedding with no alt text -- PDF
            # figures previously rendered as "![]()" with a blank caption
            # regardless of what they showed.
            processed = process_image(buf.getvalue(), ".png")
            if processed is None:
                continue
            out.append({
                "words": [], "x0": img["x0"], "x1": img["x1"], "top": img["top"],
                "is_image": True, "src": processed["uri"],
                "caption": processed["caption"], "ocr_text": processed["ocr_text"],
            })
        except Exception:
            continue
    return out


def _line_text(line: dict) -> str:
    """Join a line-dict's words into plain text for comparison. Image
    sentinel lines have no words and simply produce an empty string,
    safely never matching any real header/footer text."""
    return " ".join(w["text"] for w in line.get("words", [])).strip()


def _detect_repeated_edge_line(pages_lines: list, position: str):
    """Detect a line of text that repeats verbatim as the first (or last)
    line of a page across a large fraction of pages -- a running header,
    footer, or watermark inserted by whatever tool produced the PDF. Left
    alone, this text gets glued onto whatever paragraph follows/precedes
    it once pages are flattened into one continuous stream. Returns None
    unless the same text appears on at least 3 pages and at least 40% of
    all pages that have any text at all, so a real, recurring one-line
    paragraph in normal body text isn't mistaken for a header/footer."""
    texts = []
    for lines in pages_lines:
        if not lines:
            continue
        line = lines[0] if position == "first" else lines[-1]
        text = _line_text(line)
        if text:
            texts.append(text)
    if len(texts) < 4:
        return None
    counts = Counter(texts)
    candidate, count = counts.most_common(1)[0]
    if count >= max(3, len(texts) * 0.4):
        return candidate
    return None


def _group_into_lines(words):
    """Group words sharing a visual line (close 'top' position) together,
    left-to-right, in reading order. Each line is {"words": [...], "x0": ...}
    where x0 is captured once, up front -- later passes (dehyphenation,
    drop-cap merging) may add/remove words from the line, but the original
    left edge must stay stable since paragraph-indent detection depends on it."""
    raw_lines = []
    current = []
    current_top = None
    for w in sorted(words, key=lambda w: (w["top"], w["x0"])):
        if current_top is None or abs(w["top"] - current_top) <= LINE_TOP_TOLERANCE:
            current.append(w)
            current_top = w["top"] if current_top is None else current_top
        else:
            raw_lines.append(sorted(current, key=lambda w: w["x0"]))
            current = [w]
            current_top = w["top"]
    if current:
        raw_lines.append(sorted(current, key=lambda w: w["x0"]))
    return [{"words": ln, "x0": ln[0]["x0"], "top": ln[0]["top"]} for ln in raw_lines]


def _is_bare_number(line):
    words = line["words"]
    return len(words) == 1 and words[0]["text"].strip().isdigit()


def _median_line_gap(lines):
    tops = [ln["top"] for ln in lines]
    gaps = sorted(b - a for a, b in zip(tops, tops[1:]) if b > a)
    return gaps[len(gaps) // 2] if gaps else None


def _dehyphenate_lines(all_lines):
    """Merge a word split by a line-end hyphen ('hyphen-' + 'ated' -> 'hyphenated').
    Popping the next line's first word must not disturb that line's recorded
    x0 -- it still starts where it visually started."""
    i = 0
    while i < len(all_lines) - 1:
        line, nxt = all_lines[i]["words"], all_lines[i + 1]["words"]
        if line and nxt:
            last = line[-1]
            text = last["text"]
            if len(text) > 2 and text.endswith("-") and not text.endswith("--"):
                first_next = nxt[0]
                if first_next["text"] and first_next["text"][0].islower():
                    last["text"] = text[:-1] + first_next["text"]
                    nxt.pop(0)
                    if not nxt:
                        all_lines.pop(i + 1)
                        continue
        i += 1


def _merge_dropcaps(all_lines, body_size):
    """A chapter-opening drop cap extracts as its own oversized single-letter
    line (e.g. 'I') immediately before the rest of that first word ('t was').
    Detect and splice it back onto the following word. The following line's
    x0 is deliberately left untouched (it's the drop-cap paragraph's real
    start position, not the merged word's)."""
    threshold = body_size * DROPCAP_SIZE_RATIO
    i = 0
    while i < len(all_lines) - 1:
        words = all_lines[i]["words"]
        if len(words) == 1:
            w = words[0]
            if w["size"] >= threshold and len(w["text"]) <= 2 and w["text"].isalpha():
                nxt_words = all_lines[i + 1]["words"]
                if nxt_words:
                    nxt_words[0] = dict(nxt_words[0])  # don't mutate shared refs
                    nxt_words[0]["text"] = w["text"] + nxt_words[0]["text"]
                    all_lines.pop(i)
                    continue
        i += 1


def _assemble_page_lines(words, images, page_width):
    """Group one page's raw words into lines, detect a two-column gutter,
    and -- if found -- reorder into real left-column-then-right-column
    reading order, with this page's images folded into the same pass so
    they land in the correct column position. Column detection must run
    on raw word-rows *before* the final line-grouping merge: two-column
    text is almost always baseline-aligned across both columns, so
    top-proximity grouping (the same technique used for ordinary single-
    column text) would otherwise merge each row's left- and right-column
    words into a single line before column logic ever saw them
    separately. Returns lines in final reading order, each tagged with
    `col` (0 or 1) so indent detection downstream can use the right
    column's own margin."""
    if not words:
        return sorted(images, key=lambda i: i["top"]) if images else []

    raw_rows = []
    current, current_top = [], None
    for w in sorted(words, key=lambda w: (w["top"], w["x0"])):
        if current_top is None or abs(w["top"] - current_top) <= LINE_TOP_TOLERANCE:
            current.append(w)
            current_top = w["top"] if current_top is None else current_top
        else:
            raw_rows.append(current)
            current, current_top = [w], w["top"]
    if current:
        raw_rows.append(current)

    def finalize(row_words):
        row_words = sorted(row_words, key=lambda w: w["x0"])
        return {"words": row_words, "x0": row_words[0]["x0"], "top": row_words[0]["top"]}

    gutter = None
    if len(raw_rows) >= COLUMN_MIN_ROWS:
        gutter = _detect_column_gutter_from_rows(raw_rows, page_width)

    if not gutter:
        lines = [finalize(r) for r in raw_rows]
        for ln in lines:
            ln["col"] = 0
        if images:
            lines = sorted(lines + images, key=lambda ln: ln["top"])
        return lines

    # A real gutter was found: walk every row and image, in top order,
    # queueing each into a left- or right-column buffer. A row/image that
    # spans across the gutter (a title, section heading, or full-width
    # figure) acts as a break in that flow -- whatever's queued for the
    # left column so far is emitted, then whatever's queued for the
    # right, then the full-width item itself. This mirrors how a
    # two-column layout is actually read. A large figure/table that
    # interrupts a single column without spanning the full gutter isn't
    # detected as a break and is just assigned to whichever column it
    # sits in -- true mid-page floats need real 2-D layout analysis.
    gutter_left, gutter_right = gutter
    mid = (gutter_left + gutter_right) / 2

    items = [("row", r) for r in raw_rows] + [("image", img) for img in images]
    items.sort(key=lambda it: it[1][0]["top"] if it[0] == "row" else it[1]["top"])

    left_buf, right_buf, out = [], [], []

    def flush():
        out.extend(left_buf)
        out.extend(right_buf)
        left_buf.clear()
        right_buf.clear()

    for kind, item in items:
        if kind == "row":
            row_words = item
            # A row is a genuine full-width element (title, section
            # heading, figure caption) only if some word actually occupies
            # the gutter space itself. Otherwise, even though the row was
            # grouped as one unit by top-proximity, it's almost always two
            # baseline-aligned columns' worth of text that happen to share
            # a vertical position -- split it into its left and right
            # halves rather than keeping it as one line or arbitrarily
            # assigning the whole thing to a single column.
            touches_gutter = any(w["x0"] < gutter_right and w["x1"] > gutter_left for w in row_words)
            if touches_gutter:
                ln = finalize(row_words)
                ln["col"] = 0
                flush()
                out.append(ln)
                continue

            left_part = [w for w in row_words if (w["x0"] + w["x1"]) / 2 < mid]
            right_part = [w for w in row_words if (w["x0"] + w["x1"]) / 2 >= mid]
            if left_part:
                ln = finalize(left_part)
                ln["col"] = 0
                left_buf.append(ln)
            if right_part:
                ln = finalize(right_part)
                ln["col"] = 1
                right_buf.append(ln)
        else:
            x0, x1 = item["x0"], item.get("x1", item["x0"])
            crosses = x0 < gutter_left and x1 > gutter_right
            is_left = (x0 + x1) / 2 < mid
            item["col"] = 0 if (crosses or is_left) else 1
            if crosses:
                flush()
                out.append(item)
            elif is_left:
                left_buf.append(item)
            else:
                right_buf.append(item)

    flush()
    return out


def _detect_column_gutter_from_rows(rows, page_width):
    """Look for a vertical gutter -- a contiguous horizontal band with
    (almost) no text in it, roughly in the middle of the page -- which
    indicates a two-column layout (papers, magazines, scripts). `rows` is
    a list of word-lists, one per visual row, computed before words on
    opposite sides of a real column gap get merged into a single row by
    top-proximity alone. Uses the fraction of *rows* touching each
    horizontal bin rather than raw word count, so a single full-width
    title or section heading can't mask a real column gap by itself.
    Returns (gutter_left, gutter_right) in points, or None."""
    if not page_width:
        return None

    bins = 200
    bin_w = page_width / bins
    coverage = [0] * bins
    for row_words in rows:
        touched = set()
        for w in row_words:
            b0 = max(0, min(bins - 1, int(w["x0"] / bin_w)))
            b1 = max(0, min(bins - 1, int(w["x1"] / bin_w)))
            touched.update(range(b0, b1 + 1))
        for b in touched:
            coverage[b] += 1

    total = len(rows)
    density = [c / total for c in coverage]

    lo, hi = int(bins * COLUMN_BAND_MIN), int(bins * COLUMN_BAND_MAX)
    best = None
    i = lo
    while i < hi:
        if density[i] <= COLUMN_ROW_DENSITY_THRESHOLD:
            j = i
            while j < hi and density[j] <= COLUMN_ROW_DENSITY_THRESHOLD:
                j += 1
            width_pt = (j - i) * bin_w
            if width_pt >= COLUMN_GUTTER_MIN_PT and (best is None or width_pt > best[1] - best[0]):
                best = (i * bin_w, j * bin_w)
            i = j
        else:
            i += 1

    if best is None:
        return None

    # Require both sides to actually hold a meaningful share of the
    # page's content -- otherwise this "gutter" is just a ragged
    # paragraph edge or a pull-quote/sidebar, not a real two-column
    # layout. Counted per word rather than per row: baseline-aligned
    # column text puts both columns' words in the same merged row (an
    # even left/right split), so no row is ever a clear row-level
    # majority for either side.
    gutter_left, gutter_right = best
    mid = (gutter_left + gutter_right) / 2
    total_words = sum(len(row_words) for row_words in rows)
    if not total_words:
        return None
    left_words = sum(
        1 for row_words in rows for w in row_words if (w["x0"] + w["x1"]) / 2 < mid
    )
    right_words = total_words - left_words
    if left_words < total_words * COLUMN_MIN_SIDE_FRACTION or right_words < total_words * COLUMN_MIN_SIDE_FRACTION:
        return None

    return gutter_left, gutter_right


def _detect_margins_by_column(all_lines):
    """Like _detect_margin, but computed separately per column (see the
    `col` tag _assemble_page_lines adds) -- a two-column page's right
    column starts at a completely different x-position than the left, so
    a single shared margin would misclassify every right-column line as
    an indented, forced new paragraph."""
    by_col = {}
    for ln in all_lines:
        by_col.setdefault(ln.get("col", 0), []).append(ln)
    return {col: _detect_margin(lines) for col, lines in by_col.items()}


def _detect_margin(all_lines):
    """Find the document's true left margin -- the smaller of the (usually
    two) dominant line-start x-positions, the other being the first-line
    paragraph indent."""
    counter = Counter()
    for line in all_lines:
        counter[round(line["x0"])] += 1
    if not counter:
        return 72.0

    buckets = []
    for x0, cnt in sorted(counter.items()):
        for b in buckets:
            if abs(b["x0"] - x0) <= MARGIN_TOLERANCE:
                b["count"] += cnt
                break
        else:
            buckets.append({"x0": x0, "count": cnt})

    buckets.sort(key=lambda b: -b["count"])
    max_count = buckets[0]["count"]
    candidates = [b["x0"] for b in buckets[:3] if b["count"] >= max_count * 0.2]
    return min(candidates) if candidates else buckets[0]["x0"]


_PUA_RE = re.compile(r"[\uE000-\uF8FF]")


def _clean_text_artifacts(text: str) -> str:
    text = re.sub(r"^[\uE000-\uF8FF]\s*", "- ", text)
    return _PUA_RE.sub("", text)


_ALLCAPS_WORD_RE = re.compile(r"^[A-Z][A-Z']{1,}$")


def _speaker_label_word_count(words) -> int:
    """Number of words in this line if the *entire* line is a short,
    all-caps speaker label (e.g. 'MARK ANTONY' or 'CLEOPATRA' on its own
    line, with the dialogue starting on the next line) -- the convention
    in narrow-column-reflowed script/play PDFs. Capped at 4 words so a
    genuine long all-caps heading/sentence isn't mistaken for a name."""
    if not words or len(words) > 4:
        return 0
    if all(_ALLCAPS_WORD_RE.match(w["text"]) for w in words):
        return len(words)
    return 0


def _looks_like_script_format(all_lines) -> bool:
    """Detect play/script formatting at the document level: standalone,
    short all-caps speaker-label lines ('CLEOPATRA', 'MARK ANTONY') with
    the dialogue starting on the next line are common throughout. Checking
    density across the whole document -- rather than trusting any single
    line -- means a normal document that happens to have one short
    all-caps line (a heading, an acronym on its own line) isn't mistaken
    for a script and doesn't get its paragraphs needlessly fragmented."""
    total, hits = 0, 0
    for line in all_lines:
        words = line.get("words")
        if not words:
            continue
        total += 1
        if _speaker_label_word_count(words) > 0:
            hits += 1
    return total >= 20 and hits >= max(15, total * 0.12)


def _render_markdown(all_lines, indent_thresholds, heading_min_size):
    script_format = _looks_like_script_format(all_lines)
    default_threshold = indent_thresholds.get(0, 80.0)
    out = []          # list of ("heading" | "para", text)
    para_words = []
    heading_words = []
    in_heading = False
    just_finished_heading = False

    def flush_para():
        nonlocal para_words
        if para_words:
            out.append(("para", _clean_text_artifacts(" ".join(para_words))))
            para_words = []

    def flush_heading():
        nonlocal heading_words, in_heading
        if heading_words:
            out.append(("heading", _clean_text_artifacts(" ".join(heading_words))))
            heading_words = []
        in_heading = False

    for line in all_lines:
        if line.get("is_image"):
            flush_heading()
            flush_para()
            out.append(("image", line["src"], line.get("caption", "")))
            just_finished_heading = False
            continue

        words = line["words"]
        if not words:
            continue
        first_word = words[0]
        # The length check exists to reject a single oversized stray glyph
        # (a drop cap, a bullet/rule character) from being mistaken for a
        # heading -- but requiring the *first* word alone to be > 2 chars
        # wrongly disqualified any real heading that starts with a short
        # word ("A Simple Plan", "An Introduction to...", "Is This It?").
        # A heading with more than one word at heading size is never a
        # stray single glyph, so the length check only needs to apply when
        # there's just the one word.
        is_heading_word = first_word["size"] >= heading_min_size and (
            len(first_word["text"]) > 2 or len(words) > 1
        )

        if is_heading_word:
            if not in_heading:
                flush_para()
                in_heading = True
            heading_words.extend(w["text"] for w in words)
            continue

        if in_heading:
            flush_heading()
            just_finished_heading = True

        is_indented = line["x0"] > indent_thresholds.get(line.get("col", 0), default_threshold)
        is_speaker_line = script_format and _speaker_label_word_count(words) > 0
        if is_indented or just_finished_heading or not para_words or is_speaker_line:
            flush_para()
            just_finished_heading = False
        para_words.extend(w["text"] for w in words)

    flush_heading()
    flush_para()

    md_lines = []
    for item in out:
        kind = item[0]
        if kind == "image":
            _, src, caption = item
            alt = caption.replace("[", "").replace("]", "") if caption else ""
            md_lines.append(f"![{alt}]({src})")
            if caption:
                md_lines.append(f"*{caption}*")
            md_lines.append("")
            continue
        text = item[1].strip()
        if not text:
            continue
        md_lines.append(f"# {text}" if kind == "heading" else text)
        md_lines.append("")
    return "\n".join(md_lines).strip()


# --------------------------------------------------------------- fallback ---

def _extract_scanned_fallback(filepath: str) -> str:
    """Last resort for a PDF with no text layer at all (a scanned book/
    document, or a PDF made entirely of flattened page images): render each
    page as an image and run it through the same vision OCR/captioning
    pipeline used for embedded figures. When ANTHROPIC_API_KEY is
    configured this recovers real page text; when it isn't, understand_image
    has nothing to return and pages come through as plain page images
    instead -- still importable, rather than the whole document being
    rejected. Raises if pdfplumber isn't available or truly nothing could
    be produced (blank/corrupt PDF)."""
    import pdfplumber
    from app.parser.image_pipeline import process_image

    md_lines = []
    with pdfplumber.open(filepath) as pdf:
        if not pdf.pages:
            raise RuntimeError("This PDF has no pages.")
        for i, page in enumerate(pdf.pages):
            try:
                pil_img = page.to_image(resolution=150).original
                buf = io.BytesIO()
                pil_img.save(buf, format="PNG")
                processed = process_image(buf.getvalue(), ".png")
            except Exception:
                processed = None
            if processed is None:
                continue
            if processed["ocr_text"]:
                md_lines.append(processed["ocr_text"])
                md_lines.append("")
            else:
                alt = (processed["caption"] or f"Page {i + 1}").replace("[", "").replace("]", "")
                md_lines.append(f"![{alt}]({processed['uri']})")
                md_lines.append("")

    text = "\n".join(md_lines).strip()
    if not text:
        raise RuntimeError(
            "No extractable text found in this PDF (it may be a scanned "
            "image without OCR text, and image understanding isn't "
            "configured)."
        )
    return text


def _extract_plain_fallback(filepath: str) -> str:
    try:
        from pypdf import PdfReader
    except ImportError:
        raise RuntimeError("Neither pdfplumber nor pypdf is installed.")

    reader = PdfReader(filepath)
    if reader.is_encrypted:
        try:
            # decrypt() returns a falsy status (PasswordType.NOT_DECRYPTED)
            # on a wrong/empty password rather than raising -- checking
            # only for an exception let that failure through silently,
            # and the actual failure only surfaced later as an unrelated,
            # unhandled pypdf internal error when something touched the
            # still-encrypted content.
            result = reader.decrypt("")
        except Exception:
            result = None
        if not result:
            raise RuntimeError("This PDF is password-protected and can't be read.")

    try:
        pages = [p.extract_text() or "" for p in reader.pages]
    except Exception:
        raise RuntimeError("This PDF is password-protected and can't be read.")
    pages = [p for p in pages if p.strip()]
    if not pages:
        raise RuntimeError(
            "No extractable text found in this PDF (it may be a scanned "
            "image without OCR text)."
        )
    text = "\n\n".join(pages)
    text = text.replace("\t", " ")
    text = re.sub(r"(\w)-\n(\w)", r"\1\2", text)
    text = re.sub(r"(?<=[a-z,;])\n(?=[a-z])", " ", text)
    text = re.sub(r"\n\s*\d+\s*\n", "\n\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()

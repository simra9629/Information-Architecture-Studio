"""
Image extraction and "understanding" (captioning + OCR), shared across every
input format (DOCX, PDF, Markdown, HTML) and by the renderers/exporters that
place images back into output.

Storage design: images are carried as data URIs (data:image/png;base64,...)
rather than files on disk. This app has no other stateful per-session file
store for derived assets, and data URIs round-trip for free through the
existing raw_content text-caching mechanism (pipeline._blocks_to_markdown ->
markdown text -> re-parsed later by markdown_parser) with zero new Flask
routes, zero session-scoped cleanup, and one code path shared by every
input format and every exporter.

Design:
  - Extraction (see docx_parser/pdf_parser/markdown_parser/pipeline._strip_html)
    never depends on network access or an API key -- it always works,
    producing raw image bytes plus whatever alt-text/description the
    source format already had.
  - understand_image() is the only network-dependent piece (calls the
    Anthropic API for captioning + OCR). It is entirely optional: if no
    API key is configured, or the call fails for any reason, callers get
    back a graceful fallback (existing alt-text, or a generic caption) --
    extraction and placement never depend on this succeeding.
"""
import os
import re
import io
import base64
from typing import Optional

_EXT_TO_MEDIA_TYPE = {
    ".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
    ".gif": "image/gif", ".webp": "image/webp", ".bmp": "image/bmp",
}
_MEDIA_TYPE_TO_EXT = {v: k for k, v in _EXT_TO_MEDIA_TYPE.items() if k != ".jpg"}


def to_data_uri(data: bytes, ext: str) -> str:
    media_type = _EXT_TO_MEDIA_TYPE.get((ext or "").lower(), "image/png")
    b64 = base64.standard_b64encode(data).decode("ascii")
    return f"data:{media_type};base64,{b64}"


_DATA_URI_RE = re.compile(r"^data:([\w/+.-]+);base64,(.+)$", re.DOTALL)


def from_data_uri(uri: str):
    """Returns (bytes, ext) or (None, None) if not a recognized data URI."""
    m = _DATA_URI_RE.match(uri.strip())
    if not m:
        return None, None
    media_type, b64 = m.group(1), m.group(2)
    ext = _MEDIA_TYPE_TO_EXT.get(media_type, ".png")
    try:
        return base64.standard_b64decode(b64), ext
    except Exception:
        return None, None


def is_data_uri(s: str) -> bool:
    return bool(s) and s.strip().startswith("data:image/")


# ─────────────────────────────────────────────────────────────────────────
# "Understanding": captioning + OCR via the Anthropic API. Optional --
# controlled entirely by whether ANTHROPIC_API_KEY is set. Never raises;
# always returns a usable (possibly empty) result.
# ─────────────────────────────────────────────────────────────────────────

_GENERIC_ALT_RE = re.compile(
    r"^(image|picture|photo|img|graphic|untitled|screenshot)\s*\d*$", re.IGNORECASE
)


def _alt_is_meaningful(alt: Optional[str]) -> bool:
    """A real, human-written caption vs. a placeholder like 'image1.png' or
    an empty/absent alt attribute."""
    if not alt:
        return False
    alt = alt.strip()
    if len(alt) < 4:
        return False
    if _GENERIC_ALT_RE.match(alt):
        return False
    if re.match(r"^[\w-]+\.(png|jpe?g|gif|webp|bmp)$", alt, re.IGNORECASE):
        return False
    return True


def understand_image(data: bytes, ext: str, existing_alt: Optional[str] = None) -> dict:
    """Caption (where the source didn't already give a meaningful one) and
    OCR (only where the image actually contains meaningful text) an image
    via a single Claude vision call. Returns {"caption": str, "ocr_text": str}
    -- both may be "" if understanding wasn't needed/available/successful.
    `existing_alt`, when meaningful, is trusted as-is and returned as the
    caption without spending an API call on it."""
    if _alt_is_meaningful(existing_alt):
        return {"caption": existing_alt.strip(), "ocr_text": ""}

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        return {"caption": "", "ocr_text": ""}

    try:
        import anthropic
    except ImportError:
        return {"caption": "", "ocr_text": ""}

    media_type = _EXT_TO_MEDIA_TYPE.get((ext or "").lower(), "image/png")

    try:
        client = anthropic.Anthropic(api_key=api_key)
        b64 = base64.standard_b64encode(data).decode("ascii")
        response = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=300,
            messages=[{
                "role": "user",
                "content": [
                    {"type": "image", "source": {"type": "base64", "media_type": media_type, "data": b64}},
                    {"type": "text", "text": (
                        "Reply with exactly two lines, nothing else.\n"
                        "Line 1: a single plain-English sentence (under 20 words) captioning this "
                        "image for use as alt-text/a figure caption. If the image is purely "
                        "decorative or too generic to describe usefully, write NONE instead.\n"
                        "Line 2: if the image contains meaningful readable text (e.g. it's a "
                        "screenshot, chart, slide, or scanned document), transcribe that text "
                        "verbatim. Otherwise write NONE."
                    )},
                ],
            }],
        )
        text = "".join(block.text for block in response.content if getattr(block, "type", "") == "text")
        lines = [l.strip() for l in text.strip().splitlines() if l.strip()]
        caption = lines[0] if lines else ""
        ocr = lines[1] if len(lines) > 1 else ""
        if caption.upper() == "NONE":
            caption = ""
        if ocr.upper() == "NONE":
            ocr = ""
        return {"caption": caption, "ocr_text": ocr}
    except Exception:
        # Network error, bad key, rate limit, unexpected response shape --
        # image extraction/placement must never fail because of this.
        return {"caption": "", "ocr_text": ""}


def fallback_caption(index: int, existing_alt: Optional[str] = None) -> str:
    """What to use when understand_image() has nothing (no API key, or the
    call declined to caption): prefer any existing alt text even if
    generic, else a plain numbered label."""
    if existing_alt and existing_alt.strip():
        return existing_alt.strip()
    return f"Image {index}"


# ─────────────────────────────────────────────────────────────────────────
# Normalization: every image, from any source format, is decoded and
# re-encoded here before it's stored or sent anywhere else.
# ─────────────────────────────────────────────────────────────────────────

MAX_DIMENSION = 2200   # px, long-edge cap for stored/rendered images
JPEG_QUALITY = 87


def _has_real_alpha(im) -> bool:
    """True only if this image actually uses transparency, not just a mode
    that supports it -- most "RGBA" screenshots and scans are fully
    opaque, and flattening those to JPEG is far smaller than keeping them
    as PNG for no visual benefit."""
    if im.mode == "P":
        im = im.convert("RGBA")
    if im.mode not in ("RGBA", "LA"):
        return False
    alpha = im.getchannel("A")
    return alpha.getextrema()[0] < 255


def normalize_image(data: bytes, ext_hint: str = ""):
    """Decode arbitrary image bytes with Pillow, downscale if oversized, and
    re-encode as PNG (if it has real transparency) or JPEG (otherwise).
    This is the single point where embedded bytes are validated as an
    actual, displayable raster image: Word documents in particular
    sometimes embed vector metafiles (WMF/EMF) or other formats no browser
    can render, and trusting the source's own content-type/extension label
    for those -- the previous behavior -- silently produced a broken
    <img> tag labeled image/png, and sent that same unusable data to the
    captioning API. Returns (bytes, ext) on success, or None if `data`
    isn't a decodable raster image at all, so the caller can skip it
    instead of embedding something broken.
    Falls back to trusting `data`/`ext_hint` as-is only if Pillow itself
    isn't installed (extraction should never hard-fail over this)."""
    try:
        from PIL import Image
    except ImportError:
        return data, (ext_hint or ".png")

    try:
        with Image.open(io.BytesIO(data)) as im:
            im.load()  # force full decode now, while we can still catch a bad file
            has_alpha = _has_real_alpha(im)
            w, h = im.size
            if w <= 0 or h <= 0:
                return None
            if max(w, h) > MAX_DIMENSION:
                scale = MAX_DIMENSION / max(w, h)
                new_size = (max(1, round(w * scale)), max(1, round(h * scale)))
                im = im.resize(new_size, Image.LANCZOS)

            buf = io.BytesIO()
            if has_alpha:
                im.convert("RGBA").save(buf, format="PNG", optimize=True)
                return buf.getvalue(), ".png"
            im.convert("RGB").save(buf, format="JPEG", quality=JPEG_QUALITY)
            return buf.getvalue(), ".jpg"
    except Exception:
        return None


def process_image(data: bytes, ext_hint: str, existing_alt: Optional[str] = None) -> Optional[dict]:
    """Single entry point every parser (DOCX, PDF, Markdown/HTML) should use
    to ingest an embedded image: normalize the raw bytes into a real,
    reasonably-sized raster image, then caption/OCR it. Returns None if
    `data` isn't a decodable image, so the caller can skip that block
    entirely rather than embedding a broken one. On success, returns
    {"uri": str, "caption": str, "ocr_text": str}."""
    normalized = normalize_image(data, ext_hint)
    if normalized is None:
        return None
    norm_data, norm_ext = normalized
    understanding = understand_image(norm_data, norm_ext, existing_alt=existing_alt)
    return {
        "uri": to_data_uri(norm_data, norm_ext),
        "caption": understanding["caption"],
        "ocr_text": understanding["ocr_text"],
    }

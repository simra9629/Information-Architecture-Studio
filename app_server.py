"""
Information Architecture Studio — Flask Web App  v1.3
"""
import os
import traceback
import json
import uuid
import tempfile
from werkzeug.utils import secure_filename
from flask import Flask, request, jsonify, send_from_directory, send_file
from app.pipeline import Pipeline
from app.themes.theme_engine import ThemeEngine, THEME_META, THEME_DEFAULTS
from app.themes import theme_extractor
from app.themes import auto_designer
from app.exporters.exporters import DOCXExporter, PDFExporter
from app.exporters.pdf_exporter import export_pdf as rl_export_pdf
from app.renderer.presentation_engine import generate_pptx

app = Flask(__name__, static_folder="static", template_folder="templates")
app.config["MAX_CONTENT_LENGTH"] = 32 * 1024 * 1024  # 32 MB


def _safe_auto_design(doc):
    """
    auto_designer.design(doc) wrapped so a bug in genre/palette generation
    for one particular document degrades to "no auto palette" (the export
    then falls back to that format's own default palette) instead of
    taking down the whole export. Logs the real traceback server-side
    either way, so a failure here is diagnosable rather than silently
    swallowed.
    """
    try:
        return auto_designer.design(doc)
    except Exception:
        traceback.print_exc()
        return None


def _safe_export_name(raw_name: str, ext: str) -> str:
    """
    Sanitize a user-supplied filename before joining it with EXPORTS_DIR.
    Without this, a filename like '../../etc/cron.d/x' in the JSON body
    would let a client write files outside the exports directory.
    """
    base = secure_filename((raw_name or "document").strip()) or "document"
    return base + ext

pipeline  = Pipeline()
theme_eng = ThemeEngine()
docx_exp  = DOCXExporter()
pdf_exp   = PDFExporter()

EXPORTS_DIR = os.path.join(os.path.dirname(__file__), "exports")
os.makedirs(EXPORTS_DIR, exist_ok=True)


# ── UI ─────────────────────────────────────────────────────────────────────────

def _resolve_theme(theme: str, custom_css: str):
    """
    If `theme` refers to a saved custom theme (not one of the 14 built-ins,
    and not the special 'auto' value) and no explicit custom_css override was
    already supplied, generate the theme's CSS from its saved properties/
    elements and route it through the renderer's 'custom:' CSS-is-complete-
    stylesheet path. Without this, a saved custom theme selected by ID would
    silently fall back to the academic theme, since THEME_CSS only recognizes
    the 14 built-in IDs. 'auto' is left untouched — Pipeline.run() handles
    the content-aware auto-design logic itself.
    """
    if custom_css or theme in THEME_META or theme == "auto":
        return theme, custom_css
    custom = theme_eng.load_custom_theme(theme)
    if not custom:
        return "academic", custom_css
    css = theme_eng.build_css_from_properties(
        theme, custom.get("properties", {}), custom.get("elements")
    )
    return "custom:", css


@app.route("/")
def index():
    return send_from_directory("static", "index.html")

@app.route("/designer")
def designer():
    return send_from_directory("static", "designer.html")


# ── TRANSFORM ──────────────────────────────────────────────────────────────────

@app.route("/api/transform", methods=["POST"])
def transform():
    data       = request.get_json(force=True)
    raw_text   = data.get("content", "").strip()
    theme      = data.get("theme", "auto")
    mode       = data.get("mode", "document")
    custom_css = data.get("custom_css", "")
    icon_style = data.get("icon_style", "unicode")
    decorate   = bool(data.get("decorate", False))
    border     = bool(data.get("border", False))
    decoration_style = data.get("decoration_style", "auto")
    doodle_density = data.get("doodle_density", None)

    if not raw_text:
        return jsonify({"error": "No content provided"}), 400

    requested_theme = theme
    theme, custom_css = _resolve_theme(theme, custom_css)

    try:
        result = pipeline.run(raw_text, theme=theme, mode=mode, custom_css=custom_css, icon_style=icon_style,
                               decorate=decorate, border=border, decoration_style=decoration_style,
                               doodle_density=doodle_density)
        return jsonify({
            "html":            result["html"],
            "project_type":    result["project_type"],
            "type_confidence": result["type_confidence"],
            "block_count":     result["block_count"],
            "blocks":          result["blocks"],
            "suggestions":     [(s[0], s[1]) for s in result["suggestions"]],
            "theme":           requested_theme,
            "mode":            result["mode"],
            "input_mode":      result.get("input_mode", "markdown"),
            "auto_design_profile": result.get("auto_design_profile"),
            "auto_design_properties": result.get("auto_design_properties"),
            "auto_design_elements": result.get("auto_design_elements"),
        })
    except Exception as e:
        traceback.print_exc()  # full traceback -> server console, for debugging
        return jsonify({"error": str(e)}), 500


# ── UPLOAD ─────────────────────────────────────────────────────────────────────


# In-memory store: session_id → {path, ext, filename, raw_content}
_upload_store: dict = {}
_UPLOAD_DIR = os.path.join(tempfile.gettempdir(), "ias_uploads")
os.makedirs(_UPLOAD_DIR, exist_ok=True)


def _run_for_session(info: dict, theme: str, mode: str, custom_css: str, icon_style: str,
                      decorate: bool = False, border: bool = False,
                      decoration_style: str = "auto", doodle_density=None) -> dict:
    """Re-run the pipeline for a previously-uploaded session. Reuses the
    cached raw_content (captured at upload time) via the fast pipeline.run()
    path instead of pipeline.run_from_file(), which would otherwise redo
    the original file parsing -- e.g. PDF layout extraction, which can take
    upwards of a minute on a full-length novel -- on every single theme
    switch or export. Falls back to re-parsing the file only if no cached
    raw_content is available (e.g. sessions created before this cache existed)."""
    raw = info.get("raw_content")
    if raw:
        return pipeline.run(raw, theme=theme, mode=mode, custom_css=custom_css, icon_style=icon_style,
                             decorate=decorate, border=border, decoration_style=decoration_style,
                             doodle_density=doodle_density)
    return pipeline.run_from_file(info["path"], theme=theme, mode=mode,
                                   custom_css=custom_css, icon_style=icon_style,
                                   decorate=decorate, border=border, decoration_style=decoration_style,
                                   doodle_density=doodle_density)


@app.route("/api/upload", methods=["POST"])
def upload():
    if "file" not in request.files:
        return jsonify({"error": "No file provided"}), 400

    f     = request.files["file"]
    theme = request.form.get("theme", "auto")
    mode  = request.form.get("mode", "document")
    icon_style = request.form.get("icon_style", "unicode")
    custom_css = request.form.get("custom_css", "")
    decorate   = request.form.get("decorate", "false").lower() == "true"
    border     = request.form.get("border", "false").lower() == "true"
    decoration_style = request.form.get("decoration_style", "auto")
    doodle_density = request.form.get("doodle_density", type=int)

    if not f.filename:
        return jsonify({"error": "No file selected"}), 400

    ext     = os.path.splitext(f.filename)[1].lower()
    allowed = {".md", ".txt", ".html", ".docx", ".pdf"}
    if ext not in allowed:
        return jsonify({"error": f"Unsupported type '{ext}'. Allowed: {', '.join(sorted(allowed))}"}), 400

    # Save file persistently so /api/rerender can re-process it
    session_id = str(uuid.uuid4())
    persistent_path = os.path.join(_UPLOAD_DIR, f"{session_id}{ext}")
    f.save(persistent_path)
    _upload_store[session_id] = {
        "path": persistent_path,
        "ext": ext,
        "filename": f.filename,
    }

    try:
        requested_theme = theme
        theme, custom_css = _resolve_theme(theme, custom_css)
        result = pipeline.run_from_file(persistent_path, theme=theme, mode=mode,
                                         custom_css=custom_css, icon_style=icon_style,
                                         decorate=decorate, border=border,
                                         decoration_style=decoration_style, doodle_density=doodle_density)
    except Exception as e:
        traceback.print_exc()  # full traceback -> server console, for debugging
        return jsonify({"error": str(e)}), 500

    # Cache the extracted/reconstructed raw text alongside the session so
    # later theme switches and exports can reuse it via pipeline.run()
    # instead of re-running the (potentially slow -- e.g. PDF layout
    # extraction on a novel) file-parsing step from scratch every time.
    _upload_store[session_id]["raw_content"] = result.get("raw_content", "")

    return jsonify({
        "html":            result["html"],
        "raw_content":     result.get("raw_content", ""),
        "session_id":      session_id,
        "project_type":    result["project_type"],
        "type_confidence": result["type_confidence"],
        "block_count":     result["block_count"],
        "blocks":          result["blocks"],
        "suggestions":     [(s[0], s[1]) for s in result["suggestions"]],
        "theme":           requested_theme,
        "mode":            result["mode"],
        "input_mode":      result.get("input_mode", "unknown"),
        "filename":        f.filename,
        "auto_design_profile": result.get("auto_design_profile"),
        "auto_design_properties": result.get("auto_design_properties"),
        "auto_design_elements": result.get("auto_design_elements"),
    })


@app.route("/api/rerender", methods=["POST"])
def rerender():
    """Re-render a previously uploaded file with a new theme/mode."""
    data       = request.get_json(force=True)
    session_id = data.get("session_id", "")
    theme      = data.get("theme", "auto")
    mode       = data.get("mode", "document")
    raw        = data.get("raw_content", "")
    custom_css = data.get("custom_css", "")
    icon_style = data.get("icon_style", "unicode")
    decorate   = bool(data.get("decorate", False))
    border     = bool(data.get("border", False))
    decoration_style = data.get("decoration_style", "auto")
    doodle_density = data.get("doodle_density", None)

    requested_theme = theme
    theme, custom_css = _resolve_theme(theme, custom_css)

    if session_id and session_id in _upload_store:
        info = _upload_store[session_id]
        try:
            result = _run_for_session(info, theme, mode, custom_css, icon_style,
                                       decorate, border, decoration_style, doodle_density)
            return jsonify({
                "html": result["html"], "block_count": result["block_count"],
                "theme": requested_theme, "auto_design_profile": result.get("auto_design_profile"),
                "auto_design_properties": result.get("auto_design_properties"),
                "auto_design_elements": result.get("auto_design_elements"),
            })
        except Exception as e:
            traceback.print_exc()  # full traceback -> server console, for debugging
            return jsonify({"error": str(e)}), 500

    if raw:
        try:
            result = pipeline.run(raw, theme=theme, mode=mode, custom_css=custom_css, icon_style=icon_style,
                                   decorate=decorate, border=border, decoration_style=decoration_style,
                                   doodle_density=doodle_density)
            return jsonify({
                "html": result["html"], "block_count": result["block_count"],
                "theme": requested_theme, "auto_design_profile": result.get("auto_design_profile"),
                "auto_design_properties": result.get("auto_design_properties"),
                "auto_design_elements": result.get("auto_design_elements"),
            })
        except Exception as e:
            traceback.print_exc()  # full traceback -> server console, for debugging
            return jsonify({"error": str(e)}), 500

    return jsonify({"error": "No session or content to rerender"}), 400


# ── EXPORTS ────────────────────────────────────────────────────────────────────

@app.route("/api/export/html", methods=["POST"])
def export_html():
    """Byte-for-byte export of the rendered HTML."""
    data     = request.get_json(force=True)
    html     = data.get("html", "")
    filename = _safe_export_name(data.get("filename", "document"), ".html")
    path     = os.path.join(EXPORTS_DIR, filename)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(html)
    return send_file(path, as_attachment=True, download_name=filename,
                     mimetype="text/html")


@app.route("/api/export/pdf", methods=["POST"])
def export_pdf():
    """
    PDF export. Prefers WeasyPrint, which renders the *actual* styled HTML
    (custom CSS included — colors, borders, ::before content, fonts, filters)
    so the PDF visually matches the live preview. Falls back to the
    dependency-free ReportLab renderer (no custom CSS support) only if
    WeasyPrint isn't installed.
    """
    data       = request.get_json(force=True)
    html       = data.get("html", "")
    raw_text   = data.get("content", "")
    session_id = data.get("session_id", "")
    theme      = data.get("theme", "auto")
    custom_css = data.get("custom_css", "")
    icon_style = data.get("icon_style", "unicode")
    decorate   = bool(data.get("decorate", False))
    border     = bool(data.get("border", False))
    decoration_style = data.get("decoration_style", "auto")
    doodle_density = data.get("doodle_density", None)
    filename   = _safe_export_name(data.get("filename", "document"), ".pdf")
    path       = os.path.join(EXPORTS_DIR, filename)

    theme, custom_css = _resolve_theme(theme, custom_css)

    # Get fully-rendered HTML (with custom CSS/icon style baked in) one way or another.
    # Keep the parsed `result` around (if we had to parse at all) so the
    # WeasyPrint-failure fallback below can reuse the already-parsed
    # document instead of re-running the whole pipeline a second time --
    # for a large import (e.g. a novel PDF, tens of seconds to parse) that
    # double-parse was pushing total request time well past typical
    # timeouts, effectively making PDF export hang/fail on big documents.
    result = None
    if not html:
        try:
            if session_id and session_id in _upload_store:
                info = _upload_store[session_id]
                result = _run_for_session(info, theme, "document", custom_css, icon_style,
                                           decorate, border, decoration_style, doodle_density)
            elif raw_text:
                result = pipeline.run(raw_text, theme=theme, mode="document",
                                       custom_css=custom_css, icon_style=icon_style,
                                       decorate=decorate, border=border,
                                       decoration_style=decoration_style, doodle_density=doodle_density)
            else:
                return jsonify({"error": "No content provided for PDF export"}), 400
            html = result["html"]
        except Exception as e:
            traceback.print_exc()  # full traceback -> server console, for debugging
            return jsonify({"error": f"PDF export failed: {e}"}), 500

    try:
        pdf_exp.export(html, path)
        return send_file(path, as_attachment=True, download_name=filename,
                         mimetype="application/pdf")
    except Exception as e:
        traceback.print_exc()  # full traceback -> server console, for debugging
        # WeasyPrint unavailable or failed — fall back to the ReportLab renderer.
        # Note: this fallback does NOT support custom CSS (it uses its own
        # hardcoded theme palettes) but reuses the already-parsed document
        # (see above) rather than re-parsing from scratch. It DOES still
        # honor the auto-generated (or saved custom) palette below, though —
        # without that, every 'auto'/'custom:' export landing on this path
        # would silently render in the hardcoded 'academic' colors instead
        # of the theme actually shown in the live preview. It also honors
        # decorate/border via its own canvas-based page decoration, since
        # it can't reuse the HTML/CSS version rendered above.
        try:
            if result is None:
                if raw_text:
                    result = pipeline.run(raw_text, theme=theme, mode="document")
                elif session_id and session_id in _upload_store:
                    result = _run_for_session(_upload_store[session_id], theme, "document", "", "unicode")
                else:
                    return jsonify({"error": f"PDF export failed: {e}"}), 500
            rl_palette = None
            if theme == "auto":
                design = _safe_auto_design(result["document"])
                if design:
                    rl_palette = auto_designer.to_docx_palette(design)
            pdf_bytes = rl_export_pdf(result["document"], theme=theme, palette=rl_palette,
                                       decorate=decorate, border=border,
                                       decoration_style=decoration_style)
            with open(path, "wb") as fh:
                fh.write(pdf_bytes)
            return send_file(path, as_attachment=True, download_name=filename,
                             mimetype="application/pdf")
        except Exception as e2:
            return jsonify({"error": f"PDF export failed: {e2}"}), 500


@app.route("/api/export/docx", methods=["POST"])
def export_docx():
    """DOCX export — respects current theme."""
    data       = request.get_json(force=True)
    raw_text   = data.get("content", "")
    session_id = data.get("session_id", "")
    theme      = data.get("theme", "auto")
    custom_css = data.get("custom_css", "")
    icon_style = data.get("icon_style", "unicode")
    decorate   = bool(data.get("decorate", False))
    border     = bool(data.get("border", False))
    decoration_style = data.get("decoration_style", "auto")
    filename   = _safe_export_name(data.get("filename", "document"), ".docx")
    path       = os.path.join(EXPORTS_DIR, filename)

    requested_theme = theme
    theme, custom_css = _resolve_theme(theme, custom_css)

    try:
        if session_id and session_id in _upload_store:
            info = _upload_store[session_id]
            result = _run_for_session(info, theme, "document", custom_css, icon_style)
        elif raw_text:
            result = pipeline.run(raw_text, theme=theme, mode="document",
                                   custom_css=custom_css, icon_style=icon_style)
        else:
            return jsonify({"error": "No content provided for DOCX export"}), 400

        docx_palette = None
        if theme == "auto":
            design = _safe_auto_design(result["document"])
            if design:
                docx_palette = auto_designer.to_docx_palette(design)
        else:
            meta = THEME_DEFAULTS.get(requested_theme)
            if not meta and theme == "custom:":
                custom = theme_eng.load_custom_theme(requested_theme)
                meta = custom.get("properties") if custom else None
            if meta:
                docx_palette = {
                    "accent": meta.get("color_accent", "#2B4C9B"), "entity": meta.get("color_entity", "#5D3A8E"),
                    "callout": meta.get("color_callout", "#1A6E4A"), "warning": meta.get("color_warning", "#C0392B"),
                    "border": meta.get("color_border", "#888888"), "text": meta.get("color_text", "#000000"),
                    "heading_font": meta.get("font_heading"), "body_font": meta.get("font_body"),
                }

        docx_exp.export(result["document"], path, palette=docx_palette, decorate=decorate, border=border,
                         decoration_style=decoration_style, theme=theme)
        return send_file(path, as_attachment=True, download_name=filename,
                         mimetype="application/vnd.openxmlformats-officedocument.wordprocessingml.document")
    except Exception as e:
        traceback.print_exc()  # full traceback -> server console, for debugging
        return jsonify({"error": str(e)}), 500


@app.route("/api/export/pptx", methods=["POST"])
def export_pptx():
    """PowerPoint export via Presentation Engine."""
    data       = request.get_json(force=True)
    raw_text   = data.get("content", "")
    session_id = data.get("session_id", "")
    theme      = data.get("theme", "auto")
    pptx_mode  = data.get("pptx_mode", "presenter")
    decorate   = bool(data.get("decorate", False))
    decoration_style = data.get("decoration_style", "auto")
    filename   = _safe_export_name(data.get("filename", "document"), ".pptx")
    path       = os.path.join(EXPORTS_DIR, filename)

    if pptx_mode not in ("presenter", "detailed"):
        pptx_mode = "presenter"

    try:
        if session_id and session_id in _upload_store:
            info   = _upload_store[session_id]
            result = _run_for_session(info, theme, "document", "", "unicode")
        elif raw_text:
            result = pipeline.run(raw_text, theme=theme, mode="document")
        else:
            return jsonify({"error": "No content provided for PPTX export"}), 400

        custom_palette = None
        if theme == "auto":
            design = _safe_auto_design(result["document"])
            if design:
                custom_palette = auto_designer.to_pptx_palette(design)

        pptx_bytes = generate_pptx(result["document"], theme=theme, mode=pptx_mode,
                                    custom_palette=custom_palette,
                                    decorate=decorate, decoration_style=decoration_style)
        with open(path, "wb") as fh:
            fh.write(pptx_bytes)
        return send_file(path, as_attachment=True, download_name=filename,
                         mimetype="application/vnd.openxmlformats-officedocument.presentationml.presentation")
    except Exception as e:
        traceback.print_exc()  # full traceback -> server console, for debugging
        return jsonify({"error": f"PPTX export failed: {e}"}), 500


# ── THEMES ─────────────────────────────────────────────────────────────────────

@app.route("/api/themes", methods=["GET"])
def get_themes():
    return jsonify(theme_eng.get_all_themes())

@app.route("/api/themes/<theme_id>/defaults", methods=["GET"])
def get_theme_defaults(theme_id):
    return jsonify(theme_eng.get_theme_defaults(theme_id))

@app.route("/api/theme/import", methods=["POST"])
def import_theme():
    """
    Extract colors/fonts from an already-designed document (.docx or .html,
    uploaded as a file, or raw HTML pasted as JSON) so it can be tweaked in
    the Designer and/or saved directly as a reusable theme preset.

    If the caller also supplies `content` (the document currently loaded in
    the editor — plain text/Markdown, not the source of the import), the
    response includes `preview_html`: that document rendered with the
    freshly extracted design applied, through the exact same
    properties+elements -> CSS path a saved custom theme uses. This lets the
    UI show a real, full rendering immediately after import instead of a
    handful of color swatches, so a person can actually judge "does this
    look like the design I imported" before saving it as a preset.
    """
    html_text = None
    docx_path = None
    tmp_path = None
    source_name = "Imported Design"
    preview_content = None

    if "file" in request.files:
        f = request.files["file"]
        if not f.filename:
            return jsonify({"error": "No file selected"}), 400
        ext = os.path.splitext(f.filename)[1].lower()
        if ext not in (".docx", ".html", ".htm"):
            return jsonify({"error": f"Unsupported type '{ext}'. Use .docx or .html"}), 400
        source_name = os.path.splitext(f.filename)[0]
        tmp_path = os.path.join(_UPLOAD_DIR, f"_import_{uuid.uuid4()}{ext}")
        f.save(tmp_path)
        if ext == ".docx":
            docx_path = tmp_path
        else:
            with open(tmp_path, "r", encoding="utf-8", errors="ignore") as fh:
                html_text = fh.read()
        preview_content = request.form.get("content", "")
    else:
        data = request.get_json(force=True)
        html_text = data.get("html", "")
        if not html_text:
            return jsonify({"error": "No file or HTML provided"}), 400
        preview_content = data.get("content", "")

    try:
        if docx_path:
            result = theme_extractor.extract_from_docx(docx_path)
        else:
            result = theme_extractor.extract_from_html(html_text)
        result["suggested_name"] = source_name.replace("_", " ").replace("-", " ").title()
        result["source_type"] = "docx" if docx_path else "html"

        if preview_content and preview_content.strip():
            try:
                css = theme_eng.build_css_from_properties(
                    "imported", result.get("properties", {}), result.get("elements")
                )
                preview = pipeline.run(preview_content, theme="custom:", custom_css=css)
                result["preview_html"] = preview["html"]
            except Exception:
                # Preview is a nice-to-have on top of the extraction result
                # itself; never fail the whole import over a rendering hiccup.
                result["preview_html"] = None

        return jsonify(result)
    except Exception as e:
        traceback.print_exc()  # full traceback -> server console, for debugging
        return jsonify({"error": f"Import failed: {e}"}), 500
    finally:
        if tmp_path and os.path.exists(tmp_path):
            try:
                os.remove(tmp_path)
            except OSError:
                pass


@app.route("/api/themes/custom", methods=["GET"])
def list_custom_themes():
    return jsonify(theme_eng.list_custom_themes())

@app.route("/api/themes/custom", methods=["POST"])
def save_custom_theme():
    data     = request.get_json(force=True)
    theme_id = data.get("id", "").strip()
    name     = data.get("name", "").strip()
    if not theme_id or not name:
        return jsonify({"error": "id and name are required"}), 400
    if theme_id in THEME_META:
        return jsonify({"error": "Cannot overwrite a built-in theme ID"}), 400
    saved = theme_eng.save_custom_theme(
        theme_id    = theme_id,
        name        = name,
        description = data.get("description", ""),
        properties  = data.get("properties", {}),
        icon        = data.get("icon", "🎨"),
        elements    = data.get("elements", {}),
    )
    return jsonify(saved)

@app.route("/api/themes/custom/<theme_id>", methods=["GET"])
def get_custom_theme(theme_id):
    t = theme_eng.load_custom_theme(theme_id)
    if not t:
        return jsonify({"error": "Not found"}), 404
    return jsonify(t)

@app.route("/api/themes/custom/<theme_id>", methods=["DELETE"])
def delete_custom_theme(theme_id):
    if not theme_eng.delete_custom_theme(theme_id):
        return jsonify({"error": "Not found"}), 404
    return jsonify({"deleted": theme_id})

@app.route("/api/themes/export/<theme_id>", methods=["GET"])
def export_theme_json(theme_id):
    from app.themes.theme_engine import THEME_DEFAULTS
    if theme_id in THEME_META:
        data = {"id": theme_id, "name": THEME_META[theme_id]["name"],
                "description": THEME_META[theme_id]["description"],
                "icon": THEME_META[theme_id]["icon"],
                "properties": THEME_DEFAULTS.get(theme_id, {})}
    else:
        data = theme_eng.load_custom_theme(theme_id)
        if not data:
            return jsonify({"error": "Not found"}), 404
    filename = _safe_export_name(f"theme_{theme_id}", ".json")
    path = os.path.join(EXPORTS_DIR, filename)
    with open(path, "w") as fh:
        json.dump(data, fh, indent=2)
    return send_file(path, as_attachment=True, download_name=filename,
                     mimetype="application/json")

@app.route("/api/health", methods=["GET"])
def health():
    return jsonify({"status": "ok", "version": "1.3.0"})


if __name__ == "__main__":
    app.run(debug=True, port=5000)

#!/usr/bin/env python3
"""
Information Architecture Studio — CLI

Usage:
  python ias.py transform <input_file> [--theme THEME] [--mode MODE] [--out OUTPUT]
  python ias.py serve [--port PORT]
  python ias.py themes
"""
import argparse
import os
import sys


def cmd_transform(args):
    from app.pipeline import Pipeline
    from app.exporters.exporters import PDFExporter, DOCXExporter

    pipeline = Pipeline()
    print(f"📄 Processing: {args.input}")
    result = pipeline.run_from_file(args.input, theme=args.theme, mode=args.mode)

    doc = result["document"]
    print(f"✅ Project type : {result['project_type']} ({result['type_confidence']:.0f}%)")
    print(f"   Blocks found : {result['block_count']}")
    print(f"   Theme        : {args.theme}")
    print(f"   Mode         : {args.mode}")

    # Determine output path
    base = os.path.splitext(args.input)[0]
    out = args.out or (base + ".html")
    ext = os.path.splitext(out)[1].lower()

    if ext == ".html":
        with open(out, "w", encoding="utf-8") as f:
            f.write(result["html"])
        print(f"📁 HTML saved   : {out}")

    elif ext == ".pdf":
        PDFExporter().export(result["html"], out)
        print(f"📁 PDF saved    : {out}")

    elif ext == ".docx":
        DOCXExporter().export(doc, out)
        print(f"📁 DOCX saved   : {out}")

    else:
        # Default to HTML
        out_html = out + ".html"
        with open(out_html, "w", encoding="utf-8") as f:
            f.write(result["html"])
        print(f"📁 HTML saved   : {out_html}")

    # Print top entities
    entities = doc.get_top_entities(5)
    if entities:
        print("\n🔑 Top entities:")
        for e in entities:
            print(f"   [{e.importance_score:5.1f}] {e.content}")

    # Print critical blocks
    critical = doc.get_critical_blocks(threshold=75)
    if critical:
        print(f"\n⚠  Critical blocks ({len(critical)}):")
        for b in critical[:4]:
            snippet = b.content[:70] + ("…" if len(b.content) > 70 else "")
            print(f"   [{b.type.value:14s}] {snippet}")


def cmd_serve(args):
    sys.path.insert(0, os.path.dirname(__file__))
    from app_server import app
    print(f"🚀 Starting IAS server on http://localhost:{args.port}")
    app.run(debug=args.debug, port=args.port, host="0.0.0.0")


def cmd_themes(_args):
    from app.themes.theme_engine import THEME_META
    print("\n🎨 Available themes:\n")
    for tid, meta in THEME_META.items():
        print(f"  {meta['icon']}  {tid:12s}  {meta['name']}")
        print(f"              {meta['description']}")
    print()


def main():
    parser = argparse.ArgumentParser(
        prog="ias",
        description="Information Architecture Studio — transform structured content into beautiful documents"
    )
    sub = parser.add_subparsers(dest="command")

    # transform
    from app.themes.theme_engine import THEME_META
    t = sub.add_parser("transform", help="Process a file through the pipeline")
    t.add_argument("input", help="Input file (.md, .txt, .docx, .html)")
    t.add_argument("--theme", default="auto",
                   choices=["auto"] + sorted(THEME_META.keys()),
                   help="Output theme (default: auto — analyzes the "
                        "document and generates a bespoke design)")
    t.add_argument("--mode", default="document",
                   choices=["document","slides","brief"],
                   help="Render mode (default: document)")
    t.add_argument("--out", default=None,
                   help="Output file path (.html, .pdf, .docx). Defaults to <input>.html")

    # serve
    s = sub.add_parser("serve", help="Start the web interface")
    s.add_argument("--port", type=int, default=5000)
    s.add_argument("--debug", action="store_true")

    # themes
    sub.add_parser("themes", help="List available themes")

    args = parser.parse_args()

    if args.command == "transform":
        cmd_transform(args)
    elif args.command == "serve":
        cmd_serve(args)
    elif args.command == "themes":
        cmd_themes(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()

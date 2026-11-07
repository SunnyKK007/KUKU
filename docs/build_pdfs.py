"""Render docs/*_solution.md to PDF with headless Chrome and report page counts.
Usage: python3 docs/build_pdfs.py"""
import pathlib
import subprocess

import markdown
from pypdf import PdfReader

HERE = pathlib.Path(__file__).parent
CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
CSS = """
@page { size: A4; margin: 13mm 14mm; }
body { font: 9.6pt/1.38 -apple-system, "Helvetica Neue", Arial, sans-serif; color: #1b1b1b; }
h1 { font-size: 15pt; margin: 0 0 4px; } h2 { font-size: 11pt; margin: 9px 0 3px; border-bottom: 1px solid #ddd; }
p { margin: 3px 0; } ul, ol { margin: 2px 0 3px 18px; padding: 0; } li { margin: 1px 0; }
table { border-collapse: collapse; width: 100%; margin: 3px 0; font-size: 8.8pt; }
th, td { border: 1px solid #d6d6d6; padding: 2px 5px; text-align: left; vertical-align: top; }
th { background: #f2f2f2; } code { font-size: 8.6pt; background: #f4f4f4; padding: 0 2px; }
"""

def fix_lists(text: str) -> str:
    """Python-Markdown needs a blank line before a list that follows a paragraph."""
    import re
    out, prev = [], ""
    for line in text.splitlines():
        is_item = bool(re.match(r"^(\s*[-*] |\d+\. )", line))
        prev_item = bool(re.match(r"^(\s*[-*] |\d+\. )", prev))
        if is_item and prev.strip() and not prev_item:
            out.append("")
        out.append(line)
        prev = line
    return "\n".join(out)


for md_file in sorted(HERE.glob("*_solution.md")):
    html = markdown.markdown(fix_lists(md_file.read_text()), extensions=["tables"])
    html_file = md_file.with_suffix(".html")
    html_file.write_text(f"<!doctype html><html><head><meta charset='utf-8'><style>{CSS}</style></head><body>{html}</body></html>")
    pdf = md_file.with_suffix(".pdf")
    subprocess.run([CHROME, "--headless=new", "--disable-gpu", "--no-pdf-header-footer",
                    f"--print-to-pdf={pdf}", html_file.as_uri()], check=True, capture_output=True)
    html_file.unlink()
    print(f"{pdf.name}: {len(PdfReader(str(pdf)).pages)} page(s)")

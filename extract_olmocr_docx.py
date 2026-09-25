#!/usr/bin/env python3
"""Extract full text of the previous OLMoCR decision report (docx) for reconciliation.
Read-only extraction: unzip word/document.xml, strip tags, print paragraphs."""
import re
import sys
import zipfile

DOCX = "/home/z/my-project/download/olmocr-decision-report/OLMoCR_INTEGRATION_DECISION_REPORT.docx"

def main() -> int:
    with zipfile.ZipFile(DOCX) as z:
        xml = z.read("word/document.xml").decode("utf-8", errors="replace")
    # Paragraph boundaries -> newlines, then strip all tags
    xml = re.sub(r"</w:p>", "\n", xml)
    xml = re.sub(r"<w:tab[^>]*/>", "\t", xml)
    text = re.sub(r"<[^>]+>", "", xml)
    text = re.sub(r"\n{3,}", "\n\n", text)
    lines = [ln.rstrip() for ln in text.splitlines()]
    out = "\n".join(lines)
    sys.stdout.write(out)
    sys.stdout.write("\n")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())

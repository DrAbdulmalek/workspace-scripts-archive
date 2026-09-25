#!/usr/bin/env python3
"""Extract full text + tables from the comprehensive report docx for audit.
Outputs to /home/z/my-project/scripts/report_extract.txt (no secrets involved).
"""
import docx

SRC = '/home/z/my-project/download/omni-session-comprehensive-report-2026-09-19.docx'
OUT = '/home/z/my-project/scripts/report_extract.txt'

d = docx.Document(SRC)
lines = []

# Walk body elements in order (paragraphs + tables interleaved)
from docx.oxml.ns import qn

body = d.element.body
tbl_idx = 0
for child in body.iterchildren():
    if child.tag == qn('w:p'):
        # paragraph text
        texts = child.xpath('.//w:t')
        txt = ''.join(t.text or '' for t in texts)
        if txt.strip():
            lines.append(txt)
    elif child.tag == qn('w:tbl'):
        tbl_idx += 1
        # find the matching table object
        t = d.tables[tbl_idx - 1]
        lines.append(f'<<<TABLE {tbl_idx}: {len(t.rows)} rows x {len(t.columns)} cols>>>')
        for r_i, row in enumerate(t.rows):
            cells = [c.text.replace('\n', ' / ').strip() for c in row.cells]
            lines.append(f'  T{tbl_idx}R{r_i}: ' + ' | '.join(cells))
        lines.append(f'<<<END TABLE {tbl_idx}>>>')

with open(OUT, 'w', encoding='utf-8') as f:
    f.write('\n'.join(lines))

print(f'paragraph+table lines: {len(lines)}')
print(f'tables: {tbl_idx}')
print(f'written: {OUT}')

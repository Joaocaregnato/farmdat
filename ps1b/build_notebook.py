"""Build ps1b.ipynb from ps1b.py: one markdown heading + one code cell per section banner."""
import re, sys
import nbformat as nbf

src = open(sys.argv[1] if len(sys.argv) > 1 else "ps1b.py").read().replace("# %%\n", "")   # drop Spyder/VS Code cell markers
banner = re.compile(r"^# -{20,}\n# (.+)\n# -{20,}\n", re.M)
parts = banner.split(src)            # [pre, title1, body1, title2, body2, ...]
pre, rest = parts[0], parts[1:]

nb = nbf.v4.new_notebook()
cells = [nbf.v4.new_markdown_cell(
    "# Problem Set 1b: BHARs and calendar-time portfolios after stock splits\n\n"
    "**How to run.** Put the seven CSV files in `DATA_DIR` (set in the first code cell; default `C:\\Users\\joaoac2\\Downloads\\PS1b\\data`) and run all cells. "
    "Tables (`.tex` + `.csv`) and figures (`.png`) are written to `OUT_DIR` (default: `output` next to `data`). "
    "Every `[CHECK]` line is a sanity check; the full list is saved in `sanity_checks.csv`.\n\n"
    "**Sections:** setup and data checks -> Q1 event panel -> Q2 BHAR -> Q3 size-decile benchmark (+ Q4 skewness-adjusted t) -> Q5 calendar-time portfolio -> "
    "Q6 factor regressions -> Q8 weighting -> robustness -> Q6/Q7 supporting tables -> save checks.")]
doc = re.match(r'\s*"""(.*?)"""', pre, re.S)
body = pre[doc.end():] if doc else pre
cells.append(nbf.v4.new_code_cell(body.strip("\n")))
for title, code in zip(rest[0::2], rest[1::2]):
    cells.append(nbf.v4.new_markdown_cell("## " + title.strip()))
    if code.strip():
        cells.append(nbf.v4.new_code_cell(code.strip("\n")))
nb["cells"] = cells
nb.metadata["kernelspec"] = {"display_name": "Python 3", "language": "python", "name": "python3"}
nbf.write(nb, "ps1b.ipynb")
print(len(cells), "cells")

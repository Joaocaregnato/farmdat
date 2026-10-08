# PS1b - BHAR and calendar-time portfolios (stock splits)

* `ps1b.ipynb` - the analysis as a Jupyter notebook (Q1-Q8), already executed so tables, checks and charts are visible.
  Set `DATA_DIR` in the first code cells (default `C:\Users\joaoac2\Downloads\PS1b\data`, or env var `PS1B_DATA_DIR`) and run all cells.
  Outputs go to `DATA_DIR/../output` (or `PS1B_OUT_DIR`): tables as `.tex` + `.csv`, figures as `.png`, `sanity_checks.csv`.
* `ps1b.py` - the same code as a plain script (the notebook is generated from it with `build_notebook.py`).
* Data folder must hold: `stock_splits.csv`, `stock_daily.csv`, `F-F_Research_Data_Factors.csv`, `F-F_Research_Data_5_Factors_2x3.csv`,
  `F-F_Momentum_Factor.csv`, `ME_Breakpoints.csv`, `Portfolios_Formed_on_ME.csv` (CSV files unzipped from Kenneth French's library).
* `overleaf/` - upload this folder to Overleaf (`main.tex`, `tables/`, `figures/`). After re-running, copy `output/*.tex` into
  `overleaf/tables/` and `output/fig*.png` into `overleaf/figures/`.
* `data/` is not committed (course data are private). Install packages with `pip install -r requirements.txt`.

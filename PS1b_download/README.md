# PS1b - BHAR and calendar-time portfolios (stock splits)

* `ps1b.py` - full analysis (Q1-Q8). Set `DATA_DIR` (default `C:\Users\joaoac2\Downloads\PS1b\data`, or env var `PS1B_DATA_DIR`);
  outputs go to `DATA_DIR/../output` (or `PS1B_OUT_DIR`): tables as `.tex` + `.csv`, figures `.png`, `sanity_checks.csv`, `run_log.txt`.
* Data folder must hold: `stock_splits.csv`, `stock_daily.csv`, `F-F_Research_Data_Factors.csv`, `F-F_Research_Data_5_Factors_2x3.csv`,
  `F-F_Momentum_Factor.csv`, `ME_Breakpoints.csv`, `Portfolios_Formed_on_ME.csv` (CSV files unzipped from Kenneth French's library).
* `overleaf/` - upload this folder to Overleaf (`main.tex`, `tables/`, `figures/`). After re-running the script, copy `output/*.tex` into
  `overleaf/tables/` and `output/fig*.png` into `overleaf/figures/`.
* `data/` is not committed (course data are private).

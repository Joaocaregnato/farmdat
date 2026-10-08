"""
PS1b - BHAR and Calendar-Time Portfolios (stock splits)

Run:  python ps1b.py
Data folder (CSV files from the course zip + Kenneth French files) is DATA_DIR.
All tables (.tex and .csv) and figures (.png) are written to OUT_DIR.

Unit of observation
  - event panel:   one row per (split event, month tau = +1..+12)
  - calendar-time: one row per calendar month (portfolio return)
Returns are decimals everywhere except in the printed regression tables, where
alphas are shown in percent per month (French's factor files are divided by 100).
"""
import os
import re
import json
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import statsmodels.api as sm
from scipy import stats

# --------------------------------------------------------------------------
# Paths (override with environment variables if needed)
# --------------------------------------------------------------------------
DATA_DIR = Path(os.environ.get("PS1B_DATA_DIR", r"C:\Users\joaoac2\Downloads\PS1b\data"))
OUT_DIR = Path(os.environ.get("PS1B_OUT_DIR", str(DATA_DIR.parent / "output")))
OUT_DIR.mkdir(parents=True, exist_ok=True)

DATA_END_MI = 2025 * 12 + 11          # December 2025 as integer month index (year*12 + month-1)
NW_LAGS = 6                           # Newey-West lags (monthly data, 12-month overlapping holdings)
CHECKS = []                           # sanity checks collected for the appendix


def mi_to_str(mi):
    return f"{mi // 12}-{mi % 12 + 1:02d}"


def check(name, value, note=""):
    """Print and store a sanity check."""
    CHECKS.append({"check": name, "value": value, "note": note})
    print(f"[CHECK] {name}: {value}  {note}")


def save_table(df, name, caption, label, index=True, colfmt=None):
    """Plain pandas tables: .csv and a default (unstyled) .tex file (colfmt only sets column widths)."""
    df.to_csv(OUT_DIR / f"{name}.csv", index=index)
    df.to_latex(OUT_DIR / f"{name}.tex", index=index, escape=True, caption=caption, label=label, column_format=colfmt, float_format="%.3f")
    print(f"\n=== {name} ===\n{df.to_string()}\n")


# --------------------------------------------------------------------------
# French data parsers
# --------------------------------------------------------------------------
def read_french_block(path, block=0):
    """Return the `block`-th contiguous block of 'yyyymm, v1, v2...' rows with its header line."""
    lines = Path(path).read_text(encoding="latin-1").splitlines()
    pat = re.compile(r"^\s*\d{6}\s*,")
    blocks, cur, start = [], [], None
    for i, ln in enumerate(lines):
        if pat.match(ln):
            if not cur:
                start = i
            cur.append(ln)
        elif cur:
            blocks.append((start, cur))
            cur = []
    if cur:
        blocks.append((start, cur))
    start, rows = blocks[block]
    header = lines[start - 1]
    return header, rows


def parse_french(path, block=0, header=None):
    hdr, rows = read_french_block(path, block)
    cols = header if header is not None else [c.strip() for c in hdr.split(",")][1:]
    recs = []
    for r in rows:
        parts = [p.strip() for p in r.split(",") if p.strip() != ""]
        recs.append(parts)
    df = pd.DataFrame(recs)
    df = df.apply(pd.to_numeric)
    ym = df.iloc[:, 0].astype(int)
    df = df.iloc[:, 1:]
    df.columns = cols[: df.shape[1]]
    df.index = (ym // 100) * 12 + (ym % 100) - 1       # month index
    df.index.name = "mi"
    df = df.replace([-99.99, -999, -999.0], np.nan)
    return df


# --------------------------------------------------------------------------
# 0. Load data
# --------------------------------------------------------------------------
daily = pd.read_csv(DATA_DIR / "stock_daily.csv", parse_dates=["date"])
splits = pd.read_csv(DATA_DIR / "stock_splits.csv", parse_dates=["disdeclaredt", "disexdt"])

check("daily rows", len(daily), "(manifest: 629,274)")
check("split events", len(splits), "(manifest: 232)")
check("daily duplicates (permno,date)", int(daily.duplicated(["permno", "date"]).sum()))
check("daily missing ret / mkt_ret / mktcap", f"{int(daily.ret.isna().sum())} / {int(daily.mkt_ret.isna().sum())} / {int(daily.mktcap.isna().sum())}")
check("distinct permnos in daily", daily.permno.nunique())
check("event permnos missing from daily", int((~splits.permno.isin(daily.permno)).sum()))
check("duplicated event_id", int(splits.event_id.duplicated().sum()))
check("ex-date range", f"{splits.disexdt.min().date()} to {splits.disexdt.max().date()}")
check("ex-date before declaration date", int((splits.disexdt < splits.disdeclaredt).sum()))
check("daily ret min / max", f"{daily.ret.min():.3f} / {daily.ret.max():.3f}", "decimal returns; max is a real +1140% (penny-stock) day, kept")
mk_per_date = daily.groupby("date").mkt_ret.nunique()
check("dates with >1 distinct mkt_ret", int((mk_per_date > 1).sum()), "mkt_ret is one series")

daily = daily.sort_values(["permno", "date"]).reset_index(drop=True)
cal = np.sort(daily.date.unique())                       # market trading calendar
cal_idx = pd.Series(np.arange(len(cal)), index=pd.DatetimeIndex(cal))
mkt_daily = daily.groupby("date").mkt_ret.first()
check("trading days in calendar", len(cal), "(approx. 252 x 14 = 3,528)")

# --------------------------------------------------------------------------
# 1. Fill empty returns inside a stock's history with the market return
# --------------------------------------------------------------------------
daily["ci"] = daily.date.map(cal_idx)
daily["mi"] = daily.date.dt.year * 12 + daily.date.dt.month - 1
span = daily.groupby("permno").ci.agg(["min", "max"])
grid = pd.concat([pd.DataFrame({"permno": p, "ci": np.arange(lo, hi + 1)}) for p, (lo, hi) in span.iterrows()],
                 ignore_index=True)
grid = grid.merge(daily[["permno", "ci", "ret", "mktcap"]], on=["permno", "ci"], how="left")
grid["date"] = pd.DatetimeIndex(cal)[grid.ci]
grid["mi"] = grid.date.dt.year * 12 + grid.date.dt.month - 1
grid["mkt_ret"] = grid.date.map(mkt_daily)
grid["actual"] = grid.ret.notna()
# a month with NO actual observation is a "stops trading" month (handled in the event panel),
# so empty days are filled only in months where the stock has at least one real return
n_act = grid.groupby(["permno", "mi"]).actual.transform("sum")
n_grid_total = len(grid)
grid = grid[n_act > 0].copy()
n_dropped_empty_months = n_grid_total - len(grid)
to_fill = grid.ret.isna()
check("explicit NaN ret in raw file", int(daily.ret.isna().sum()))
check("empty stock-days inside stock history filled with mkt_ret", int(to_fill.sum()),
      f"({to_fill.mean():.4%} of {len(grid):,} stock-days)")
check("stock-days in wholly-empty months (not filled, month treated as 'stopped trading')", n_dropped_empty_months)
grid.loc[to_fill, "ret"] = grid.loc[to_fill, "mkt_ret"]
check("remaining NaN returns after fill", int(grid.ret.isna().sum()))
check("filled-days by permno (top 5)", grid[to_fill].groupby("permno").size().sort_values(ascending=False).head(5).to_dict())

# --------------------------------------------------------------------------
# 2. Monthly returns (compounded daily), monthly market return, end-of-month cap
# --------------------------------------------------------------------------
grid["lr"] = np.log1p(grid.ret)
mon = grid.groupby(["permno", "mi"]).agg(ret=("lr", lambda x: np.expm1(x.sum())), ndays=("lr", "size")).reset_index()
last_cap = (grid[grid.actual].sort_values("date").groupby(["permno", "mi"]).mktcap.last()
            .rename("mktcap_end").reset_index())
mon = mon.merge(last_cap, on=["permno", "mi"], how="left")
mon_stock = mon.set_index(["permno", "mi"]).sort_index()
check("monthly stock-months", len(mon_stock))
check("monthly stock-return range", f"{mon_stock.ret.min():.3f} to {mon_stock.ret.max():.3f}")

mk = pd.DataFrame({"mkt_ret": mkt_daily})
mk["mi"] = mk.index.year * 12 + mk.index.month - 1
mon_mkt = mk.groupby("mi").mkt_ret.agg(lambda x: np.expm1(np.log1p(x).sum()))
ndays_mkt = mk.groupby("mi").size()
check("market days per month: min / max", f"{ndays_mkt.min()} / {ndays_mkt.max()}", "(expect ~19-23)")
check("monthly market return mean / sd (decimal)", f"{mon_mkt.mean():.4f} / {mon_mkt.std():.4f}")

# --------------------------------------------------------------------------
# 3. French data
# --------------------------------------------------------------------------
ff3 = parse_french(DATA_DIR / "F-F_Research_Data_Factors.csv", 0) / 100
ff5 = parse_french(DATA_DIR / "F-F_Research_Data_5_Factors_2x3.csv", 0) / 100
mom = parse_french(DATA_DIR / "F-F_Momentum_Factor.csv", 0) / 100
mom.columns = [c.strip() for c in mom.columns]
dec_names = ["Lo 10", "2-Dec", "3-Dec", "4-Dec", "5-Dec", "6-Dec", "7-Dec", "8-Dec", "9-Dec", "Hi 10"]
hdr_me, _ = read_french_block(DATA_DIR / "Portfolios_Formed_on_ME.csv", 0)
assert "Hi 10" in hdr_me, "first block of Portfolios_Formed_on_ME is not the value-weighted block"
me_vw = parse_french(DATA_DIR / "Portfolios_Formed_on_ME.csv", 0)[dec_names] / 100
bp_raw = parse_french(DATA_DIR / "ME_Breakpoints.csv", 0,
                      header=["n_nyse"] + [f"p{5 * k}" for k in range(1, 21)])
check("French monthly ranges (ff3 / ff5 / mom / ME-VW / ME bp)",
      f"{mi_to_str(ff3.index.min())}-{mi_to_str(ff3.index.max())} / {mi_to_str(ff5.index.min())}-{mi_to_str(ff5.index.max())} / "
      f"{mi_to_str(mom.index.min())}-{mi_to_str(mom.index.max())} / {mi_to_str(me_vw.index.min())}-{mi_to_str(me_vw.index.max())} / "
      f"{mi_to_str(bp_raw.index.min())}-{mi_to_str(bp_raw.index.max())}")
check("ff3 Mkt-RF mean / sd in 2014-2025 (decimal/month)",
      f"{ff3.loc[2014*12:2025*12+11, 'Mkt-RF'].mean():.4f} / {ff3.loc[2014*12:2025*12+11, 'Mkt-RF'].std():.4f}",
      "(units: percent/100)")
check("ME breakpoints monotone in p5..p100", bool((bp_raw.filter(like="p").diff(axis=1).iloc[:, 1:] > 0).all().all()))
check("ME-VW decile NaNs", int(me_vw.isna().sum().sum()))
common = ff3.index.intersection(ff5.index)
check("Mkt-RF ff3 vs ff5 max abs diff", float((ff3.loc[common, "Mkt-RF"] - ff5.loc[common, "Mkt-RF"]).abs().max()), "(<=0.08pp: file-vintage/rounding differences, immaterial)")
check("SMB ff3 vs ff5 max abs diff", float((ff3.loc[common, "SMB"] - ff5.loc[common, "SMB"]).abs().max()), "(SMB differs: 3-factor file sorts on size/B-M, 5-factor file averages SMB over B/M, OP and Inv sorts)")

# Cross-check: monthly compounded mkt_ret vs French CRSP value-weighted market (Mkt-RF + RF)
frm = (ff3["Mkt-RF"] + ff3["RF"])
j = pd.concat([mon_mkt.rename("mine"), frm.rename("french")], axis=1, join="inner")
check("corr(compounded mkt_ret, French Mkt-RF+RF) monthly", f"{j.mine.corr(j.french):.5f}", f"over {len(j)} months")
check("max abs diff (compounded mkt_ret - French Mkt)", f"{(j.mine - j.french).abs().max():.4f}")
check("mean monthly diff (mkt_ret - French Mkt), and 2014-2025 compounded return of each",
      f"{(j.mine - j.french).mean():.5f}; {np.expm1(np.log1p(j.mine[j.index >= 2014 * 12]).sum()):.3f} vs {np.expm1(np.log1p(j.french[j.index >= 2014 * 12]).sum()):.3f}",
      "mkt_ret runs ~0.11pp/month (~1.4%/yr) BELOW French's market: BHAR benchmark is slightly easier than the factor-model market")

# --------------------------------------------------------------------------
# Q1. Event-time panel
# --------------------------------------------------------------------------
ev = splits.copy()
ev["m0"] = ev.disexdt.dt.year * 12 + ev.disexdt.dt.month - 1
ev["m0_has_obs"] = [(p, m) in mon_stock.index for p, m in zip(ev.permno, ev.m0)]
check("events with trading obs in month 0", f"{ev.m0_has_obs.sum()} of {len(ev)}")

pan = ev[["event_id", "permno", "m0"]].merge(pd.DataFrame({"tau": np.arange(1, 13)}), how="cross")
pan["mi"] = pan.m0 + pan.tau
pan = pan[pan.mi <= DATA_END_MI].copy()                          # data end cuts the window
pan = pan.merge(mon_stock[["ret", "mktcap_end"]].reset_index().rename(columns={"ret": "ret_stock"}),
                on=["permno", "mi"], how="left")
pan["ret_mkt"] = pan.mi.map(mon_mkt)
pan["has_obs"] = pan.ret_stock.notna()
stop_tau = pan[~pan.has_obs].groupby("event_id").tau.min().rename("stop_tau")
pan = pan.merge(stop_tau, on="event_id", how="left")
pan["held"] = pan.stop_tau.isna() | (pan.tau < pan.stop_tau)       # still holding the stock
pan["ret_used"] = np.where(pan.held, pan.ret_stock, pan.ret_mkt)    # proceeds go to mkt_ret after the stop
pan = pan.sort_values(["event_id", "tau"]).reset_index(drop=True)
check("panel rows with NaN ret_used", int(pan.ret_used.isna().sum()))
check("panel rows with NaN ret_mkt", int(pan.ret_mkt.isna().sum()))
check("monthly stock return inside event windows: min / max", f"{pan.ret_stock.min():.3f} / {pan.ret_stock.max():.3f}",
      "the four >+200% single-day spikes in the file (micro-caps, real cap jumps) fall outside all event windows")

ev["n_months"] = ev.event_id.map(pan.groupby("event_id").size()).fillna(0).astype(int)
ev["cut_data_end"] = ev.m0 + 12 > DATA_END_MI
ev["cut_stop"] = ev.event_id.isin(stop_tau.index)
ev["stop_tau"] = ev.event_id.map(stop_tau)
ev["full12"] = ev.n_months == 12
ev["bhar_ok"] = ~ev.cut_data_end                                  # month +12 on or before Dec 2025
q1 = pd.Series({
    "Split events (stock_splits.csv)": len(ev),
    "Events with at least one window month <= Dec 2025": int((ev.n_months > 0).sum()),
    "Events whose ex-date month is Dec 2025 (no window month at all)": int((ev.n_months == 0).sum()),
    "Panel rows (event x month)": len(pan),
    "Cut short by data end (month +12 after Dec 2025)": int(ev.cut_data_end.sum()),
    "Cut short by stock stopping trading (in window, <= Dec 2025)": int(ev.cut_stop.sum()),
    "   of which also cut by data end": int((ev.cut_stop & ev.cut_data_end).sum()),
    "   stopped trading only (full 12 months, proceeds in market)": int((ev.cut_stop & ~ev.cut_data_end).sum()),
    "   stock has no data from month +1 (all 12 months = market)": int((ev.stop_tau == 1).sum()),
    "Complete events (12 months, never stops)": int((~ev.cut_data_end & ~ev.cut_stop).sum()),
    "Events with 12-month BHAR (month +12 <= Dec 2025)": int(ev.bhar_ok.sum()),
}).to_frame("Events")
save_table(q1, "table1_event_panel",
           "Q1: Event-time panel. Window = calendar months +1 to +12 after the ex-date month (month 0). "
           "'Cut short by data end' = month +12 falls after Dec 2025; 'cut short by stock stopping trading' = a window month "
           "up to Dec 2025 has no daily returns for the stock (proceeds are invested in mkt\\_ret for the rest of the window). "
           "The two reasons overlap for some events, so rows do not add up to the total.", "tab:q1", colfmt="p{11cm}r")
check("events by ex-year", ev.disexdt.dt.year.value_counts().sort_index().to_dict())
check("panel rows by tau (each should be <= #events)", pan.groupby("tau").size().to_dict())
check("expected panel rows = sum(min(12, DATA_END - m0))", int(np.clip(DATA_END_MI - ev.m0, 0, 12).sum()), f"observed {len(pan)}")

# independent recomputation of monthly returns for a handful of events directly from daily data
rng = np.random.default_rng(0)
sample = ev[ev.full12 & ~ev.cut_stop].sample(8, random_state=1)
maxdiff = 0
for _, r in sample.iterrows():
    lo = pd.Timestamp(year=(r.m0 + 1) // 12, month=(r.m0 + 1) % 12 + 1, day=1)
    hi = pd.Timestamp(year=(r.m0 + 12) // 12, month=(r.m0 + 12) % 12 + 1, day=1) + pd.offsets.MonthEnd(0)
    g = grid[(grid.permno == r.permno) & (grid.date >= lo) & (grid.date <= hi)]
    direct = np.prod(1 + g.ret.values) - np.prod(1 + g.mkt_ret.values)
    p = pan[pan.event_id == r.event_id]
    viapanel = np.prod(1 + p.ret_used) - np.prod(1 + p.ret_mkt)
    maxdiff = max(maxdiff, abs(direct - viapanel))
check("BHAR from panel vs direct daily compounding (8 random events), max abs diff", f"{maxdiff:.2e}")

# --------------------------------------------------------------------------
# Q2. BHAR vs market
# --------------------------------------------------------------------------
full = pan[pan.event_id.isin(ev[ev.bhar_ok].event_id)]
assert full.groupby("event_id").size().eq(12).all()
bhar = full.groupby("event_id").apply(lambda g: np.prod(1 + g.ret_used) - np.prod(1 + g.ret_mkt),
                                      include_groups=False).rename("bhar_mkt")
ev = ev.merge(bhar, left_on="event_id", right_index=True, how="left")
x = ev.bhar_mkt.dropna()


def bhar_stats(x):
    n = len(x)
    m, s = x.mean(), x.std(ddof=1)
    se = s / np.sqrt(n)
    g = ((x - m) ** 3).sum() / (n * s ** 3)
    S = m / s
    tsa = np.sqrt(n) * (S + g * S ** 2 / 3 + g / (6 * n))
    tcrit = stats.t.ppf(0.975, n - 1)
    return {
        "N events": n, "Mean": m, "Median": x.median(), "Std. dev.": s, "Std. error of mean": se,
        "t-statistic": m / se, "p-value (two-sided, t)": 2 * stats.t.sf(abs(m / se), n - 1),
        "Skewness (gamma-hat)": g, "p10": x.quantile(0.10), "p25": x.quantile(0.25),
        "p75": x.quantile(0.75), "p90": x.quantile(0.90), "Min": x.min(), "Max": x.max(),
        "Share of BHAR > 0": (x > 0).mean(),
        "t_SA (skewness-adjusted)": tsa,
        "Min. mean BHAR significant at 5%": tcrit * se,
        "Mean BHAR detectable with 80% power": (tcrit + stats.t.ppf(0.80, n - 1)) * se,
    }


st_mkt = bhar_stats(x)
stopped = ev[ev.cut_stop].copy()
last_dt = daily.groupby("permno").date.max()
stopped["last trading date in file"] = stopped.permno.map(last_dt).dt.date
stopped["Ex-date"] = stopped.disexdt.dt.date
stopped["First missing window month (tau)"] = stopped.stop_tau.astype(int)
save_table(stopped.set_index("event_id")[["permno", "Ex-date", "First missing window month (tau)", "last trading date in file"]]
           .rename(columns={"First missing window month (tau)": "First missing tau", "last trading date in file": "Last date in file"}),
           "table1b_stopped_events", "Q1 (check): the events whose window is cut short because the stock stops trading. For these events the "
           "proceeds go into mkt\\_ret from the first missing month (tau) to month +12. Permno 90400 has a long gap in its history "
           "(it trades again later, which the rule ignores).", "tab:q1b", colfmt="lrrrr")
fills = grid[to_fill][["permno", "mi"]].drop_duplicates()
n_ev_fill = int(sum(((fills.permno == p) & (fills.mi > m0) & (fills.mi <= m0 + 12)).any() for p, m0 in zip(ev.permno, ev.m0)))
check("events whose window contains a day filled with mkt_ret", n_ev_fill, "(only these events can be affected by the fill rule)")
# BHAR against French's market (Mkt-RF + RF) as a robustness check on the benchmark
pan["ret_frmkt"] = pan.mi.map(ff3["Mkt-RF"] + ff3["RF"])
fullb = pan[pan.event_id.isin(ev[ev.bhar_ok].event_id)]
bhar_fr = fullb.groupby("event_id").apply(lambda g: np.prod(1 + g.ret_used) - np.prod(1 + g.ret_frmkt), include_groups=False)
st_fr = bhar_stats(bhar_fr.dropna())
check("robustness: mean BHAR vs French market / t", f"{st_fr['Mean']:.4f} / {st_fr['t-statistic']:.2f}",
      "(provided mkt_ret is ~1.4%/yr lower than French's market)")
# clustering check: events in the same ex-date month share market shocks
cl = ev.dropna(subset=["bhar_mkt"]).assign(ym=lambda d: d.disexdt.dt.to_period("M"))
dev = cl.bhar_mkt - x.mean()
G = cl.ym.nunique()
se_cl = np.sqrt((dev.groupby(cl.ym).sum() ** 2).sum()) / len(cl) * np.sqrt(G / (G - 1))
check("SE of mean BHAR: iid vs clustered by ex-date month", f"{st_mkt['Std. error of mean']:.4f} vs {se_cl:.4f}", f"{G} clusters")
check("skewness gamma-hat vs scipy skew(bias=True)", f"{st_mkt['Skewness (gamma-hat)']:.3f} vs {stats.skew(x):.3f}")
check("events with stop at tau=1 (whole window = market, BHAR = 0)", int((ev.stop_tau == 1).sum()))
check("BHAR min / max", f"{x.min():.3f} / {x.max():.3f}", "BHAR >= -(1 + market return): sanity ok if min > -1.5")

fig, ax = plt.subplots()
ax.hist(x, bins=40)
ax.axvline(x.mean(), linestyle="--", label=f"mean = {x.mean():.3f}")
ax.axvline(x.median(), linestyle=":", label=f"median = {x.median():.3f}")
ax.set_xlabel("12-month BHAR vs. value-weighted market (decimal)")
ax.set_ylabel("Number of events")
ax.set_title(f"Histogram of 12-month BHARs (N = {len(x)})")
ax.legend()
fig.savefig(OUT_DIR / "fig1_bhar_hist.png", dpi=200, bbox_inches="tight")
plt.close(fig)

# --------------------------------------------------------------------------
# Q3. BHAR vs NYSE size-decile benchmark
# --------------------------------------------------------------------------
cap0 = [mon_stock.mktcap_end.get((p, m), np.nan) for p, m in zip(ev.permno, ev.m0)]
ev["cap0_mil"] = np.array(cap0) / 1000.0                              # thousands of dollars -> millions
bp_dec = bp_raw[[f"p{10 * k}" for k in range(1, 10)]]                # 10th ... 90th NYSE percentiles
dec = []
for m, c in zip(ev.m0, ev.cap0_mil):
    if np.isnan(c) or m not in bp_dec.index:
        dec.append(np.nan)
    else:
        dec.append(int(np.searchsorted(bp_dec.loc[m].values, c, side="left")) + 1)
ev["decile"] = dec
check("events with size decile assigned", f"{ev.decile.notna().sum()} of {len(ev)}")
check("cap at month 0: median / min / max ($ millions)", f"{ev.cap0_mil.median():,.0f} / {ev.cap0_mil.min():,.1f} / {ev.cap0_mil.max():,.0f}",
      "mktcap file unit is $ thousands; divided by 1,000 to match French's $ millions")
dist = ev.decile.value_counts().sort_index().rename("Events").to_frame()
dist.index = [f"{int(i)}" for i in dist.index]
dist.index.name = "NYSE size decile (1 = smallest)"
dist["Share"] = dist.Events / dist.Events.sum()
save_table(dist.round(3), "table3_decile_dist",
           "Q3 (check): number of split events by NYSE size decile, assigned with market cap at the end of month 0 "
           "and French's NYSE ME breakpoints for that month (cap in $ thousands divided by 1,000 to match $ millions).", "tab:decile", colfmt="lrr")

dec_ret = me_vw.copy()
dec_ret.columns = range(1, 11)
pan["decile"] = pan.event_id.map(ev.set_index("event_id").decile)
pan["ret_dec"] = [dec_ret.at[m, int(d)] if (not np.isnan(d) and m in dec_ret.index) else np.nan
                  for m, d in zip(pan.mi, pan.decile)]
full = pan[pan.event_id.isin(ev[ev.bhar_ok].event_id)]
check("NaN decile benchmark returns in BHAR window", int(full.ret_dec.isna().sum()))
bhar_dec = full.groupby("event_id").apply(lambda g: np.prod(1 + g.ret_used) - np.prod(1 + g.ret_dec),
                                          include_groups=False).rename("bhar_dec")
bench_dec = full.groupby("event_id").apply(lambda g: np.prod(1 + g.ret_dec) - 1, include_groups=False).rename("bench_dec")
bench_mkt = full.groupby("event_id").apply(lambda g: np.prod(1 + g.ret_mkt) - 1, include_groups=False).rename("bench_mkt")
ev = ev.merge(bhar_dec, left_on="event_id", right_index=True, how="left") \
       .merge(bench_dec, left_on="event_id", right_index=True, how="left") \
       .merge(bench_mkt, left_on="event_id", right_index=True, how="left")
xd = ev.bhar_dec.dropna()
st_dec = bhar_stats(xd)
diff = (ev.bhar_dec - ev.bhar_mkt).dropna()        # = mkt benchmark return - decile benchmark return
st_diff = bhar_stats(diff)
check("mean 12m benchmark return: market vs size-decile", f"{ev.bench_mkt.mean():.4f} vs {ev.bench_dec.mean():.4f}")
check("diff = BHAR_dec - BHAR_mkt equals bench_mkt - bench_dec (max abs err)",
      f"{(diff + (ev.bench_dec - ev.bench_mkt).dropna()).abs().max():.2e}")

tab2 = pd.DataFrame({"vs. market": st_mkt, "vs. size decile": st_dec, "Difference": st_diff})
tab2_print = tab2.apply(lambda col: [f"{int(v)}" if k == "N events" else f"{v:.4f}" for k, v in col.items()]).set_index(tab2.index)
save_table(tab2_print, "table2_bhar_summary",
           "Q2-Q4: 12-month buy-and-hold abnormal returns (decimal; 0.10 = 10 percent). BHAR = stock gross return minus benchmark gross return "
           "over months +1 to +12. Column 'vs. market': benchmark = compounded mkt\\_ret. Column 'vs. size decile': benchmark = French value-weighted return of the event firm's NYSE size "
           "decile (month-0 cap). Column 'Difference': paired difference BHAR(decile) - BHAR(market) across the same events (its t-statistic tests whether the "
           "benchmark matters). Standard error = sd/sqrt(N). Skewness = gamma-hat of Q4. 't\\_SA' = Lyon-Barber-Tsai skewness-adjusted t. "
           "Last two rows: smallest mean BHAR significant at 5 percent (t critical value times SE) and mean BHAR detectable with 80 percent power "
           "((t critical + t at 80 percent) times SE).", "tab:bhar", colfmt="lrrr")
check("t-stat of paired difference (decile - market)", f"{st_diff['t-statistic']:.3f}")

# --------------------------------------------------------------------------
# Q5. Calendar-time portfolio (equal-weighted, each stock once per month)
# --------------------------------------------------------------------------
held = pan[pan.held][["event_id", "permno", "mi", "ret_stock"]].copy()
n_before = len(held)
held = held.drop_duplicates(["permno", "mi"])
check("held event-months before / after removing overlapping splits of the same stock", f"{n_before} / {len(held)}",
      f"{n_before - len(held)} duplicates removed")
check("held stock returns identical across duplicated events?",
      bool(pan[pan.held].groupby(["permno", "mi"]).ret_stock.nunique().max() == 1))
mon_p = held.groupby("mi").agg(rp=("ret_stock", "mean"), n=("permno", "size"))
months_all = np.arange(mon_p.index.min(), mon_p.index.max() + 1)
check("calendar months in portfolio span / with >=1 stock", f"{len(months_all)} / {len(mon_p)}")
check("portfolio span", f"{mi_to_str(mon_p.index.min())} to {mi_to_str(mon_p.index.max())}")
# weights sum to one
w_sum = held.groupby("mi").permno.transform(lambda s: 1 / len(s)).groupby(held.mi).sum()
check("EW weights sum to 1 in every month (max abs deviation)", f"{(w_sum - 1).abs().max():.2e}")
q5 = pd.Series({
    "Calendar months in portfolio": len(mon_p),
    "Average stocks held": mon_p.n.mean(),
    "Minimum stocks held": mon_p.n.min(),
    "Maximum stocks held": mon_p.n.max(),
    "Months with fewer than 10 stocks": int((mon_p.n < 10).sum()),
    "Months with zero stocks": len(months_all) - len(mon_p),
    "Mean monthly portfolio return": mon_p.rp.mean(),
    "Std. dev. of monthly portfolio return": mon_p.rp.std(),
}).to_frame("Value")
q5["Value"] = [f"{v:.0f}" if (isinstance(v, (int, np.integer)) or k in ("Minimum stocks held", "Maximum stocks held")) else f"{v:.4f}" for k, v in q5.Value.items()]
save_table(q5, "table5_portfolio", "Q5: equal-weighted calendar-time portfolio of stocks within months +1 to +12 of a split window "
           "(a stock with overlapping splits is held once; a stock is dropped after its last trading month).", "tab:q5", colfmt="p{9cm}r")
check("months with n<10: first / last", f"{mi_to_str(mon_p[mon_p.n < 10].index.min())} / {mi_to_str(mon_p[mon_p.n < 10].index.max())}"
      if (mon_p.n < 10).any() else "none")
check("portfolio monthly return range", f"{mon_p.rp.min():.3f} to {mon_p.rp.max():.3f}")
# the portfolio count must equal the count of unique permno-months implied by event windows
check("max stocks held <= number of distinct event permnos", f"{mon_p.n.max()} <= {ev.permno.nunique()}")

xm = pd.PeriodIndex([pd.Period(mi_to_str(m), "M") for m in mon_p.index]).to_timestamp()
fig, ax = plt.subplots(2, 1, sharex=True)
ax[0].plot(xm, mon_p.rp * 100, label="portfolio return")
ax[0].axhline(0, linewidth=0.5)
ax[0].set_ylabel("Monthly return (%)")
ax[0].set_title("Calendar-time portfolio: monthly return and number of stocks held")
ax[0].legend()
ax[1].plot(xm, mon_p.n, label="stocks held")
ax[1].set_ylabel("Number of stocks")
ax[1].set_xlabel("Month")
ax[1].legend()
fig.savefig(OUT_DIR / "fig2_portfolio.png", dpi=200, bbox_inches="tight")
plt.close(fig)

# --------------------------------------------------------------------------
# Q6. Factor regressions
# --------------------------------------------------------------------------
panel_m = mon_p.copy()
panel_m["rf"] = ff3.RF.reindex(panel_m.index)
for c in ["Mkt-RF", "SMB", "HML"]:
    panel_m[c] = ff3[c].reindex(panel_m.index)
panel_m["Mom"] = mom["Mom"].reindex(panel_m.index)
for c in ["Mkt-RF", "SMB", "HML", "RMW", "CMA"]:
    panel_m[c + "_5"] = ff5[c].reindex(panel_m.index)
panel_m["rf5"] = ff5.RF.reindex(panel_m.index)
panel_m["ex"] = panel_m.rp - panel_m.rf
check("months in portfolio missing French factors (3f / mom / 5f)",
      f"{int(panel_m['Mkt-RF'].isna().sum())} / {int(panel_m.Mom.isna().sum())} / {int(panel_m['Mkt-RF_5'].isna().sum())}")
check("RF mean (decimal/month) over sample", f"{panel_m.rf.mean():.5f}", "(about 1.75%/yr: near zero in 2014-2021, 4-5% in 2023-2025)")
check("RF ff3 vs ff5 identical", bool((panel_m.rf - panel_m.rf5).abs().max() < 1e-12))

MODELS = {
    "(1) No factors": [],
    "(2) CAPM": ["Mkt-RF"],
    "(3) FF3": ["Mkt-RF", "SMB", "HML"],
    "(4) FF3+Mom": ["Mkt-RF", "SMB", "HML", "Mom"],
    "(5) FF5": ["Mkt-RF_5", "SMB_5", "HML_5", "RMW_5", "CMA_5"],
}
LABEL = {"Mkt-RF_5": "Mkt-RF", "SMB_5": "SMB", "HML_5": "HML", "RMW_5": "RMW", "CMA_5": "CMA"}
ROWS = ["Mkt-RF", "SMB", "HML", "Mom", "RMW", "CMA"]


def fit(y, X, w=None, lags=NW_LAGS):
    Xc = sm.add_constant(X) if X is not None and X.shape[1] > 0 else pd.DataFrame({"const": np.ones(len(y))}, index=y.index)
    mod = sm.WLS(y, Xc, weights=w) if w is not None else sm.OLS(y, Xc)
    ols = mod.fit()
    nw = mod.fit(cov_type="HAC", cov_kwds={"maxlags": lags})
    return ols, nw


def reg_table(df, ycol, models, w=None, title=""):
    cols, res = {}, {}
    for name, fac in models.items():
        X = df[fac] if fac else None
        ols, nw = fit(df[ycol], X, w)
        res[name] = (ols, nw)
        c = {}
        c["alpha (% per month)"] = f"{ols.params['const'] * 100:.3f}"
        c["alpha t (OLS)"] = f"({ols.tvalues['const']:.2f})"
        c["alpha t (NW)"] = f"[{nw.tvalues['const']:.2f}]"
        for r in ROWS:
            src = [f for f in fac if LABEL.get(f, f) == r]
            if src:
                f = src[0]
                c[r] = f"{ols.params[f]:.3f}"
                c[f"{r} t (OLS)"] = f"({ols.tvalues[f]:.2f})"
                c[f"{r} t (NW)"] = f"[{nw.tvalues[f]:.2f}]"
            else:
                c[r] = ""
                c[f"{r} t (OLS)"] = ""
                c[f"{r} t (NW)"] = ""
        c["N months"] = f"{int(ols.nobs)}"
        c["R-squared"] = f"{ols.rsquared:.3f}"
        c["SE alpha OLS (%)"] = f"{ols.bse['const'] * 100:.3f}"
        c["SE alpha NW (%)"] = f"{nw.bse['const'] * 100:.3f}"
        cols[name] = c
    t = pd.DataFrame(cols)
    # blank out t rows for factors that never appear
    keep = [i for i in t.index if not (t.loc[i] == "").all()]
    t = t.loc[keep]
    return t, res


tab6, res6 = reg_table(panel_m, "ex", MODELS)
save_table(tab6, "table6_factor_regressions",
           "Q6: regressions of the equal-weighted calendar-time portfolio's monthly excess return ($R_p - R_f$) on factors. "
           "Coefficients: alpha in percent per month; loadings are betas. Parentheses: OLS t-statistics; brackets: Newey-West t-statistics "
           f"({NW_LAGS} lags). Model (5) uses the five-factor file's own Mkt-RF, SMB, HML, RMW, CMA and RF. Sample: calendar months with at least one stock held.",
           "tab:q6", colfmt="lrrrrr")
# sanity: (1) alpha equals the mean excess return
check("model (1) alpha == mean excess return", f"{res6['(1) No factors'][0].params['const']:.6f} vs {panel_m.ex.mean():.6f}")
# regression machinery cross-check against closed-form OLS
Xchk = np.column_stack([np.ones(len(panel_m)), panel_m[["Mkt-RF"]].values])
beta_chk = np.linalg.lstsq(Xchk, panel_m.ex.values, rcond=None)[0]
check("CAPM alpha/beta: statsmodels vs numpy lstsq (max abs diff)", f"{np.abs(beta_chk - res6['(2) CAPM'][0].params.values).max():.2e}")
# NW sensitivity to lag length
rob = {}
for name in ["(2) CAPM", "(3) FF3", "(4) FF3+Mom"]:
    fac = MODELS[name]
    rob[name] = {f"NW t(alpha), {L} lags": fit(panel_m.ex, panel_m[fac], None, L)[1].tvalues["const"] for L in (0, 3, 6, 12)}
rob = pd.DataFrame(rob).T
save_table(rob.round(2), "table6b_nw_lags", "Q6 (robustness): Newey-West t-statistic of alpha for different lag lengths (0 lags = White heteroskedasticity-robust).", "tab:q6b", colfmt="lrrrr")

# --------------------------------------------------------------------------
# Q8. Weighting: WLS (weights = N stocks) and value-weighted portfolio (prev-month cap)
# --------------------------------------------------------------------------
cap_prev = mon_stock.mktcap_end.copy()
held["mi_prev"] = held.mi - 1
held["cap_prev"] = [cap_prev.get((p, m), np.nan) for p, m in zip(held.permno, held.mi_prev)]
check("held stock-months lacking previous-month cap", int(held.cap_prev.isna().sum()))
held["w"] = held.cap_prev / held.groupby("mi").cap_prev.transform("sum")
check("VW weights sum to 1 in every month (max abs deviation)", f"{(held.groupby('mi').w.sum() - 1).abs().max():.2e}")
vw = held.groupby("mi").apply(lambda g: (g.w * g.ret_stock).sum(), include_groups=False).rename("rp_vw")
maxw = held.groupby("mi").w.max()
check("VW: average / max (over months) of largest single-stock weight", f"{maxw.mean():.3f} / {maxw.max():.3f}")
check("VW: average effective number of stocks (1/sum w^2)", f"{(1 / held.groupby('mi').w.apply(lambda s: (s ** 2).sum())).mean():.1f}")
panel_m["rp_vw"] = vw
panel_m["ex_vw"] = panel_m.rp_vw - panel_m.rf
check("corr(EW, VW) portfolio return", f"{panel_m.rp.corr(panel_m.rp_vw):.3f}")
check("mean monthly return EW vs VW (decimal)", f"{panel_m.rp.mean():.4f} vs {panel_m.rp_vw.mean():.4f}")

tab8_rows = {}
res8 = {}
for name, fac in MODELS.items():
    X = panel_m[fac] if fac else None
    o_ew, n_ew = fit(panel_m.ex, X)
    o_w, n_w = fit(panel_m.ex, X, w=panel_m.n)
    o_vw, n_vw = fit(panel_m.ex_vw, X)
    res8[name] = (o_ew, n_ew, o_w, n_w, o_vw, n_vw)
    tab8_rows[name] = {
        "EW OLS: alpha (%)": o_ew.params["const"] * 100, "EW OLS: t (NW)": n_ew.tvalues["const"], "EW OLS: t (OLS)": o_ew.tvalues["const"],
        "WLS (w = N): alpha (%)": o_w.params["const"] * 100, "WLS: t (NW)": n_w.tvalues["const"], "WLS: t (OLS)": o_w.tvalues["const"],
        "VW (prev. cap): alpha (%)": o_vw.params["const"] * 100, "VW: t (NW)": n_vw.tvalues["const"], "VW: t (OLS)": o_vw.tvalues["const"],
    }
tab8_full = pd.DataFrame(tab8_rows).T.round(3)
tab8_full.to_csv(OUT_DIR / "table8_weighting_full.csv")
tab8 = tab8_full[["EW OLS: alpha (%)", "EW OLS: t (NW)", "WLS (w = N): alpha (%)", "WLS: t (NW)", "VW (prev. cap): alpha (%)", "VW: t (NW)"]]
tab8.columns = ["EW alpha", "EW t", "WLS alpha", "WLS t", "VW alpha", "VW t"]
save_table(tab8, "table8_weighting",
           "Q8: monthly alpha (percent) and its t-statistic by weighting scheme. EW OLS = Q6 (each month equal weight, stocks equally weighted); "
           "WLS = months weighted by the number of stocks held that month; VW = stocks weighted by their market cap at the end of the previous month "
           f"(OLS across months). t: Newey-West with {NW_LAGS} lags (usual OLS t-statistics are in table8\\_weighting\\_full.csv and lead to the same conclusions).", "tab:q8", colfmt="lrrrrrr")
# loadings for VW and WLS, for discussion
loadings = {}
for tag, k in [("EW", 0), ("WLS", 2), ("VW", 4)]:
    for name in ["(3) FF3", "(4) FF3+Mom"]:
        o = res8[name][k]
        loadings[f"{tag} {name}"] = o.params.drop("const").round(3)
loadings = pd.DataFrame(loadings).T[["Mkt-RF", "SMB", "HML", "Mom"]].fillna("")
save_table(loadings, "table8b_loadings", "Q8 (supporting): factor loadings under each weighting scheme.", "tab:q8b", colfmt="lrrrr")


# --------------------------------------------------------------------------
# Robustness: drop events touched by the fill rule or by the stop-trading rule; winsorise BHAR
# --------------------------------------------------------------------------
fill_ev = set(ev.event_id[[((fills.permno == p) & (fills.mi > m0) & (fills.mi <= m0 + 12)).any() for p, m0 in zip(ev.permno, ev.m0)]])
excl = fill_ev | set(ev.event_id[ev.cut_stop])
rob_rows = {}
y = ev[ev.bhar_ok & ~ev.event_id.isin(excl)].bhar_mkt
rob_rows["BHAR vs. market, excluding fill/stop events"] = (len(y), y.mean() * 100, y.mean() / (y.std() / np.sqrt(len(y))))
lo, hi = x.quantile([0.01, 0.99])
xw = x.clip(lo, hi)
rob_rows["BHAR vs. market, winsorised at 1/99"] = (len(xw), xw.mean() * 100, xw.mean() / (xw.std() / np.sqrt(len(xw))))
h2 = pan[~pan.event_id.isin(excl) & pan.held][["permno", "mi", "ret_stock"]].drop_duplicates(["permno", "mi"])
m2 = h2.groupby("mi").ret_stock.mean().to_frame("rp")
m2["ex"] = m2.rp - ff3.RF.reindex(m2.index)
o2 = sm.OLS(m2.ex, sm.add_constant(ff3["Mkt-RF"].reindex(m2.index))).fit(cov_type="HAC", cov_kwds={"maxlags": NW_LAGS})
rob_rows["CAPM alpha (%/month), excluding fill/stop events"] = (len(m2), o2.params["const"] * 100, o2.tvalues["const"])
rob = pd.DataFrame(rob_rows, index=["N", "Estimate (%)", "t-statistic"]).T.round(2)
rob["N"] = rob.N.astype(int)
save_table(rob, "table_robustness", "Robustness: dropping the events touched by the empty-day fill rule (2) or the stopped-trading rule (4), and winsorising BHARs at the 1st and 99th percentiles. "
           "Estimates are percent (BHAR) or percent per month (alpha); t-statistics are conventional for BHAR and Newey-West for alpha.", "tab:rob", colfmt="p{8cm}rrr")

# --------------------------------------------------------------------------
# Q6/Q7 supporting tables: alpha decomposition and BHAR <-> alpha bridge
# --------------------------------------------------------------------------
dec_rows = {}
for name in ["(2) CAPM", "(3) FF3", "(4) FF3+Mom", "(5) FF5"]:
    o = res6[name][0]
    r = {"Mean excess return (%/month)": panel_m.ex.mean() * 100, "Alpha": o.params["const"] * 100}
    for f in MODELS[name]:
        r[f"{LABEL.get(f, f)}: loading x mean factor"] = o.params[f] * panel_m[f].mean() * 100
    r["Sum (alpha + contributions)"] = o.params["const"] * 100 + sum(o.params[f] * panel_m[f].mean() * 100 for f in MODELS[name])
    dec_rows[name] = r
row_order = ["Mean excess return (%/month)", "Alpha"] + [f"{f}: loading x mean factor" for f in ["Mkt-RF", "SMB", "HML", "Mom", "RMW", "CMA"]] \
    + ["Sum (alpha + contributions)"]
dec_tab = pd.DataFrame(dec_rows).reindex([r for r in row_order if r in set().union(*[set(v) for v in dec_rows.values()])]).round(3).fillna("")
save_table(dec_tab, "table6c_alpha_decomposition",
           "Q6 (supporting): decomposition of the portfolio's mean monthly excess return (percent) into alpha and loading x sample-mean factor premium. "
           "The last row equals the first row (identity check).", "tab:q6c", colfmt="lrrrr")
check("decomposition identity: max |sum - mean excess|", f"{max(abs(float(v['Sum (alpha + contributions)']) - float(v['Mean excess return (%/month)'])) for v in dec_rows.values()):.1e}")
fm = pd.DataFrame({"Mean (%/month)": panel_m[["Mkt-RF", "SMB", "HML", "Mom", "RMW_5", "CMA_5"]].mean() * 100,
                   "Std. dev. (%/month)": panel_m[["Mkt-RF", "SMB", "HML", "Mom", "RMW_5", "CMA_5"]].std() * 100}).round(3)
save_table(fm, "table6d_factor_means", "Q6 (supporting): mean and standard deviation of the factors over the portfolio's months (percent per month).", "tab:q6d", colfmt="lrr")

fullb = pan[pan.event_id.isin(ev[ev.bhar_ok].event_id)]
mkt_cal = panel_m.index.map(mon_mkt)
fr_cal = (ff3["Mkt-RF"] + ff3["RF"]).reindex(panel_m.index)
bridge = pd.Series({
    "(a) Mean 12-month BHAR vs. mkt_ret": st_mkt["Mean"] * 100,
    "(b) Mean 12-month BHAR vs. French market": st_fr["Mean"] * 100,
    "(c) Event-month mean of (R_i - mkt_ret) x 12": (fullb.ret_used - fullb.ret_mkt).mean() * 12 * 100,
    "(d) Calendar-month mean of (R_p - mkt_ret) x 12": (panel_m.rp - mkt_cal).mean() * 12 * 100,
    "(e) Calendar-month mean of (R_p - French market) x 12": (panel_m.rp - fr_cal).mean() * 12 * 100,
    "(f) CAPM alpha x 12": res6["(2) CAPM"][0].params["const"] * 12 * 100,
    "(g) Three-factor alpha x 12": res6["(3) FF3"][0].params["const"] * 12 * 100,
    "(h) Four-factor (with Mom) alpha x 12": res6["(4) FF3+Mom"][0].params["const"] * 12 * 100,
}).round(2).to_frame("Percent per year")
save_table(bridge, "table7_bridge",
           "Q7 (bridge): from the 12-month BHAR to the calendar-time alphas, in percent per year. (a)-(b) change only the benchmark; "
           "(c)-(d) change from event weighting to calendar-month weighting and from compounded to arithmetic returns; (f)-(h) let the model "
           "adjust for market beta and style loadings. Alphas are monthly alphas multiplied by 12. French market = Mkt-RF + RF.", "tab:q7", colfmt="p{9cm}r")

# --------------------------------------------------------------------------
# Save checks and key numbers
# --------------------------------------------------------------------------
chk = pd.DataFrame(CHECKS).astype(str)
chk.to_csv(OUT_DIR / "sanity_checks.csv", index=False)
keep = ["daily rows", "split events", "daily duplicates (permno,date)", "daily missing ret / mkt_ret / mktcap", "ex-date range",
        "trading days in calendar", "explicit NaN ret in raw file", "empty stock-days inside stock history filled with mkt_ret",
        "stock-days in wholly-empty months (not filled, month treated as 'stopped trading')", "events whose window contains a day filled with mkt_ret",
        "events with trading obs in month 0", "expected panel rows = sum(min(12, DATA_END - m0))",
        "BHAR from panel vs direct daily compounding (8 random events), max abs diff",
        "monthly stock return inside event windows: min / max",
        "corr(compounded mkt_ret, French Mkt-RF+RF) monthly", "mean monthly diff (mkt_ret - French Mkt), and 2014-2025 compounded return of each",
        "events with size decile assigned", "cap at month 0: median / min / max ($ millions)",
        "held event-months before / after removing overlapping splits of the same stock", "EW weights sum to 1 in every month (max abs deviation)",
        "VW weights sum to 1 in every month (max abs deviation)", "VW: average / max (over months) of largest single-stock weight",
        "VW: average effective number of stocks (1/sum w^2)", "model (1) alpha == mean excess return",
        "CAPM alpha/beta: statsmodels vs numpy lstsq (max abs diff)", "decomposition identity: max |sum - mean excess|",
        "SE of mean BHAR: iid vs clustered by ex-date month", "robustness: mean BHAR vs French market / t"]
chk_tab = chk[chk.check.isin(keep)][["check", "value"]].set_index("check")
chk_tab.index.name = None
chk_tab.columns = ["Result"]
save_table(chk_tab, "table_checks", "Appendix: data and results checks (selected). Full list in sanity\\_checks.csv.", "tab:checks", colfmt="p{9cm}p{6cm}")
ev.drop(columns=["m0_has_obs"]).to_csv(OUT_DIR / "events_with_bhar.csv", index=False)
panel_m.to_csv(OUT_DIR / "calendar_portfolio.csv")
json.dump({"bhar_mkt": {k: float(v) for k, v in st_mkt.items()},
           "bhar_dec": {k: float(v) for k, v in st_dec.items()},
           "bhar_diff": {k: float(v) for k, v in st_diff.items()},
           "cluster_se_mkt": float(se_cl)},
          open(OUT_DIR / "key_numbers.json", "w"), indent=1)
print("\nDone. Outputs in", OUT_DIR)

"""
Atlas do Mercado de Terras INCRA — Mato Grosso
Comparativo 2023 vs 2025 — VTN (Valor da Terra Nua)

Produces a multi-panel PNG figure saved to:
    /home/user/farmdat/analysis/atlas_mt_comparison.png

Run from project root:
    python -m analysis.visualize_atlas
"""

from __future__ import annotations

import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")  # non-interactive backend for headless environments
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import matplotlib.colors as mcolors
import numpy as np

# ---------------------------------------------------------------------------
# Make the package importable when called as script or module
# ---------------------------------------------------------------------------
_HERE = Path(__file__).resolve().parent
_ROOT = _HERE.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from analysis.atlas_data import ATLAS_DATA, get_region_names, get_growth_pct  # noqa: E402

# ---------------------------------------------------------------------------
# Output path
# ---------------------------------------------------------------------------
OUTPUT_PNG = _HERE / "atlas_mt_comparison.png"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def fmt_reais(value: float, decimals: int = 0) -> str:
    """Format a R$/ha value as 'R$ 52k' or 'R$ 52.000'."""
    if value >= 1_000:
        k = value / 1_000
        if k == int(k):
            return f"R$ {int(k)}k"
        return f"R$ {k:.1f}k"
    return f"R$ {value:,.0f}"


def fmt_axis_reais(value: float, _pos=None) -> str:
    """Formatter for matplotlib axes tick labels."""
    if value >= 1_000:
        return f"R$ {value/1000:.0f}k"
    return f"R$ {value:.0f}"


# ---------------------------------------------------------------------------
# Data extraction helpers
# ---------------------------------------------------------------------------

def get_avgs_sorted_by_2025(uso: str = "agricultura") -> tuple[list[str], list[float], list[float]]:
    """
    Return (region_names, avgs_2023, avgs_2025) sorted descending by 2025 avg.
    """
    regions = get_region_names()
    pairs = []
    for r in regions:
        a23 = ATLAS_DATA[2023]["regioes"][r][uso]["avg"]
        a25 = ATLAS_DATA[2025]["regioes"][r][uso]["avg"]
        pairs.append((r, a23, a25))
    pairs.sort(key=lambda x: x[2], reverse=True)
    names = [p[0] for p in pairs]
    avgs23 = [p[1] for p in pairs]
    avgs25 = [p[2] for p in pairs]
    return names, avgs23, avgs25


def get_growth_rates_sorted() -> tuple[list[str], list[float]]:
    """Return (region_names, growth_pcts) sorted ascending by growth %."""
    regions = get_region_names()
    data = [(r, get_growth_pct(r, "agricultura")) for r in regions]
    data.sort(key=lambda x: x[1])
    return [d[0] for d in data], [d[1] for d in data]


def get_top6_regions() -> list[str]:
    """Top 6 regions by 2025 VTN agriculture avg."""
    regions = get_region_names()
    regions_sorted = sorted(
        regions,
        key=lambda r: ATLAS_DATA[2025]["regioes"][r]["agricultura"]["avg"],
        reverse=True,
    )
    return regions_sorted[:6]


# ---------------------------------------------------------------------------
# Colors / style
# ---------------------------------------------------------------------------
COLOR_2023 = "#4472C4"      # steel blue
COLOR_2025 = "#C0392B"      # orange-red / brick
COLOR_AGRI = "#27AE60"      # green
COLOR_PEC  = "#E67E22"      # orange
COLOR_NAT  = "#2980B9"      # blue

GRID_ALPHA = 0.3
FONT_TITLE = 11
FONT_LABEL = 9
FONT_TICK  = 8


# ---------------------------------------------------------------------------
# Panel 1 — Grouped bar: VTN agri avg by MRT, 2023 vs 2025
# ---------------------------------------------------------------------------

def draw_panel1(ax: plt.Axes) -> None:
    names, avgs23, avgs25 = get_avgs_sorted_by_2025("agricultura")
    n = len(names)
    x = np.arange(n)
    width = 0.38

    bars23 = ax.bar(x - width / 2, avgs23, width, color=COLOR_2023, label="Atlas 2023 (ref. 2022)",
                    zorder=3, edgecolor="white", linewidth=0.5)
    bars25 = ax.bar(x + width / 2, avgs25, width, color=COLOR_2025, label="Atlas 2025 (ref. 2024)",
                    zorder=3, edgecolor="white", linewidth=0.5)

    # % growth labels on top of 2025 bars
    for bar, v23, v25 in zip(bars25, avgs23, avgs25):
        pct = (v25 / v23 - 1) * 100
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            bar.get_height() + 400,
            f"+{pct:.1f}%",
            ha="center", va="bottom",
            fontsize=6.5, color="#7B241C", fontweight="bold",
            rotation=0,
        )

    ax.set_xticks(x)
    ax.set_xticklabels(names, rotation=30, ha="right", fontsize=FONT_TICK)
    ax.yaxis.set_major_formatter(plt.FuncFormatter(fmt_axis_reais))
    ax.set_ylabel("VTN R$/ha", fontsize=FONT_LABEL)
    ax.set_title("VTN Agricultura — Média por MRT (R$/ha)", fontsize=FONT_TITLE, pad=8)
    ax.legend(fontsize=FONT_LABEL, loc="upper right")
    ax.grid(axis="y", alpha=GRID_ALPHA, zorder=0)
    ax.set_axisbelow(True)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)


# ---------------------------------------------------------------------------
# Panel 2 — Three land uses for top 6 regions (2025)
# ---------------------------------------------------------------------------

def draw_panel2(ax: plt.Axes) -> None:
    top6 = get_top6_regions()
    usos = [
        ("agricultura",       "Agricultura",         COLOR_AGRI),
        ("pecuaria",          "Pecuária",            COLOR_PEC),
        ("vegetacao_nativa",  "Vegetação Nativa",    COLOR_NAT),
    ]
    n = len(top6)
    x = np.arange(n)
    group_w = 0.75
    bar_w = group_w / len(usos)

    for i, (uso_key, uso_label, color) in enumerate(usos):
        avgs = [ATLAS_DATA[2025]["regioes"][r][uso_key]["avg"] for r in top6]
        offset = (i - len(usos) / 2 + 0.5) * bar_w
        ax.bar(x + offset, avgs, bar_w, color=color, label=uso_label,
               zorder=3, edgecolor="white", linewidth=0.5)

    ax.set_xticks(x)
    ax.set_xticklabels(top6, rotation=28, ha="right", fontsize=FONT_TICK)
    ax.yaxis.set_major_formatter(plt.FuncFormatter(fmt_axis_reais))
    ax.set_ylabel("VTN R$/ha", fontsize=FONT_LABEL)
    ax.set_title("Usos do Solo — Top 6 MRTs (Atlas 2025)", fontsize=FONT_TITLE, pad=8)
    ax.legend(fontsize=FONT_LABEL - 1, loc="upper right")
    ax.grid(axis="y", alpha=GRID_ALPHA, zorder=0)
    ax.set_axisbelow(True)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)


# ---------------------------------------------------------------------------
# Panel 3 — Horizontal bar: % growth by region
# ---------------------------------------------------------------------------

def draw_panel3(ax: plt.Axes) -> None:
    names, growths = get_growth_rates_sorted()
    y = np.arange(len(names))

    # Color gradient: yellow (low) → dark red (high)
    cmap = matplotlib.colormaps.get_cmap("YlOrRd")
    g_min, g_max = min(growths), max(growths)
    norm = mcolors.Normalize(vmin=g_min - 1, vmax=g_max + 1)

    bars = ax.barh(y, growths, color=[cmap(norm(g)) for g in growths],
                   zorder=3, edgecolor="white", linewidth=0.4, height=0.65)

    # Growth % labels
    for bar, pct in zip(bars, growths):
        ax.text(
            bar.get_width() + 0.15,
            bar.get_y() + bar.get_height() / 2,
            f"+{pct:.2f}%",
            va="center", ha="left", fontsize=7, color="#333333",
        )

    # National average reference line
    nat_growth = ATLAS_DATA[2025]["crescimento_nacional_pct"]
    ax.axvline(nat_growth, color="navy", linestyle="--", linewidth=1.2, zorder=4,
               label=f"Média nacional +{nat_growth}%")

    ax.set_yticks(y)
    ax.set_yticklabels(names, fontsize=FONT_TICK)
    ax.set_xlabel("Crescimento VTN agri (%)", fontsize=FONT_LABEL)
    ax.set_title("Crescimento 2023→2025 por MRT (%)", fontsize=FONT_TITLE, pad=8)
    ax.legend(fontsize=FONT_LABEL - 1, loc="lower right")
    ax.grid(axis="x", alpha=GRID_ALPHA, zorder=0)
    ax.set_axisbelow(True)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

    # Colorbar legend
    sm = plt.cm.ScalarMappable(cmap=cmap, norm=norm)
    sm.set_array([])
    cbar = plt.colorbar(sm, ax=ax, pad=0.02, fraction=0.03)
    cbar.set_label("Crescimento %", fontsize=6)
    cbar.ax.tick_params(labelsize=6)


# ---------------------------------------------------------------------------
# Panel 4 — Min-avg-max range chart (agriculture, both years)
# ---------------------------------------------------------------------------

def draw_panel4(ax: plt.Axes) -> None:
    names = get_region_names()
    # Sort by 2025 avg descending for consistency with panel 1
    names = sorted(names,
                   key=lambda r: ATLAS_DATA[2025]["regioes"][r]["agricultura"]["avg"],
                   reverse=True)
    n = len(names)
    x = np.arange(n)
    offset = 0.18  # horizontal spread between 2023/2025

    for xi, region in zip(x, names):
        for year, color, dx in [(2023, COLOR_2023, -offset), (2025, COLOR_2025, offset)]:
            d = ATLAS_DATA[year]["regioes"][region]["agricultura"]
            vmin, vavg, vmax = d["min"], d["avg"], d["max"]
            # Vertical range line
            ax.plot([xi + dx, xi + dx], [vmin, vmax],
                    color=color, linewidth=1.8, solid_capstyle="round", zorder=2)
            # Min / max ticks
            for v in (vmin, vmax):
                ax.plot([xi + dx - 0.06, xi + dx + 0.06], [v, v],
                        color=color, linewidth=1.5, zorder=2)
            # Average marker
            ax.scatter(xi + dx, vavg, color=color, s=40, zorder=4,
                       edgecolors="white", linewidths=0.8)

    # Legend proxies
    patch23 = mpatches.Patch(color=COLOR_2023, label="Atlas 2023 (ref. 2022)")
    patch25 = mpatches.Patch(color=COLOR_2025, label="Atlas 2025 (ref. 2024)")
    ax.legend(handles=[patch23, patch25], fontsize=FONT_LABEL, loc="upper right")

    ax.set_xticks(x)
    ax.set_xticklabels(names, rotation=30, ha="right", fontsize=FONT_TICK)
    ax.yaxis.set_major_formatter(plt.FuncFormatter(fmt_axis_reais))
    ax.set_ylabel("VTN R$/ha", fontsize=FONT_LABEL)
    ax.set_title(
        "Amplitude VTN Agricultura — Mín / Média / Máx por MRT",
        fontsize=FONT_TITLE, pad=8,
    )
    ax.grid(axis="y", alpha=GRID_ALPHA, zorder=0)
    ax.set_axisbelow(True)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

    # Annotation explaining markers
    ax.annotate(
        "● = média  |  ─── = amplitude min–máx",
        xy=(0.5, -0.22), xycoords="axes fraction",
        ha="center", va="top", fontsize=7, color="#555555",
    )


# ---------------------------------------------------------------------------
# Main figure assembly
# ---------------------------------------------------------------------------

def build_figure() -> plt.Figure:
    fig = plt.figure(figsize=(18, 22))

    # Layout: 3 rows
    #   row 0: panel 1 (full width)
    #   row 1: panel 2 (left) + panel 3 (right)
    #   row 2: panel 4 (full width)
    gs = fig.add_gridspec(
        3, 2,
        height_ratios=[1.0, 1.0, 1.05],
        hspace=0.52,
        wspace=0.30,
        left=0.07, right=0.97,
        top=0.92, bottom=0.06,
    )

    ax1 = fig.add_subplot(gs[0, :])    # full width top
    ax2 = fig.add_subplot(gs[1, 0])   # middle left
    ax3 = fig.add_subplot(gs[1, 1])   # middle right
    ax4 = fig.add_subplot(gs[2, :])   # full width bottom

    draw_panel1(ax1)
    draw_panel2(ax2)
    draw_panel3(ax3)
    draw_panel4(ax4)

    # ---------------------------------------------------------------------------
    # Overall title
    # ---------------------------------------------------------------------------
    fig.suptitle(
        "Atlas do Mercado de Terras INCRA\n"
        "Mato Grosso – Comparativo 2023 vs 2025\n"
        "VTN – Valor da Terra Nua (R$/ha)",
        fontsize=14,
        fontweight="bold",
        y=0.975,
        linespacing=1.5,
    )

    # ---------------------------------------------------------------------------
    # Footnote
    # ---------------------------------------------------------------------------
    fig.text(
        0.5, 0.005,
        "Fonte: INCRA/SIGEF. Atlas do Mercado de Terras 2023 (ref. 2022) e 2025 (ref. 2024). "
        "Valores de VTN sem benfeitorias.",
        ha="center", va="bottom",
        fontsize=7.5, color="#555555",
        style="italic",
    )

    return fig


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    print("Building Atlas do Mercado de Terras comparison figure...")
    fig = build_figure()
    OUTPUT_PNG.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(str(OUTPUT_PNG), dpi=150, bbox_inches="tight", facecolor="white")
    plt.close(fig)

    size_kb = OUTPUT_PNG.stat().st_size / 1024
    print(f"Saved: {OUTPUT_PNG}")
    print(f"File size: {size_kb:.1f} KB")
    if size_kb < 100:
        print("WARNING: File size < 100 KB — image may be incomplete.")
        sys.exit(1)
    else:
        print("OK: File size looks good.")


if __name__ == "__main__":
    main()

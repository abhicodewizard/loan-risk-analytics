"""
Step 5 - Presentation-quality charts built from the SQL query results (matplotlib).
Chart titles are computed from the data, so they can never disagree with the numbers.

Run:  python src/05_eda_charts.py
"""
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
Q, IMG = ROOT / "outputs" / "query_results", ROOT / "outputs" / "images"
IMG.mkdir(parents=True, exist_ok=True)
NAVY, BLUE, ORANGE, RED, GREY, GREEN = "#1F4E78", "#2E75B6", "#ED7D31", "#C00000", "#7F7F7F", "#548235"
plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 10, "axes.spines.top": False, "axes.spines.right": False,
                     "axes.titleweight": "bold", "axes.titlesize": 12.5})
rd = lambda n: pd.read_csv(next(Q.glob(f"{n}*.csv")))


def save(fig, name):
    fig.tight_layout()
    fig.savefig(IMG / name, dpi=130)
    plt.close(fig)
    print("  saved", name)


# 1. funnel ---------------------------------------------------------------------------
m = rd("q02")
fig, ax = plt.subplots(figsize=(11, 5))
ax.bar(m.app_month.str[2:], m.applications, color=BLUE, alpha=.85)
ax.set_ylabel("Applications per month")
ax.set_xticks(range(0, len(m), 3), m.app_month.str[2:][::3])
ax2 = ax.twinx()
ax2.plot(m.app_month.str[2:], m.approval_rate_pct, color=ORANGE, lw=2.5)
ax2.set_ylim(0, 100)
ax2.set_ylabel("Approval rate %")
ax2.spines["right"].set_visible(True)
ax.set_title(f"Application funnel: {m.applications.sum():,} applications, {100 * m.approved.sum() / m.applications.sum():.0f}% approved")
save(fig, "01_monthly_application_funnel.png")

# 2. NPA vs credit score + pricing ---------------------------------------------------------
s = rd("q06")
fig, ax = plt.subplots(figsize=(10, 5))
cols = [RED if v > 12 else BLUE for v in s.npa_rate_pct]
ax.bar(s.score_band.str[3:], s.npa_rate_pct, color=cols)
for i, v in enumerate(s.npa_rate_pct):
    ax.text(i, v + .3, f"{v:.1f}%", ha="center", fontsize=9)
ax.set_ylabel("NPA rate % (loans with 12+ months on book)")
ax2 = ax.twinx()
ax2.plot(range(len(s)), s.avg_interest_rate, color=ORANGE, marker="o", lw=2.5)
ax2.set_ylim(0, 18)
ax2.set_ylabel("Average interest rate %")
ax2.spines["right"].set_visible(True)
lo, hi = s.iloc[0], s.iloc[5]
ax.set_title(f"NPA rate falls from {lo.npa_rate_pct:.0f}% to {hi.npa_rate_pct:.0f}% as score rises, but pricing moves only "
             f"{lo.avg_interest_rate - hi.avg_interest_rate:.1f} pts")
save(fig, "02_npa_vs_credit_score.png")

# 3. product risk ----------------------------------------------------------------------------
p = rd("q07").sort_values("npa_rate_pct")
fig, ax = plt.subplots(figsize=(9, 4.8))
ax.barh(p["product"], p.npa_rate_pct, color=[GREEN if s_ else RED for s_ in p.secured])
for y, (v, l) in enumerate(zip(p.npa_rate_pct, p.lgd)):
    ax.text(v + .15, y, f"{v:.1f}%  (LGD {int(l * 100)}%)", va="center", fontsize=9)
ax.set_xlim(0, p.npa_rate_pct.max() * 1.35)
ax.set_xlabel("NPA rate %   (green = secured, red = unsecured)")
top = p.iloc[-1]
ax.set_title(f"{top['product']}s have the highest NPA rate ({top.npa_rate_pct:.1f}%) and lose most after recovery")
save(fig, "03_npa_by_product.png")

# 4. FOIR ----------------------------------------------------------------------------------------
f = rd("q09")
fig, ax = plt.subplots(figsize=(8.5, 4.8))
ax.bar(f.foir_band.str[3:], f.npa_rate_pct, color=[BLUE, BLUE, ORANGE, ORANGE, RED])
for i, v in enumerate(f.npa_rate_pct):
    ax.text(i, v + .2, f"{v:.1f}%", ha="center")
ax.set_ylabel("NPA rate %")
ax.set_xlabel("FOIR (fixed obligations / monthly income)")
ax.set_title(f"Borrowers with FOIR above 60% default {f.npa_rate_pct.iloc[-1] / f.npa_rate_pct.iloc[0]:.1f}x more than those below 30%")
save(fig, "04_npa_by_foir.png")

# 5. vintage ----------------------------------------------------------------------------------------
v = rd("q10")
fig, ax = plt.subplots(figsize=(9, 4.8))
ax.plot(v.disb_quarter, v.npa_rate_mob12_pct, marker="o", lw=2.5, color=RED, label="NPA by month 12")
ax.plot(v.disb_quarter, v.npa_rate_mob6_pct, marker="o", lw=2.5, color=BLUE, label="NPA by month 6")
ax.set_ylabel("Cumulative NPA rate %")
ax.set_ylim(0, v.npa_rate_mob12_pct.max() * 1.25)
ax.legend(frameon=False)
w = v.loc[v.npa_rate_mob12_pct.idxmax()]
ax.set_title(f"Vintage analysis: {w.disb_quarter} is the weakest cohort ({w.npa_rate_mob12_pct:.1f}% NPA by month 12)")
save(fig, "05_vintage_analysis.png")

# 6. ageing --------------------------------------------------------------------------------------------
a = rd("q12")
fig, ax = plt.subplots(figsize=(8.5, 4.8))
ax.bar(a.dpd_bucket.str[3:], a.share_of_book_pct, color=[GREEN, BLUE, ORANGE, RED])
for i, (sh, cr) in enumerate(zip(a.share_of_book_pct, a.outstanding_cr)):
    ax.text(i, sh + 1, f"{sh:.1f}%\nRs {cr:,.0f} Cr", ha="center", fontsize=9)
ax.set_ylim(0, 100)
ax.set_ylabel("Share of outstanding book %")
ax.set_title(f"Portfolio ageing: gross NPA {a.share_of_book_pct.iloc[-1]:.1f}%, a further {a.share_of_book_pct.iloc[2]:.1f}% at 30-89 DPD")
save(fig, "06_portfolio_ageing.png")

# 7. risk matrix heatmap -----------------------------------------------------------------------------------
mx = rd("q21").pivot(index="score_band", columns="foir_group", values="npa_rate_pct")[["FOIR < 40%", "FOIR 40-55%", "FOIR 55%+"]]
fig, ax = plt.subplots(figsize=(8.5, 5.5))
im = ax.imshow(mx.values, cmap="RdYlGn_r", aspect="auto", vmin=0, vmax=28)
ax.set_xticks(range(3), mx.columns)
ax.set_yticks(range(len(mx)), mx.index.str[3:])
for i in range(mx.shape[0]):
    for j in range(mx.shape[1]):
        if not np.isnan(mx.values[i, j]):
            ax.text(j, i, f"{mx.values[i, j]:.1f}%", ha="center", va="center", fontsize=10, fontweight="bold")
ax.spines[:].set_visible(False)
fig.colorbar(im, ax=ax, label="NPA rate %")
ax.set_title("Risk matrix: credit score x FOIR (NPA rate, segments with 80+ loans)")
save(fig, "07_risk_matrix_score_foir.png")

# 8. risk-adjusted return ---------------------------------------------------------------------------------
r = rd("q15").sort_values("return_on_disbursed_pct")
fig, ax = plt.subplots(figsize=(9, 4.8))
ax.barh(r["product"], r.return_on_disbursed_pct, color=[RED if x < 10 else BLUE for x in r.return_on_disbursed_pct])
for y, (x, c) in enumerate(zip(r.return_on_disbursed_pct, r.credit_loss_cr)):
    ax.text(x + .1, y, f"{x:.1f}%  (credit loss Rs {c:.1f} Cr)", va="center", fontsize=9)
ax.set_xlim(0, r.return_on_disbursed_pct.max() * 1.45)
ax.set_xlabel("Risk-adjusted return on disbursed amount % (interest + fees - credit loss)")
ax.set_title(f"{r['product'].iloc[0]}s earn the lowest risk-adjusted return ({r.return_on_disbursed_pct.iloc[0]:.1f}%)")
save(fig, "08_risk_adjusted_return_by_product.png")

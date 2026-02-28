"""Claude Code 토큰 사용량 시각화 스크립트"""
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
import numpy as np
from datetime import date

# ── 일별 합산 데이터 (두 프로젝트 합산) ──
daily_data = [
    ("01-15", 440_007, 0.11),
    ("01-19", 184_330, 0.06),
    ("01-24", 615_471, 0.22),
    ("01-27", 0, 0.00),
    ("01-31", 78_535, 0.10),
    ("02-04", 25_469_658, 15.02),
    ("02-05", 23_061_056, 14.38),
    ("02-06", 5_192_093, 4.08),
    ("02-07", 31_983_688, 21.83),
    ("02-08", 21_291_412, 8.35),
    ("02-09", 6_659_628, 2.93),
    ("02-10", 31_219_265, 12.36),
    ("02-11", 40_701_514, 25.17),
    ("02-12", 74_927_079, 46.45),
    ("02-13", 170_375_954, 107.32),
    ("02-14", 96_782_448, 66.71),
    ("02-15", 79_190_605, 51.69),
    ("02-16", 71_691_533, 42.45),
    ("02-17", 7_244_154, 5.59),
    ("02-18", 34_174_765, 20.18),
    ("02-19", 65_263_157, 40.13),
    ("02-20", 41_591_988, 28.29),
    ("02-21", 30_639_266, 20.24),
    ("02-22", 65_342_791, 43.13),
    ("02-23", 45_049_895, 37.40),
    ("02-24", 105_468_035, 70.33),
    ("02-25", 25_064_869, 18.19),
    ("02-26", 39_486_892, 28.14),
    ("02-27", 23_099_411, 14.85),
    ("02-28", 118_659_505, 77.10),
]

# ── 주별 합산 데이터 ──
weekly_data = [
    ("W3\n01/12-18", 440_007, 0.11, 1),
    ("W4\n01/19-25", 799_801, 0.28, 2),
    ("W5\n01/26-02/01", 78_535, 0.10, 2),
    ("W6\n02/02-08", 106_997_907, 63.66, 5),
    ("W7\n02/09-15", 499_856_493, 312.63, 7),
    ("W8\n02/16-22", 315_947_654, 200.01, 7),
    ("W9\n02/23-28", 356_828_607, 246.01, 6),
]

dates = [d[0] for d in daily_data]
tokens = [d[1] for d in daily_data]
costs = [d[2] for d in daily_data]

w_labels = [d[0] for d in weekly_data]
w_tokens = [d[1] for d in weekly_data]
w_costs = [d[2] for d in weekly_data]
w_days = [d[3] for d in weekly_data]

# ── 스타일 설정 ──
plt.rcParams.update({
    "figure.facecolor": "#1a1a2e",
    "axes.facecolor": "#16213e",
    "axes.edgecolor": "#e0e0e0",
    "axes.labelcolor": "#e0e0e0",
    "xtick.color": "#e0e0e0",
    "ytick.color": "#e0e0e0",
    "text.color": "#e0e0e0",
    "grid.color": "#2a2a4a",
    "grid.alpha": 0.5,
    "font.size": 10,
})

fig = plt.figure(figsize=(18, 14))
fig.suptitle("Claude Code Token Usage Report\n2026-01 ~ 2026-02-28  |  Total: $822.78",
             fontsize=16, fontweight="bold", y=0.98)

# ═══════════════════════════════════════════
# 1) 일별 비용 막대그래프
# ═══════════════════════════════════════════
ax1 = fig.add_subplot(3, 1, 1)
colors_daily = ["#ff6b6b" if c >= 50 else "#ffd93d" if c >= 20 else "#6bcb77" for c in costs]
bars1 = ax1.bar(dates, costs, color=colors_daily, edgecolor="none", width=0.7)
ax1.set_ylabel("Cost (USD)")
ax1.set_title("Daily Cost", fontsize=13, fontweight="bold", pad=10)
ax1.grid(axis="y", linestyle="--")
ax1.set_ylim(0, max(costs) * 1.15)

# 상위 5일에 금액 표시
top5_idx = sorted(range(len(costs)), key=lambda i: costs[i], reverse=True)[:5]
for i in top5_idx:
    ax1.annotate(f"${costs[i]:.0f}", xy=(i, costs[i]),
                 ha="center", va="bottom", fontsize=8, fontweight="bold", color="#ffffff")

ax1.tick_params(axis="x", rotation=45, labelsize=7)

# ═══════════════════════════════════════════
# 2) 주별 비용 막대그래프
# ═══════════════════════════════════════════
ax2 = fig.add_subplot(3, 2, 3)
colors_weekly = ["#ff6b6b" if c >= 200 else "#ffd93d" if c >= 50 else "#6bcb77" for c in w_costs]
bars2 = ax2.bar(w_labels, w_costs, color=colors_weekly, edgecolor="none", width=0.6)
ax2.set_ylabel("Cost (USD)")
ax2.set_title("Weekly Cost", fontsize=13, fontweight="bold", pad=10)
ax2.grid(axis="y", linestyle="--")

for bar, cost in zip(bars2, w_costs):
    ax2.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 5,
             f"${cost:.0f}", ha="center", va="bottom", fontsize=9, fontweight="bold")

ax2.set_ylim(0, max(w_costs) * 1.2)
ax2.tick_params(axis="x", labelsize=8)

# ═══════════════════════════════════════════
# 3) 주별 토큰 수 막대그래프
# ═══════════════════════════════════════════
ax3 = fig.add_subplot(3, 2, 4)
bars3 = ax3.bar(w_labels, [t / 1e6 for t in w_tokens], color="#4ecdc4", edgecolor="none", width=0.6)
ax3.set_ylabel("Tokens (M)")
ax3.set_title("Weekly Tokens", fontsize=13, fontweight="bold", pad=10)
ax3.grid(axis="y", linestyle="--")

for bar, tok in zip(bars3, w_tokens):
    ax3.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 5,
             f"{tok/1e6:.0f}M", ha="center", va="bottom", fontsize=9, fontweight="bold")

ax3.set_ylim(0, max(w_tokens) / 1e6 * 1.2)
ax3.tick_params(axis="x", labelsize=8)

# ═══════════════════════════════════════════
# 4) 일별 누적 비용 영역 그래프
# ═══════════════════════════════════════════
ax4 = fig.add_subplot(3, 2, 5)
cumulative_cost = np.cumsum(costs)
ax4.fill_between(range(len(dates)), cumulative_cost, color="#ff6b6b", alpha=0.3)
ax4.plot(range(len(dates)), cumulative_cost, color="#ff6b6b", linewidth=2, marker="o", markersize=3)
ax4.set_ylabel("Cumulative Cost (USD)")
ax4.set_title("Cumulative Cost Over Time", fontsize=13, fontweight="bold", pad=10)
ax4.grid(axis="y", linestyle="--")
ax4.set_xticks(range(0, len(dates), 3))
ax4.set_xticklabels([dates[i] for i in range(0, len(dates), 3)], rotation=45, fontsize=7)

# $100 단위 수평선
for milestone in [100, 200, 300, 400, 500, 600, 700, 800]:
    if milestone < max(cumulative_cost):
        ax4.axhline(y=milestone, color="#ffd93d", linestyle=":", alpha=0.4, linewidth=0.8)

ax4.annotate(f"${cumulative_cost[-1]:.0f}", xy=(len(dates)-1, cumulative_cost[-1]),
             ha="left", va="bottom", fontsize=10, fontweight="bold", color="#ff6b6b")

# ═══════════════════════════════════════════
# 5) 주별 일평균 비용
# ═══════════════════════════════════════════
ax5 = fig.add_subplot(3, 2, 6)
avg_costs = [c / d for c, d in zip(w_costs, w_days)]
bars5 = ax5.bar(w_labels, avg_costs, color="#a78bfa", edgecolor="none", width=0.6)
ax5.set_ylabel("Avg Cost/Day (USD)")
ax5.set_title("Weekly Avg Cost per Day", fontsize=13, fontweight="bold", pad=10)
ax5.grid(axis="y", linestyle="--")

for bar, avg in zip(bars5, avg_costs):
    ax5.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.5,
             f"${avg:.1f}", ha="center", va="bottom", fontsize=9, fontweight="bold")

ax5.set_ylim(0, max(avg_costs) * 1.25)
ax5.tick_params(axis="x", labelsize=8)

plt.tight_layout(rect=[0, 0, 1, 0.95])
out_path = "/mnt/d/projects/trilobase/dist/token_usage_chart.png"
plt.savefig(out_path, dpi=150, bbox_inches="tight")
print(f"Chart saved to {out_path}")
plt.close()

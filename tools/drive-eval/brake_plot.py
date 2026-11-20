"""Small-multiple plots of the events from brake_events.py. PC (matplotlib).

  python brake_plot.py <events.json> <out prefix>      -> <prefix>-1.png, -2.png, ... (12 events per page)

Per event, three stacked panels on a shared time axis (0 = braking begins): speed of the car and the lead (mph),
gap to the lead (m), and acceleration commanded and measured (m/s2) with the -3.5 m/s2 limit marked."""
import sys, json
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
EV = json.load(open(sys.argv[1])); PRE = sys.argv[2]
BLUE, ORANGE, GRID, INK, MUTED, RED = "#2a78d6", "#eb6834", "#e1e0d9", "#0b0b0b", "#898781", "#d03b3b"
plt.rcParams.update({"font.size": 9, "axes.edgecolor": "#c3c2b7", "axes.labelcolor": MUTED, "xtick.color": MUTED, "ytick.color": MUTED, "axes.spines.top": False, "axes.spines.right": False})
N, COLS, ROWS = 12, 4, 3
for pg in range((len(EV) + N - 1) // N):
    fig = plt.figure(figsize=(19, 14.5), facecolor="white"); outer = fig.add_gridspec(ROWS, COLS, hspace=0.34, wspace=0.2, left=0.035, right=0.99, top=0.95, bottom=0.04)
    for n, e in enumerate(EV[pg * N:(pg + 1) * N]):
        gs = outer[n // COLS, n % COLS].subgridspec(3, 1, hspace=0.12, height_ratios=(1.25, 0.8, 1.0)); x = e["x"]
        nan = lambda y: [float("nan") if v is None else v for v in y]
        a1 = fig.add_subplot(gs[0]); a1.plot(x, e["v"], color=BLUE, lw=2, label="car"); a1.plot(x, nan(e["vl"]), color=ORANGE, lw=1.6, ls="--", label="lead"); a1.set_ylabel("mph"); a1.set_ylim(bottom=0)
        hard = e["amin"] <= -3.0
        a1.set_title(f"{e['route']} +{e['t'] // 60}:{e['t'] % 60:02d}   {e['v0']} to {e['v1']} mph   strongest {e['amin']:.1f} m/s² at {e['v_at']} mph", fontsize=9.5, color=RED if hard else INK, loc="left", fontweight="bold" if hard else "normal")
        a2 = fig.add_subplot(gs[1], sharex=a1); a2.plot(x, nan(e["d"]), color=ORANGE, lw=1.6); a2.set_ylabel("gap m"); a2.set_ylim(bottom=0)
        a3 = fig.add_subplot(gs[2], sharex=a1); a3.plot(x, nan(e["cmd"]), color=MUTED, lw=1.4, ls=":", label="asked"); a3.plot(x, e["a"], color=BLUE, lw=1.8, label="measured")
        a3.axhline(-3.5, color=RED, lw=0.8, ls="--"); a3.axhline(0, color="#c3c2b7", lw=0.8); a3.set_ylabel("m/s²"); a3.set_ylim(-4.6, 2.2); a3.set_xlabel("seconds from the start of braking", fontsize=8)
        for ax in (a1, a2, a3): ax.grid(axis="y", color=GRID, lw=0.7); ax.axvline(0, color="#c3c2b7", lw=0.8)
        for ax in (a1, a2): plt.setp(ax.get_xticklabels(), visible=False)
        if n == 0: a1.legend(frameon=False, fontsize=8, loc="lower left", ncol=2); a3.legend(frameon=False, fontsize=8, loc="upper left", ncol=2)
    fig.suptitle(f"Braking events with openpilot speed control, 2026-11-20 ({pg * N + 1}-{min((pg + 1) * N, len(EV))} of {len(EV)}); red title = 3.0 m/s² or more; dashed red line = the -3.5 m/s² limit", fontsize=11, x=0.035, ha="left", color=INK)
    out = f"{PRE}-{pg + 1}.png"; fig.savefig(out, dpi=105); plt.close(fig); print(out)

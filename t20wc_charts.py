"""
T20 WC 2026 Thread Charts
=========================
Reads Cricsheet JSON files from your local folder and produces
7 high-res Twitter-ready PNGs.

SETUP (run once in terminal):
    pip install matplotlib numpy

RUN:
    python t20wc_charts.py

OUTPUT: 7 PNG files saved in the same folder as this script.
"""

import json
import os
import glob
from collections import defaultdict
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import numpy as np

# ─────────────────────────────────────────────
# CONFIG — your local data folder
# ─────────────────────────────────────────────
DATA_DIR = r"C:\Users\pasca\Desktop\thread\data\matches"

# Match IDs per edition (from readme)
WC2026_IDS = {str(i) for i in range(1512719, 1512774)}
WC2024_IDS = {str(i) for i in range(1415701, 1415756)}
WC2022_IDS = {str(i) for i in range(1298135, 1298180)}
WC2021_IDS = {str(i) for i in range(1273712, 1273757)}
WC2016_IDS = {str(i) for i in range(951309, 951374)}

EDITION_MAP = {
    "2026": WC2026_IDS,
    "2024": WC2024_IDS,
    "2022": WC2022_IDS,
    "2021": WC2021_IDS,
    "2016": WC2016_IDS,
}

# ─────────────────────────────────────────────
# STYLE
# ─────────────────────────────────────────────
BG       = "#0F0F0F"
CARD     = "#1A1A1A"
RED      = "#E24B4A"
GREEN    = "#1D9E75"
NEUTRAL  = "#888780"
WHITE    = "#F0EDE8"
SUBTEXT  = "#9C9A95"
GOLD     = "#D4A843"

plt.rcParams.update({
    "figure.facecolor": BG,
    "axes.facecolor":   CARD,
    "axes.edgecolor":   "#2A2A2A",
    "axes.labelcolor":  WHITE,
    "xtick.color":      SUBTEXT,
    "ytick.color":      SUBTEXT,
    "text.color":       WHITE,
    "font.family":      "DejaVu Sans",
    "axes.spines.top":  False,
    "axes.spines.right":False,
    "grid.color":       "#2A2A2A",
    "grid.linewidth":   0.6,
})

DPI = 180


# ─────────────────────────────────────────────
# DATA LOADING
# ─────────────────────────────────────────────
def load_matches(edition_ids):
    """Load all JSON match files for a given set of match IDs."""
    matches = []
    for fpath in glob.glob(os.path.join(DATA_DIR, "*.json")):
        mid = os.path.splitext(os.path.basename(fpath))[0]
        if mid in edition_ids:
            with open(fpath, encoding="utf-8") as f:
                matches.append(json.load(f))
    return matches


def batter_innings(matches):
    """
    Returns list of dicts per batter per innings:
      {player, runs, balls, balls_to_100, team, match_id, inn_idx}

    balls_to_100 = balls faced at the exact delivery the batter reached 100.
                   None if batter never reached 100 in that innings.
    """
    rows = []
    for m in matches:
        mid = m["info"].get("event", {}).get("match_number", "?")
        for inn_idx, inn in enumerate(m.get("innings", [])):
            bat_team = inn.get("team", "")
            batter_runs         = defaultdict(int)
            batter_balls        = defaultdict(int)
            batter_balls_to_100 = {}   # filled once per batter when they hit 100

            # track which batters were dismissed this innings
            dismissed = set()
            for over in inn.get("overs", []):
                for delivery in over.get("deliveries", []):
                    batter = delivery["batter"]
                    runs   = delivery["runs"]["batter"]
                    extras = delivery.get("extras", {})
                    is_wide = "wides" in extras

                    if not is_wide:
                        batter_balls[batter] += 1

                    prev_runs = batter_runs[batter]
                    batter_runs[batter] += runs

                    if (batter not in batter_balls_to_100
                            and prev_runs < 100
                            and batter_runs[batter] >= 100):
                        batter_balls_to_100[batter] = batter_balls[batter]

                    # check for dismissal
                    wickets = delivery.get("wickets", [])
                    for w in wickets:
                        if w.get("player_out"):
                            dismissed.add(w["player_out"])

            for p in batter_runs:
                rows.append({
                    "player":       p,
                    "runs":         batter_runs[p],
                    "balls":        batter_balls[p],
                    "balls_to_100": batter_balls_to_100.get(p),
                    "dismissed":    p in dismissed,
                    "team":         bat_team,
                    "match_id":     mid,
                    "inn_idx":      inn_idx,
                })
    return rows


def aggregate_player(innings_rows, player, min_balls=0):
    """Sum runs & balls for a player across multiple innings.
    Average = runs / dismissals (not-outs excluded), same as official cricket avg.
    """
    filtered    = [r for r in innings_rows if r["player"] == player]
    total_runs  = sum(r["runs"]  for r in filtered)
    total_balls = sum(r["balls"] for r in filtered)
    dismissals  = sum(1 for r in filtered if r.get("dismissed", True))
    innings     = len(filtered)
    sr  = round(total_runs / total_balls * 100, 2) if total_balls else 0
    avg = round(total_runs / dismissals, 2) if dismissals else float("inf")
    return {
        "player":     player,
        "runs":       total_runs,
        "balls":      total_balls,
        "sr":         sr,
        "avg":        avg,
        "inns":       innings,
        "dismissals": dismissals,
        "not_outs":   innings - dismissals,
    }


def tournament_avg_sr(innings_rows, min_balls=12):
    """Overall tournament batting SR (min balls faced threshold)."""
    totals = defaultdict(lambda: {"runs": 0, "balls": 0})
    for r in innings_rows:
        totals[r["player"]]["runs"]  += r["runs"]
        totals[r["player"]]["balls"] += r["balls"]
    all_runs  = sum(v["runs"]  for v in totals.values() if v["balls"] >= min_balls)
    all_balls = sum(v["balls"] for v in totals.values() if v["balls"] >= min_balls)
    return round(all_runs / all_balls * 100, 1) if all_balls else 0


def find_centuries(innings_rows):
    """
    Returns list of {player, runs, balls_to_100, sr} for 100+ innings.
    balls_to_100 = exact balls faced when batter reached 100 (not total innings balls).
    """
    return [
        {
            "player":       r["player"],
            "runs":         r["runs"],
            "balls":        r["balls_to_100"],   # balls to reach 100, not full innings
            "sr":           round(100 / r["balls_to_100"] * 100, 1) if r["balls_to_100"] else 0,
        }
        for r in innings_rows
        if r["runs"] >= 100 and r.get("balls_to_100")
    ]


def match_scores_for_player(innings_rows, player):
    """Return list of individual innings scores for a player."""
    return sorted(
        [r["runs"] for r in innings_rows if r["player"] == player]
    )


def team_totals(matches):
    """
    Returns list of {team, total, won} per innings where batting first.
    'won' = True if that team won the match.
    """
    rows = []
    for m in matches:
        innings = m.get("innings", [])
        if len(innings) < 2:
            continue
        # first innings
        inn1 = innings[0]
        inn2 = innings[1]
        team1 = inn1.get("team", "")
        # compute total
        total1 = sum(
            d["runs"]["total"]
            for ov in inn1.get("overs", [])
            for d in ov.get("deliveries", [])
        )
        # winner
        outcome = m["info"].get("outcome", {})
        winner  = outcome.get("winner", "")
        rows.append({
            "team":  team1,
            "total": total1,
            "won":   winner == team1,
        })
    return rows


# ─────────────────────────────────────────────
# CHART HELPERS
# ─────────────────────────────────────────────
def save(fig, name):
    path = f"{name}.png"
    fig.savefig(path, dpi=DPI, bbox_inches="tight", facecolor=BG)
    plt.close(fig)
    print(f"  ✓ Saved {path}")


def watermark(ax, text="Data: Cricsheet · @TukTukAcademy"):
    ax.annotate(
        text,
        xy=(1, 0), xycoords="axes fraction",
        ha="right", va="bottom",
        fontsize=8, color=SUBTEXT,
        xytext=(0, -32), textcoords="offset points",
    )


# ─────────────────────────────────────────────
# CHART 1 — Tweet 2: Babar SR vs avg vs top-5
# ─────────────────────────────────────────────
def chart_babar(innings_2026, avg_sr):
    print("Building Chart 1 — Babar SR comparison...")

    babar  = aggregate_player(innings_2026, "Babar Azam")
    # top-5 average SR (by SR, min 30 balls)
    totals = defaultdict(lambda: {"runs": 0, "balls": 0})
    for r in innings_2026:
        totals[r["player"]]["runs"]  += r["runs"]
        totals[r["player"]]["balls"] += r["balls"]
    top5_sr = sorted(
        [v["runs"] / v["balls"] * 100 for v in totals.values() if v["balls"] >= 30],
        reverse=True
    )[:5]
    top5_avg = round(sum(top5_sr) / len(top5_sr), 1)

    categories = ["Babar Azam", "Tournament\nAverage", "Top-5 Avg SR"]
    values     = [babar["sr"], avg_sr, top5_avg]
    colors     = [RED, NEUTRAL, GREEN]

    fig, ax = plt.subplots(figsize=(10, 5))
    fig.patch.set_facecolor(BG)
    ax.set_facecolor(CARD)

    bars = ax.barh(categories, values, color=colors, height=0.45,
                   edgecolor="none")

    for bar, val, col in zip(bars, values, colors):
        ax.text(val + 1.5, bar.get_y() + bar.get_height() / 2,
                f"{val}", va="center", ha="left",
                fontsize=16, fontweight="bold", color=col)

    ax.set_xlim(0, max(values) * 1.22)
    ax.axvline(140, color=GOLD, linewidth=1.2, linestyle="--", alpha=0.7)
    ax.text(140.5, -0.6, "T20 floor\n(140 SR)", fontsize=8,
            color=GOLD, va="bottom")

    ax.set_xlabel("Strike Rate", fontsize=11)
    ax.set_title("Babar Azam's Strike Rate vs Tournament\n(2026 T20 World Cup)",
                 fontsize=14, fontweight="bold", color=WHITE, pad=14)
    ax.xaxis.set_major_formatter(mticker.FormatStrFormatter("%.0f"))
    ax.grid(axis="x", alpha=0.4)
    watermark(ax)

    save(fig, "chart1_babar_sr")


# ─────────────────────────────────────────────
# CHART 2 — Tweet 3: Maxwell SR across WC editions
# ─────────────────────────────────────────────
def chart_maxwell(all_edition_innings):
    print("Building Chart 2 — Maxwell SR trend...")

    # Cricsheet uses "GJ Maxwell" — try variants in case of data differences
    name_variants = ["GJ Maxwell", "Glenn Maxwell", "G Maxwell"]

    edition_srs = {}
    for yr, inn in all_edition_innings.items():
        for name in name_variants:
            stats = aggregate_player(inn, name)
            # Only include editions where he faced at least 10 balls
            if stats["balls"] >= 10:
                edition_srs[yr] = stats["sr"]
                break

    if not edition_srs:
        print("  ⚠ Maxwell not found in any edition — check his Cricsheet name.")
        print("    Run: python find_player.py to list all player names.")
        return

    editions = sorted(edition_srs.keys())
    srs      = [edition_srs[e] for e in editions]

    fig, ax = plt.subplots(figsize=(10, 5))
    fig.patch.set_facecolor(BG)
    ax.set_facecolor(CARD)

    color_list = [GREEN if s >= 140 else RED for s in srs]
    ax.bar(editions, srs, color=color_list, width=0.5, edgecolor="none")

    for e, s, c in zip(editions, srs, color_list):
        ax.text(e, s + 2, f"{s:.1f}", ha="center", fontsize=13,
                fontweight="bold", color=c)

    ax.axhline(140, color=GOLD, linewidth=1.2, linestyle="--", alpha=0.7)
    ax.text(editions[-1], 143, "140 SR floor", ha="right",
            fontsize=8, color=GOLD)

    ax.set_ylabel("Strike Rate", fontsize=11)
    ax.set_title(
        f"Glenn Maxwell — Strike Rate Across T20 World Cups\n"
        f"({', '.join(editions)} editions where he played)",
        fontsize=14, fontweight="bold", color=WHITE, pad=14,
    )
    ax.set_ylim(0, max(srs) * 1.22)
    ax.grid(axis="y", alpha=0.4)
    watermark(ax)

    save(fig, "chart2_maxwell_trend")


# ─────────────────────────────────────────────
# CHART 3 — Tweet 4: India batters SR bar chart
# ─────────────────────────────────────────────

# Cricsheet name → display name for India players
# Add or edit any name here if your data uses a different spelling
INDIA_NAME_MAP = {
    "Sanju Samson":       "Sanju Samson",
    "KM Sanju Samson":    "Sanju Samson",
    "SV Samson":          "Sanju Samson",
    "Ishan Kishan":       "Ishan Kishan",
    "Shubman Gill":       "Shubman Gill",
    "Rohit Sharma":       "Rohit Sharma",
    "Virat Kohli":        "Virat Kohli",
    "KL Rahul":           "KL Rahul",
    "Hardik Pandya":      "Hardik Pandya",
    "SA Yadav":           "SKY",
    "Suryakumar Yadav":   "SKY",
    "AT Rayudu":          "Ambati Rayudu",
    "RG Sharma":          "Rohit Sharma",
    "V Kohli":            "Virat Kohli",
    "HH Pandya":          "Hardik Pandya",
    "Tilak Varma":        "Tilak Varma",
    "Abhishek Sharma":    "Abhishek Sharma",
    "Rishabh Pant":       "Rishabh Pant",
    "RR Pant":            "Rishabh Pant",
    "Dinesh Karthik":     "Dinesh Karthik",
    "MS Dhoni":           "MS Dhoni",
    "Yuvraj Singh":       "Yuvraj Singh",
}

def resolve_india_name(cricsheet_name):
    """Return a clean display name, falling back to the raw name if not mapped."""
    return INDIA_NAME_MAP.get(cricsheet_name, cricsheet_name)


def chart_india_batters(innings_2026):
    print("Building Chart 3 — India batters SR...")

    india_inn = [r for r in innings_2026 if r["team"] == "India"]
    totals = defaultdict(lambda: {"runs": 0, "balls": 0})
    for r in india_inn:
        totals[r["player"]]["runs"]  += r["runs"]
        totals[r["player"]]["balls"] += r["balls"]

    # Filter: min 20 balls, then resolve display name
    batters = [
        {
            "player":  resolve_india_name(p),
            "sr":      round(v["runs"] / v["balls"] * 100, 1),
        }
        for p, v in totals.items()
        if v["balls"] >= 20
    ]
    batters.sort(key=lambda x: x["sr"], reverse=True)

    if not batters:
        print("  ⚠ No India batting data found.")
        return

    names  = [b["player"] for b in batters]
    srs    = [b["sr"]     for b in batters]
    colors = [RED if s < 140 else GREEN for s in srs]

    fig, ax = plt.subplots(figsize=(12, 5))
    fig.patch.set_facecolor(BG)
    ax.set_facecolor(CARD)

    bars = ax.bar(names, srs, color=colors, width=0.55, edgecolor="none")

    for bar, val, col in zip(bars, srs, colors):
        ax.text(bar.get_x() + bar.get_width() / 2, val + 2,
                f"{val}", ha="center", fontsize=11,
                fontweight="bold", color=col)

    ax.axhline(140, color=GOLD, linewidth=1.2, linestyle="--", alpha=0.7)
    ax.set_ylabel("Strike Rate", fontsize=11)
    ax.set_title("India Batters — Strike Rate (2026 T20 World Cup)\nSorted highest → lowest",
                 fontsize=14, fontweight="bold", color=WHITE, pad=14)
    ax.set_ylim(0, max(srs) * 1.22)
    ax.grid(axis="y", alpha=0.4)
    plt.xticks(rotation=20, ha="right", fontsize=10)
    watermark(ax)

    save(fig, "chart3_india_batters_sr")


# ─────────────────────────────────────────────
# CHART 9 — India: slowest vs fastest vs team avg vs tournament avg
#           across editions (with SKY as forced slowest in 2026)
# ─────────────────────────────────────────────
def chart_india_sr_trend(all_edition_innings):
    print("Building Chart 9 — India SR trend (slowest/fastest/team/tournament)...")

    # Editions to include — skip 2024 if India data missing, it auto-handles
    target_editions = ["2016", "2021", "2022", "2024", "2026"]

    # For 2026 we force SKY as the "slowest" to highlight the contrast
    SKY_VARIANTS = ["SA Yadav", "Suryakumar Yadav"]

    rows = []

    for yr in target_editions:
        inn = all_edition_innings.get(yr)
        if not inn:
            continue

        india_inn = [r for r in inn if r["team"] == "India"]
        if not india_inn:
            continue

        # Per-batter totals for India, min 15 balls
        totals = defaultdict(lambda: {"runs": 0, "balls": 0})
        for r in india_inn:
            totals[r["player"]]["runs"]  += r["runs"]
            totals[r["player"]]["balls"] += r["balls"]

        eligible = {
            p: v for p, v in totals.items() if v["balls"] >= 15
        }
        if not eligible:
            continue

        sr_map = {
            p: round(v["runs"] / v["balls"] * 100, 1)
            for p, v in eligible.items()
        }

        # Fastest batter this edition
        fastest_name = max(sr_map, key=sr_map.__getitem__)
        fastest_sr   = sr_map[fastest_name]

        # Slowest batter — for 2026 force SKY, otherwise natural minimum
        if yr == "2026":
            slowest_sr   = None
            slowest_name = None
            for v in SKY_VARIANTS:
                if v in sr_map:
                    slowest_sr   = sr_map[v]
                    slowest_name = "SKY"
                    break
            if slowest_sr is None:
                # Fallback to natural minimum if SKY not found
                slowest_name = min(sr_map, key=sr_map.__getitem__)
                slowest_sr   = sr_map[slowest_name]
                slowest_name = resolve_india_name(slowest_name)
        else:
            slowest_name = min(sr_map, key=sr_map.__getitem__)
            slowest_sr   = sr_map[slowest_name]
            slowest_name = resolve_india_name(slowest_name)

        # India team avg SR
        india_runs  = sum(v["runs"]  for v in eligible.values())
        india_balls = sum(v["balls"] for v in eligible.values())
        india_avg   = round(india_runs / india_balls * 100, 1) if india_balls else 0

        # Tournament avg SR
        tourn_avg = tournament_avg_sr(inn, min_balls=12)

        rows.append({
            "edition":      yr,
            "fastest_sr":   fastest_sr,
            "fastest_name": resolve_india_name(fastest_name),
            "slowest_sr":   slowest_sr,
            "slowest_name": slowest_name,
            "india_avg":    india_avg,
            "tourn_avg":    tourn_avg,
        })

    if not rows:
        print("  ⚠ No India data found across editions.")
        return

    editions    = [r["edition"]    for r in rows]
    fastest_srs = [r["fastest_sr"] for r in rows]
    slowest_srs = [r["slowest_sr"] for r in rows]
    india_avgs  = [r["india_avg"]  for r in rows]
    tourn_avgs  = [r["tourn_avg"]  for r in rows]

    x     = np.arange(len(editions))
    width = 0.2

    fig, ax = plt.subplots(figsize=(14, 6))
    fig.patch.set_facecolor(BG)
    ax.set_facecolor(CARD)

    BLUE = "#4A90D9"

    b1 = ax.bar(x - 1.5*width, fastest_srs, width, color=GREEN,   label="India Fastest SR",    edgecolor="none")
    b2 = ax.bar(x - 0.5*width, india_avgs,  width, color=BLUE,    label="India Team Avg SR",   edgecolor="none")
    b3 = ax.bar(x + 0.5*width, tourn_avgs,  width, color=NEUTRAL, label="Tournament Avg SR",   edgecolor="none")
    b4 = ax.bar(x + 1.5*width, slowest_srs, width, color=RED,     label="India Slowest SR",    edgecolor="none")

    # Value labels
    for bars, vals, col in [
        (b1, fastest_srs, GREEN),
        (b2, india_avgs,  BLUE),
        (b3, tourn_avgs,  NEUTRAL),
        (b4, slowest_srs, RED),
    ]:
        for bar, val in zip(bars, vals):
            ax.text(
                bar.get_x() + bar.get_width() / 2,
                val + 1.5,
                f"{val:.0f}",
                ha="center", va="bottom",
                fontsize=8, fontweight="bold", color=col,
            )

    # Player name annotations below slowest and fastest bars
    for i, r in enumerate(rows):
        # Fastest name — above bar (already has SR label), put name slightly higher
        ax.text(
            x[i] - 1.5*width,
            fastest_srs[i] + 8,
            r["fastest_name"].split()[-1],   # last name to keep it short
            ha="center", fontsize=7.5, color=GREEN, fontstyle="italic",
        )
        # Slowest name
        ax.text(
            x[i] + 1.5*width,
            slowest_srs[i] + 8,
            r["slowest_name"].split()[-1],
            ha="center", fontsize=7.5, color=RED, fontstyle="italic",
        )

    ax.axhline(140, color=GOLD, linewidth=1.2, linestyle="--", alpha=0.7)
    ax.text(x[-1] + 1.5*width + 0.25, 141.5, "140 floor",
            fontsize=8, color=GOLD, va="bottom")

    ax.set_xticks(x)
    ax.set_xticklabels(editions, fontsize=12)
    ax.set_ylabel("Strike Rate", fontsize=11)
    ax.set_ylim(0, max(fastest_srs) * 1.3)
    ax.set_title(
        "India at T20 World Cups — Fastest vs Slowest vs Team Avg vs Tournament Avg\n"
        "(2026: SKY used as slowest benchmark)",
        fontsize=13, fontweight="bold", color=WHITE, pad=14,
    )
    ax.legend(
        fontsize=9, facecolor=CARD, edgecolor="#2A2A2A",
        labelcolor=WHITE, loc="upper left",
    )
    ax.grid(axis="y", alpha=0.4)
    watermark(ax)

    save(fig, "chart9_india_sr_trend")




# ─────────────────────────────────────────────
# CHART 4 — Tweet 5: Buttler match-by-match dot plot
# ─────────────────────────────────────────────
def chart_buttler(innings_2026):
    print("Building Chart 4 — Buttler dot plot...")

    name_variants = ["JC Buttler", "Jos Buttler", "J Buttler"]
    scores = []
    for name in name_variants:
        scores = [r["runs"] for r in innings_2026 if r["player"] == name]
        if scores:
            break

    if not scores:
        print("  ⚠ Buttler not found in 2026 data.")
        return

    scores_sorted = sorted(scores)
    x = range(1, len(scores_sorted) + 1)

    fig, ax = plt.subplots(figsize=(10, 5))
    fig.patch.set_facecolor(BG)
    ax.set_facecolor(CARD)

    colors = [GREEN if s >= 30 else RED for s in scores_sorted]
    ax.scatter(x, scores_sorted, s=120, color=colors, zorder=3, edgecolors="none")

    for xi, s, c in zip(x, scores_sorted, colors):
        ax.text(xi, s + 2.5, str(s), ha="center", fontsize=10,
                fontweight="bold", color=c)

    ax.axhline(30, color=GOLD, linewidth=1, linestyle="--", alpha=0.6)
    ax.text(len(scores_sorted), 32, "30-run mark", ha="right",
            fontsize=8, color=GOLD)

    ax.set_xticks(list(x))
    ax.set_xticklabels([f"Inn {i}" for i in x], fontsize=9)
    ax.set_ylabel("Runs Scored", fontsize=11)
    avg_score = round(sum(scores) / len(scores), 1)
    ax.set_title(
        f"Jos Buttler — Innings by Innings (2026 T20 WC)\nAvg: {avg_score}  |  Most scores under 20",
        fontsize=14, fontweight="bold", color=WHITE, pad=14,
    )
    ax.set_ylim(-5, max(scores_sorted) * 1.3)
    ax.grid(axis="y", alpha=0.4)
    watermark(ax)

    save(fig, "chart4_buttler_dotplot")


# ─────────────────────────────────────────────
# CHART 5 — Tweet 6: Win rate stacked bars (150+ vs <150)
# ─────────────────────────────────────────────
def chart_winrate(matches_2026):
    print("Building Chart 5 — Win rate stacked bars...")

    rows = team_totals(matches_2026)
    above = [r for r in rows if r["total"] >= 150]
    below = [r for r in rows if r["total"] < 150]

    def win_loss(group):
        wins   = sum(1 for r in group if r["won"])
        losses = len(group) - wins
        return wins, losses

    w_above, l_above = win_loss(above)
    w_below, l_below = win_loss(below)

    labels   = [f"Scored 150+\n(n={len(above)})", f"Scored <150\n(n={len(below)})"]
    wins_pct = [
        round(w_above / len(above) * 100, 1) if above else 0,
        round(w_below / len(below) * 100, 1) if below else 0,
    ]
    loss_pct = [100 - w for w in wins_pct]

    fig, ax = plt.subplots(figsize=(9, 5))
    fig.patch.set_facecolor(BG)
    ax.set_facecolor(CARD)

    x = np.arange(len(labels))
    w = 0.45
    ax.bar(x, wins_pct, width=w, color=GREEN, label="Won", edgecolor="none")
    ax.bar(x, loss_pct, width=w, bottom=wins_pct, color=RED,
           label="Lost", edgecolor="none")

    for xi, wp, lp in zip(x, wins_pct, loss_pct):
        if wp > 6:
            ax.text(xi, wp / 2, f"{wp}%\nW", ha="center", va="center",
                    fontsize=13, fontweight="bold", color=BG)
        if lp > 6:
            ax.text(xi, wp + lp / 2, f"{lp}%\nL", ha="center", va="center",
                    fontsize=13, fontweight="bold", color=BG)

    ax.set_xticks(x)
    ax.set_xticklabels(labels, fontsize=12)
    ax.set_ylabel("% of matches", fontsize=11)
    ax.set_ylim(0, 115)
    ax.set_title("Batting First — Win Rate by Total Score\n2026 T20 World Cup",
                 fontsize=14, fontweight="bold", color=WHITE, pad=14)
    ax.legend(loc="upper right", fontsize=10,
              facecolor=CARD, edgecolor="none",
              labelcolor=WHITE)
    ax.grid(axis="y", alpha=0.4)
    watermark(ax)

    save(fig, "chart5_winrate_stacked")


# ─────────────────────────────────────────────
# CHART 6 — Tweet 7: Head-to-head comparison table
# ─────────────────────────────────────────────
def chart_headtohead(innings_2026, matches_2026):
    print("Building Chart 6 — Head-to-head table...")

    players_variants = {
        "Sanju Samson":  ["Sanju Samson", "KM Sanju Samson", "SV Samson"],
        "Babar Azam":    ["Babar Azam"],
        "Glenn Maxwell": ["GJ Maxwell", "Glenn Maxwell"],
        "Jos Buttler":   ["JC Buttler", "Jos Buttler", "J Buttler"],
    }

    # Pre-compute sixes from pre-loaded matches (no second disk scan)
    def count_sixes(matches, player_name):
        total = 0
        for m in matches:
            for inn in m.get("innings", []):
                for ov in inn.get("overs", []):
                    for d in ov.get("deliveries", []):
                        if d.get("batter") == player_name and d.get("runs", {}).get("batter") == 6:
                            total += 1
        return total

    rows = []
    for display_name, variants in players_variants.items():
        for v in variants:
            stats = aggregate_player(innings_2026, v)
            if stats["balls"] > 0:
                sixes = count_sixes(matches_2026, v)
                rows.append({
                    "Player":  display_name,
                    "Runs":    stats["runs"],
                    "SR":      f"{stats['sr']:.1f}",
                    "Avg":     f"{stats['avg']:.1f}",
                    "Innings": stats["inns"],
                    "Sixes":   sixes,
                })
                break

    if not rows:
        print("  ⚠ No data for head-to-head.")
        return

    col_labels = ["Player", "Runs", "SR", "Avg", "Inn", "6s"]
    col_keys   = ["Player", "Runs", "SR", "Avg", "Innings", "Sixes"]
    table_data = [[str(r[k]) for k in col_keys] for r in rows]

    fig, ax = plt.subplots(figsize=(11, 4))
    fig.patch.set_facecolor(BG)
    ax.axis("off")

    row_colors = []
    for r in rows:
        if r["Player"] == "Sanju Samson":
            row_colors.append(["#1D9E7533"] * len(col_labels))
        else:
            row_colors.append(["#E24B4A22"] * len(col_labels))

    tbl = ax.table(
        cellText=table_data,
        colLabels=col_labels,
        cellLoc="center",
        loc="center",
        cellColours=row_colors,
    )
    tbl.auto_set_font_size(False)
    tbl.set_fontsize(13)
    tbl.scale(1, 2.2)

    for j in range(len(col_labels)):
        tbl[0, j].set_facecolor("#2A2A2A")
        tbl[0, j].set_text_props(color=WHITE, fontweight="bold")

    sr_idx = col_keys.index("SR")
    for i, r in enumerate(rows):
        cell = tbl[i + 1, sr_idx]
        sr_val = float(r["SR"])
        cell.set_text_props(
            color=GREEN if sr_val >= 150 else (RED if sr_val < 130 else WHITE),
            fontweight="bold",
        )

    ax.set_title(
        "Head-to-Head: Samson vs TukTuk Batters — 2026 T20 WC",
        fontsize=14, fontweight="bold", color=WHITE, pad=16, y=0.98,
    )
    watermark(ax)

    save(fig, "chart6_headtohead")


# ─────────────────────────────────────────────
# CHART 7 — Tweet 8: Fastest centuries dot/number line
# ─────────────────────────────────────────────
def chart_fastest_centuries(all_edition_innings, edition_years):
    print("Building Chart 7 — Fastest centuries number line...")

    all_centuries = []
    for yr in edition_years:
        inn = all_edition_innings.get(yr, [])
        centuries = find_centuries(inn)
        for c in centuries:
            c["edition"] = yr
            all_centuries.append(c)

    if not all_centuries:
        print("  ⚠ No centuries found across editions.")
        return

    all_centuries.sort(key=lambda x: x["balls"])

    players = [f"{c['player'].split()[-1]} ({c['edition']})" for c in all_centuries]
    balls   = [c["balls"] for c in all_centuries]
    colors  = []
    for c in all_centuries:
        if c["balls"] == min(balls):
            colors.append(GOLD)
        elif c["edition"] == "2026":
            colors.append(GREEN)
        else:
            colors.append(NEUTRAL)

    fig, ax = plt.subplots(figsize=(13, max(4, len(balls) * 0.55)))
    fig.patch.set_facecolor(BG)
    ax.set_facecolor(CARD)

    y = range(len(balls))
    ax.scatter(balls, y, s=140, color=colors, zorder=3, edgecolors="none")
    ax.hlines(y, 0, balls, color="#2A2A2A", linewidth=1, zorder=1)

    for xi, yi, p, col in zip(balls, y, players, colors):
        ax.text(xi + 0.8, yi, f"{xi} balls — {p}",
                va="center", fontsize=9.5, color=col)

    ax.set_yticks([])
    ax.set_xlabel("Balls faced to reach 100", fontsize=11)
    ax.set_xlim(0, max(balls) * 1.55)
    ax.set_title(
        "Fastest T20 World Cup Centuries — All Time\n(gold = record, green = 2026)",
        fontsize=14, fontweight="bold", color=WHITE, pad=14,
    )
    ax.grid(axis="x", alpha=0.4)
    watermark(ax)

    save(fig, "chart7_fastest_centuries")


# ─────────────────────────────────────────────
# CHART 8 — Babar SR trend: him vs tournament avg vs Pakistan avg
# ─────────────────────────────────────────────
def chart_babar_trend(all_edition_innings):
    print("Building Chart 8 — Babar SR trend across editions...")

    babar_variants = ["Babar Azam", "Babar Azam Khan"]

    babar_srs   = {}
    tourn_srs   = {}
    pak_srs     = {}

    for yr, inn in all_edition_innings.items():
        # Babar — min 10 balls faced to count
        for name in babar_variants:
            stats = aggregate_player(inn, name)
            if stats["balls"] >= 10:
                babar_srs[yr] = round(stats["sr"], 1)
                break

        # Only include the edition if Babar actually played
        if yr not in babar_srs:
            continue

        # Tournament average SR (min 12 balls)
        tourn_srs[yr] = tournament_avg_sr(inn, min_balls=12)

        # Pakistan team average SR (min 6 balls per batter)
        pak_inn = [r for r in inn if r["team"] == "Pakistan"]
        totals  = defaultdict(lambda: {"runs": 0, "balls": 0})
        for r in pak_inn:
            totals[r["player"]]["runs"]  += r["runs"]
            totals[r["player"]]["balls"] += r["balls"]
        pak_runs  = sum(v["runs"]  for v in totals.values() if v["balls"] >= 6)
        pak_balls = sum(v["balls"] for v in totals.values() if v["balls"] >= 6)
        pak_srs[yr] = round(pak_runs / pak_balls * 100, 1) if pak_balls else 0

    if not babar_srs:
        print("  ⚠ Babar Azam not found in any edition — check Cricsheet name.")
        return

    editions = sorted(babar_srs.keys())
    b_vals   = [babar_srs[e]  for e in editions]
    t_vals   = [tourn_srs[e]  for e in editions]
    p_vals   = [pak_srs[e]    for e in editions]

    x     = np.arange(len(editions))
    width = 0.26

    fig, ax = plt.subplots(figsize=(12, 6))
    fig.patch.set_facecolor(BG)
    ax.set_facecolor(CARD)

    bars_b = ax.bar(x - width, b_vals, width, color=RED,     label="Babar Azam",        edgecolor="none")
    bars_t = ax.bar(x,          t_vals, width, color=NEUTRAL, label="Tournament Avg SR",  edgecolor="none")
    bars_p = ax.bar(x + width,  p_vals, width, color="#4A90D9", label="Pakistan Team Avg SR", edgecolor="none")

    # Value labels on top of each bar
    for bars, vals, col in [(bars_b, b_vals, RED), (bars_t, t_vals, NEUTRAL), (bars_p, p_vals, "#4A90D9")]:
        for bar, val in zip(bars, vals):
            ax.text(
                bar.get_x() + bar.get_width() / 2,
                val + 1.5,
                f"{val:.0f}",
                ha="center", va="bottom",
                fontsize=9, fontweight="bold", color=col,
            )

    # 140 SR floor line
    ax.axhline(140, color=GOLD, linewidth=1.2, linestyle="--", alpha=0.7)
    ax.text(x[-1] + width + 0.22, 141.5, "140 floor", fontsize=8, color=GOLD, va="bottom")

    ax.set_xticks(x)
    ax.set_xticklabels(editions, fontsize=12)
    ax.set_ylabel("Strike Rate", fontsize=11)
    ax.set_ylim(0, max(t_vals + p_vals + b_vals) * 1.22)
    ax.set_title(
        "Babar Azam — Strike Rate vs Tournament Avg vs Pakistan Avg\nAcross T20 World Cups (editions where he played)",
        fontsize=14, fontweight="bold", color=WHITE, pad=14,
    )
    ax.legend(
        fontsize=10, facecolor=CARD, edgecolor="#2A2A2A",
        labelcolor=WHITE, loc="upper left",
    )
    ax.grid(axis="y", alpha=0.4)
    watermark(ax)

    save(fig, "chart8_babar_trend")



def main():
    print(f"\nLoading match data from: {DATA_DIR}\n")

    # Load innings per edition
    all_edition_innings = {}
    for yr, ids in EDITION_MAP.items():
        matches = load_matches(ids)
        print(f"  {yr}: {len(matches)} matches loaded")
        all_edition_innings[yr] = batter_innings(matches)

    innings_2026 = all_edition_innings["2026"]
    matches_2026 = load_matches(WC2026_IDS)
    avg_sr_2026  = tournament_avg_sr(innings_2026)
    print(f"\n2026 Tournament average SR: {avg_sr_2026}\n")

    chart_babar(innings_2026, avg_sr_2026)
    chart_maxwell(all_edition_innings)
    chart_india_batters(innings_2026)
    chart_buttler(innings_2026)
    chart_winrate(matches_2026)
    chart_headtohead(innings_2026, matches_2026)
    chart_fastest_centuries(all_edition_innings, list(EDITION_MAP.keys()))

    chart_babar_trend(all_edition_innings)
    chart_india_sr_trend(all_edition_innings)

    print("\n✅ All charts saved! Look for chart1_*.png through chart9_*.png")
    print("   in the same folder as this script.\n")


if __name__ == "__main__":
    main()
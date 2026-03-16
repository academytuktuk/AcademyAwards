# T20 WC 2026 — TukTuk Academy Data Analysis

Python script that generates 9 cricket analytics charts from Cricsheet ball-by-ball JSON data across 230 T20 World Cup matches (2016–2026).

Built for the [TukTuk Academy Awards 2026 thread](https://x.com/TukTuk_Academy/status/2032456217826861086?s=20) on X — 140K+ views.

---

## Setup

```bash
pip install matplotlib numpy
```

Download match data from [cricsheet.org/downloads](https://cricsheet.org/downloads/) → `icc_mens_t20_world_cup_male_json.zip` → extract.

Update the path in `t20wc_charts.py`:
```python
DATA_DIR = r"path\to\extracted\matches"
```

Run:
```bash
python t20wc_charts.py
```

9 PNGs saved in the same folder.

---

## Methodology

- **Strike rate** — legal deliveries only, wides excluded
- **Average** — runs / dismissals, not-outs excluded
- **Balls to century** — exact delivery batter crosses 100, not full innings length

---

## Files

| File | Description |
|------|-------------|
| `t20wc_charts.py` | Main script |
| `find_player.py` | Find exact Cricsheet player name spellings |

---

## Data

[Cricsheet](https://cricsheet.org/) — open-source ball-by-ball data. Not included in this repo — download directly from their site.

---

*Data: Cricsheet · [@TukTukAcademy](https://x.com/TukTuk_Academy)*

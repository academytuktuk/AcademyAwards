"""
find_player.py
==============
Run this if t20wc_charts.py prints a ⚠ warning for a player not found.
It scans all your JSON files and prints every unique batter name,
so you can find the exact spelling Cricsheet uses.

USAGE:
    python find_player.py
    python find_player.py maxwell        # filter by keyword (case-insensitive)
    python find_player.py buttler
    python find_player.py samson
"""

import json, glob, os, sys

DATA_DIR = r"C:\Users\pasca\Desktop\thread\data\matches"

keyword = sys.argv[1].lower() if len(sys.argv) > 1 else ""

all_names = set()
for fpath in glob.glob(os.path.join(DATA_DIR, "*.json")):
    with open(fpath, encoding="utf-8") as f:
        m = json.load(f)
    for inn in m.get("innings", []):
        for ov in inn.get("overs", []):
            for d in ov.get("deliveries", []):
                all_names.add(d["batter"])

matches = sorted(n for n in all_names if keyword in n.lower()) if keyword else sorted(all_names)

print(f"\n{'Filtered' if keyword else 'All'} player names ({len(matches)} found):\n")
for name in matches:
    print(f"  {name}")
print()

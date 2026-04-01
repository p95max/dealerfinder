"""
One-time utility to build a static German cities dataset for autocomplete.

Fetches the open-source cities.json dataset, filters to German cities (country == "DE"),
deduplicates, sorts alphabetically, and writes a compact JSON array to
static/data/cities_de.json.

Run from the project root:
    python build_cities.py

Output: static/data/cities_de.json  (~3500 city names, UTF-8)
"""

import json
import urllib.request
from pathlib import Path

URL = "https://raw.githubusercontent.com/lutangar/cities.json/master/cities.json"
OUT = Path("../static/data/cities_de.json")

print("Downloading cities.json ...")
with urllib.request.urlopen(URL) as r:
    data = json.load(r)

cities = sorted(
    {c["name"] for c in data if c.get("country") == "DE"}
)

OUT.parent.mkdir(parents=True, exist_ok=True)
OUT.write_text(json.dumps(cities, ensure_ascii=False), encoding="utf-8")

print(f"Done: {len(cities)} cities → {OUT}")
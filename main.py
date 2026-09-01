"""
Entry point. Runs the engine, renders the page, writes index.html.

    python main.py

The output filename matters. GitHub Pages serves index.html, so that is what
the pipeline has to write. This used to write copilot.html, and index.html was
a one-off copy made when the site was first set up — so the daily job faithfully
regenerated a file nobody was serving, and the published page stayed frozen at
the date of that copy.
"""

from pathlib import Path

from engine import build_recommendations, print_brief
from render import render

OUTPUT = Path("index.html")

if __name__ == "__main__":
    recs = build_recommendations()
    print_brief(recs)

    OUTPUT.write_text(render(recs), encoding="utf-8")
    print(f"\nWrote {OUTPUT} — {OUTPUT.stat().st_size:,} bytes")

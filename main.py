"""
Entry point. Runs the engine, renders the page, writes copilot.html.

    python main.py
"""

from pathlib import Path

from engine import build_recommendations, print_brief
from render import render

OUTPUT = Path("copilot.html")

if __name__ == "__main__":
    recs = build_recommendations()
    print_brief(recs)

    OUTPUT.write_text(render(recs), encoding="utf-8")
    print(f"\nWrote {OUTPUT} — {OUTPUT.stat().st_size:,} bytes")
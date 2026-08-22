"""
Luxury Advisor Co-Pilot — interactive version.

Same engine, same data, same rules as main.py. Two things the static page
cannot do:

  1. The weights are adjustable, and the ranking recalculates live.
  2. Advisor decisions are CAPTURED — approve, edit, snooze, dismiss —
     and written to decisions.csv, where they accumulate into the training
     signal that makes the system improve.

That second one is what makes this a co-pilot rather than a dashboard. A
system that proposes but never learns whether it was right is just a
prettier report.

    streamlit run app.py
"""

import csv
from datetime import datetime
from pathlib import Path

import streamlit as st

import engine
from engine import build_recommendations

LOG = Path("decisions.csv")
LOG_COLUMNS = ["timestamp", "client_id", "client_name", "action",
               "decision", "reason", "edit_distance"]

DISMISS_REASONS = [
    "Wrong timing",
    "Wrong product",
    "Wrong channel",
    "Relationship reason",
    "Already handled offline",
]

st.set_page_config(page_title="Maison Aurelle Co-Pilot", layout="wide")


# ---------------------------------------------------------------------------
# Decision capture
# ---------------------------------------------------------------------------

def record(rec, decision, reason="", edit_distance=""):
    """Append one advisor decision to decisions.csv and remember it."""
    new_file = not LOG.exists()
    with LOG.open("a", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        if new_file:
            w.writerow(LOG_COLUMNS)
        w.writerow([datetime.now().isoformat(timespec="seconds"),
                    rec["id"], rec["name"], rec["action"],
                    decision, reason, edit_distance])
    st.session_state.decided[rec["id"]] = f"{decision}{' — ' + reason if reason else ''}"


def load_log():
    if not LOG.exists():
        return []
    with LOG.open(encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


if "decided" not in st.session_state:
    st.session_state.decided = {}


# ---------------------------------------------------------------------------
# Controls — moving any of these re-runs the script from the top
# ---------------------------------------------------------------------------

st.sidebar.header("Scoring weights")
st.sidebar.caption("Move a slider and the ranking recalculates.")

engine.WEIGHTS["relevance"]    = st.sidebar.slider("Relevance", 0, 50, 30)
engine.WEIGHTS["timing"]       = st.sidebar.slider("Timing", 0, 50, 25)
engine.WEIGHTS["channel"]      = st.sidebar.slider("Channel fit", 0, 50, 15)
engine.WEIGHTS["exclusivity"]  = st.sidebar.slider("Exclusivity fit", 0, 50, 15)
engine.WEIGHTS["relationship"] = st.sidebar.slider("Relationship", 0, 50, 10)
engine.WEIGHTS["restraint"]    = st.sidebar.slider("Restraint", 0, 50, 5)

st.sidebar.header("Threshold")
engine.MIN_SCORE = st.sidebar.slider(
    "Minimum score to justify contact", 0, 100, 45,
    help="Below this, staying silent is the better answer.")

st.sidebar.divider()
if st.sidebar.button("Clear decision log"):
    LOG.unlink(missing_ok=True)
    st.session_state.decided = {}
    st.rerun()


# ---------------------------------------------------------------------------
# Recalculate — this happens again on every interaction
# ---------------------------------------------------------------------------

recs = build_recommendations()
acting = sorted([r for r in recs if r["action"] != "NO CONTACT"],
                key=lambda r: -r["score"])
holding = [r for r in recs if r["action"] == "NO CONTACT"]

decided = st.session_state.decided
pending = [r for r in acting if r["id"] not in decided]

st.title("Maison Aurelle — Advisor Co-Pilot")
st.caption("Friday, 21 August 2026 · Isabelle Cheong · 15 clients reviewed")

a, b, c, d = st.columns(4)
a.metric("To review", len(pending))
b.metric("Decided", len(decided))
c.metric("Held back", len(holding))
d.metric("Needs approval", sum(1 for r in pending if r["exception"]))


# ---------------------------------------------------------------------------
# The brief
# ---------------------------------------------------------------------------

st.subheader("Today's approaches")

for r in acting:
    done = decided.get(r["id"])
    flag = "  ⚑ APPROVAL REQUIRED" if r["exception"] else ""
    label = f"**{r['score']}**  ·  {r['name']}  ·  {r['tier']}  ·  {r['action']}{flag}"
    if done:
        label = f"~~{label}~~  ✓ {done}"

    with st.expander(label, expanded=False):
        if done:
            st.success(f"Decision recorded: {done}")
            continue

        left, right = st.columns([2, 1])

        with left:
            if r["exception"]:
                st.warning(r["exception"])

            st.write(f"**Channel** {r['channel']}  ·  **When** {r['when']}")
            st.write(f"**Tone** {r['tone']}")
            if r["product"]:
                st.write(f"**Piece** {r['product']}")

            # Evidence first, draft second — the advisor should read the
            # reasoning before the polished wording.
            st.markdown("**Why**")
            for e in r["evidence"]:
                st.markdown(f"- {e}")

            if r["alternatives"]:
                alts = ", ".join(f"{n} ({s})" for n, s in r["alternatives"])
                st.caption(f"Also considered: {alts}")

        with right:
            st.markdown("**Score breakdown**")
            st.bar_chart(r["dims"])

        st.divider()

        draft = st.text_area("Draft message", value=r["draft"],
                             key=f"draft_{r['id']}", height=110)

        b1, b2, b3, b4 = st.columns(4)

        if b1.button("Approve", key=f"ap_{r['id']}", type="primary"):
            record(r, "Approved")
            st.rerun()

        if b2.button("Approve edited", key=f"ed_{r['id']}"):
            distance = abs(len(draft) - len(r["draft"]))
            record(r, "Edited", edit_distance=distance)
            st.rerun()

        if b3.button("Snooze 7 days", key=f"sn_{r['id']}"):
            record(r, "Snoozed")
            st.rerun()

        with b4:
            reason = st.selectbox("Dismiss because…", [""] + DISMISS_REASONS,
                                  key=f"rs_{r['id']}",
                                  label_visibility="collapsed",
                                  placeholder="Dismiss because…")
            if reason:
                record(r, "Dismissed", reason=reason)
                st.rerun()


# ---------------------------------------------------------------------------
# Silence
# ---------------------------------------------------------------------------

st.subheader("Held back — no contact recommended today")
for r in holding:
    st.markdown(f"**{r['name']}** · {r['tier']} — {r['evidence'][0]}")


# ---------------------------------------------------------------------------
# The learning loop, made visible
# ---------------------------------------------------------------------------

log = load_log()
if log:
    st.divider()
    st.subheader("What advisors are telling the system")

    dismissals = [row for row in log if row["decision"] == "Dismissed"]
    if dismissals:
        tally = {}
        for row in dismissals:
            tally[row["reason"]] = tally.get(row["reason"], 0) + 1
        st.bar_chart(tally)
        st.caption(
            "Dismissal reasons are the training signal. A cluster under one "
            "reason means a scoring weight is wrong — not that the advisor is.")

    edits = [row for row in log if row["decision"] == "Edited"]
    if edits:
        avg = sum(int(e["edit_distance"] or 0) for e in edits) / len(edits)
        st.metric("Average edit distance", f"{avg:.0f} characters",
                  help="Consistently large edits mean the tone model is wrong.")

    with st.expander(f"Full decision log ({len(log)} entries)"):
        st.dataframe(log, use_container_width=True)

st.caption(
    "Gates run before scoring and cannot be outvoted. Consent and the "
    "quarterly cap are never waived; a time-critical occasion may waive "
    "cooling-off, but only with advisor approval.")
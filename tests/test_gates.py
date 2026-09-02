"""
Tests for the clienteling gates.

The README's central claim is that gates run before scoring and cannot be
outvoted: consent, cooling-off, frequency caps and explicit refusals are
absolute, and a persuasive score must never talk the system past something a
client asked for. That is the kind of claim that is true on the day it is
written and quietly stops being true three refactors later, which is what
these tests are for.

The occasion exception is the interesting case. A time-critical occasion may
waive cooling-off - but never consent, never the frequency cap, and never
silently. Each of those three is asserted separately below, because they are
three different promises and only one of them is about cooling-off.

Run with:  python -m pytest -q
"""

import pandas as pd
import pytest

import engine
from engine import (TIER_RANK, build_recommendations, check_gates, derive,
                    load_data, occasion_exception)


@pytest.fixture(scope="session")
def data():
    return load_data()


@pytest.fixture(scope="session")
def recommendations(data):
    return build_recommendations(data)


def consenting(client):
    return client["Marketing_Consent"] == "Yes"


# --- coverage -------------------------------------------------------------

def test_every_client_receives_exactly_one_decision(data, recommendations):
    assert len(recommendations) == len(data["clients"])
    ids = [r["id"] for r in recommendations]
    assert len(ids) == len(set(ids))


def test_every_decision_is_either_an_approach_or_a_refusal(recommendations):
    for rec in recommendations:
        assert str(rec["action"]).strip()


# --- consent is absolute --------------------------------------------------

def test_no_client_without_consent_is_ever_contacted(data, recommendations):
    """
    The one gate with no exception anywhere in the system. If this fails,
    the brief is proposing to contact someone who asked not to be.
    """
    withheld = {
        row["Client_ID"] for _, row in data["clients"].iterrows()
        if not consenting(row)
    }
    assert withheld, "no client in the set has withdrawn consent - untested"

    for rec in recommendations:
        if rec["id"] in withheld:
            assert rec["action"] == "NO CONTACT", (
                f"{rec['id']} withdrew consent and was proposed for "
                f"'{rec['action']}'"
            )


def test_an_occasion_cannot_rescue_a_client_who_withdrew_consent(data):
    """
    Take every client, put them in the most sympathetic possible position -
    an occasion tomorrow, inside cooling-off, room left in the cap - then
    withdraw consent, and confirm the exception refuses to fire.
    """
    for _, client in data["clients"].iterrows():
        row = client.copy()
        row["Marketing_Consent"] = "No"
        row["Occasion_Type"] = "Wedding Anniversary"
        row["Occasion_Date"] = str(engine.TODAY + pd.Timedelta(days=1))[:10]

        facts = {"days_since_contact": 0,
                 "contacts_this_quarter": 0}
        assert occasion_exception(row, facts) is None


# --- the frequency cap is absolute ---------------------------------------

def test_an_occasion_cannot_waive_the_contact_cap(data):
    """
    Cooling-off is a pause and may be waived. The quarterly cap is a budget
    and may not - waiving it would let a client be contacted more times than
    they agreed to, which no occasion justifies.
    """
    for _, client in data["clients"].iterrows():
        row = client.copy()
        row["Marketing_Consent"] = "Yes"
        row["Occasion_Type"] = "Birthday"
        row["Occasion_Date"] = str(engine.TODAY + pd.Timedelta(days=1))[:10]

        facts = {"days_since_contact": 0,
                 "contacts_this_quarter": int(row["Max_Contacts_Quarter"])}
        assert occasion_exception(row, facts) is None


# --- nothing is waived silently ------------------------------------------

def test_a_waived_cooling_off_is_always_flagged_for_approval(recommendations):
    """
    The system may ask to waive cooling-off. It may never do it quietly.
    Every exception raised must say so in words an advisor has to act on.
    """
    waivers = [r for r in recommendations
               if r.get("exception") and "waived" in str(r["exception"]).lower()]
    for rec in waivers:
        assert "APPROVAL REQUIRED" in str(rec["exception"]).upper(), (
            f"{rec['id']} had cooling-off waived without an approval flag"
        )


def test_every_refusal_states_its_reason(recommendations):
    """
    Showing what was refused is the point. A NO CONTACT with no reason is
    indistinguishable from the client simply not being considered.
    """
    for rec in recommendations:
        if rec["action"] == "NO CONTACT":
            assert rec["evidence"], f"{rec['id']} refused with no reason given"


# --- gates outrank scores -------------------------------------------------

def test_a_client_level_block_is_never_overridden_by_a_score(data, recommendations):
    """
    check_gates returns "client"-level blocks that stop every play, not just
    the one being considered. No score, however high, may survive one.

    There is exactly one documented way past such a block: a time-critical
    occasion waiving COOLING-OFF, and only with an approval flag the advisor
    has to act on. A consent or frequency-cap block has no way past at all.
    So this asserts the shape of the exception rather than forbidding it -
    a blocked client who is contacted anyway must have been blocked solely
    by cooling-off, and must carry the flag.
    """
    by_id = {r["id"]: r for r in recommendations}
    plays = data["opportunities"]

    for _, client in data["clients"].iterrows():
        cid = client["Client_ID"]
        facts = derive(cid, data)

        reasons = {
            reason
            for _, play in plays.iterrows()
            for level, reason in check_gates(client, play, facts, "WhatsApp")
            if level == "client"
        }
        if not reasons:
            continue

        rec = by_id[cid]
        if rec["action"] == "NO CONTACT":
            continue

        # Contacted despite a client-level block: only cooling-off qualifies.
        non_waivable = [r for r in reasons if "cooling-off" not in r.lower()]
        assert not non_waivable, (
            f"{cid} was proposed for '{rec['action']}' despite {non_waivable}"
        )
        assert "APPROVAL REQUIRED" in str(rec.get("exception", "")).upper(), (
            f"{cid} had cooling-off waived at score {rec['score']} with no "
            f"approval flag"
        )


def test_a_play_above_the_clients_tier_is_never_proposed(data, recommendations):
    """Exclusivity is a promise to the tier above, not a scoring input."""
    plays = {p["Name"]: p for _, p in data["opportunities"].iterrows()}
    clients = {c["Client_ID"]: c for _, c in data["clients"].iterrows()}

    for rec in recommendations:
        if rec["action"] == "NO CONTACT":
            continue
        play = plays.get(rec["action"])
        if play is None:
            continue
        assert TIER_RANK[clients[rec["id"]]["Client_Tier"]] >= \
            TIER_RANK[play["Min_Tier"]]


# --- every approach is evidenced -----------------------------------------

def test_every_approach_carries_its_evidence(recommendations):
    for rec in recommendations:
        if rec["action"] != "NO CONTACT":
            assert rec["evidence"], f"{rec['id']} proposed with no evidence"


def test_every_approach_names_a_channel(recommendations):
    for rec in recommendations:
        if rec["action"] != "NO CONTACT":
            assert str(rec["channel"]).strip()


def test_no_draft_is_written_for_a_client_who_is_not_being_contacted(recommendations):
    """A drafted message for a held-back client is a message waiting to be sent
    by accident."""
    for rec in recommendations:
        if rec["action"] == "NO CONTACT":
            assert not str(rec.get("draft") or "").strip()


# --- reproducibility ------------------------------------------------------

def test_running_twice_gives_the_same_brief(data, recommendations):
    """
    Drafts are templates, not generated text. The same data must produce a
    byte-identical brief, which is what makes the output auditable.
    """
    again = build_recommendations(data)
    assert [(r["id"], r["action"], r["score"], r["draft"]) for r in recommendations] \
        == [(r["id"], r["action"], r["score"], r["draft"]) for r in again]

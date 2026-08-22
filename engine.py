"""
Luxury Advisor Co-Pilot — recommendation engine
Maison Aurelle · reference date 21 August 2026

Two stages, deliberately separated:

  STAGE 1  GATES    Hard rules. They cannot be outvoted by a high score.
                    Consent, cooling-off, frequency caps, explicit refusals.
                    If every play is gated, the recommendation is silence.

  STAGE 2  SCORING  Six weighted dimensions, 0-100 each. Only ever runs on
                    plays that already survived the gates.

Run it directly:   python engine.py
Import it:         from engine import build_recommendations
"""

from datetime import date, timedelta
from pathlib import Path

import pandas as pd

DATA = Path("data")
TODAY = date(2026, 8, 21)
QUARTER_START = TODAY - timedelta(days=90)

WEIGHTS = {
    "relevance":    30,
    "timing":       25,
    "channel":      15,
    "exclusivity":  15,
    "relationship": 10,
    "restraint":     5,
}

TIER_RANK = {"Emerging": 1, "High Value": 2, "VIC": 3}
SEND_TIME = {"Morning": "10:00", "Late Afternoon": "16:30", "Evening": "19:00"}
MIN_SCORE = 45


def load_data():
    """Read the five tables. Returns them plus two id-indexed lookups."""
    clients = pd.read_csv(DATA / "clients.csv")
    products = pd.read_csv(DATA / "products.csv")
    interactions = pd.read_csv(DATA / "interactions.csv")
    opportunities = pd.read_csv(DATA / "opportunities.csv")
    purchases = pd.read_csv(DATA / "purchases.csv")

    interactions["Interaction_Date"] = pd.to_datetime(
        interactions["Interaction_Date"]).dt.date

    return {
        "clients": clients,
        "products": products,
        "interactions": interactions,
        "opportunities": opportunities,
        "purchases": purchases,
        "clients_by_id": clients.set_index("Client_ID"),
        "products_by_id": products.set_index("Product_ID"),
        "plays": opportunities[opportunities["Opportunity_ID"] != "O008"],
    }


def tags(value):
    return {t.strip().lower() for t in str(value).split(";") if t.strip()}


def derive(client_id, d):
    """Everything the engine knows about a client that is not in their row."""
    mine = d["interactions"][d["interactions"]["Client_ID"] == client_id]

    # Only OUR outreach counts. A client walking in is not us bothering them.
    outbound = mine[mine["Initiated_By"].isin(["Advisor", "System"])]

    days_since = ((TODAY - outbound["Interaction_Date"].max()).days
                  if len(outbound) else 9999)

    # A decline IS a reply. Only silence counts as a channel failure.
    channels = {}
    for ch in outbound["Channel"].unique():
        sent = outbound[outbound["Channel"] == ch]
        replied = int((sent["Client_Response"] != "No Response").sum())
        channels[ch] = f"{replied}/{len(sent)}"

    return {
        "days_since_contact": days_since,
        "contacts_this_quarter": int(
            (outbound["Interaction_Date"] >= QUARTER_START).sum()),
        "channel_response": channels,
        "refused_channels": set(
            mine[mine["Outcome"] == "Opt-out of channel"]["Channel"]),
        "declined_types": set(
            mine[mine["Client_Response"].isin(["Declined", "Negative"])]
                ["Interaction_Type"]),
    }


def allowed_channels(client, play, facts):
    options = [c.strip() for c in str(play["Channel_Options"]).split(";")]
    if "Advisor-selected" in options:
        options = ["WhatsApp", "Phone", "Email"]

    negatives = str(client["Negative_Preferences"]).lower()
    ok = []
    for ch in options:
        if ch not in ("WhatsApp", "Phone", "Email"):
            continue
        if ch in facts["refused_channels"]:
            continue
        if ch == "Phone" and "do not call" in negatives:
            continue
        if ch == "WhatsApp" and "no whatsapp" in negatives:
            continue
        ok.append(ch)
    return ok


def check_gates(client, play, facts, channel):
    """
    Return [(level, reason)]. Empty means the play is allowed.
    level "client" blocks EVERY play; level "play" blocks only this one.
    """
    blocked = []
    negatives = str(client["Negative_Preferences"]).lower()

    if client["Marketing_Consent"] != "Yes":
        blocked.append(("client", "Marketing consent withdrawn."))

    if facts["days_since_contact"] < client["Cooling_Off_Days"]:
        blocked.append(("client",
            f"Contacted {facts['days_since_contact']} day(s) ago; "
            f"cooling-off is {client['Cooling_Off_Days']} days."))

    if facts["contacts_this_quarter"] >= client["Max_Contacts_Quarter"]:
        blocked.append(("client",
            f"{facts['contacts_this_quarter']} contacts this quarter; "
            f"cap is {client['Max_Contacts_Quarter']}."))

    if TIER_RANK[client["Client_Tier"]] < TIER_RANK[play["Min_Tier"]]:
        blocked.append(("play", f"Reserved for {play['Min_Tier']} and above."))

    if play["Requires_Event_Comfort"] == "Yes":
        if "dislikes large events" in str(client["Event_Preference"]).lower():
            blocked.append(("play", "Client dislikes large events."))
        if "declines all event invitations" in negatives:
            blocked.append(("play", "Client declines all invitations as a rule."))
        if "no group events" in negatives:
            blocked.append(("play", "Private salon appointments only."))

    if channel is None:
        blocked.append(("play", "No permitted channel for this play."))

    return blocked


def pick_product(client_id, client, play, d):
    """The best piece this play can put in front of this client."""
    if play["Opportunity_Type"] == "Relationship Gesture":
        return None, []

    products_by_id = d["products_by_id"]
    ids = [p.strip() for p in str(play["Linked_Products"]).split(";") if p.strip()]

    owned = set(d["purchases"][d["purchases"]["Client_ID"] == client_id]["Product_ID"])
    known = [p for p in owned if p in products_by_id.index]
    owned_colls = set(products_by_id.loc[known]["Collection"]) if known else set()

    best, best_score, best_why = None, -1, []
    for pid in ids:
        if pid not in products_by_id.index or pid in owned:
            continue
        prod = products_by_id.loc[pid]
        s, why = 0, []
        if tags(client["Preferred_Style"]) & tags(prod["Style_Tags"]):
            s += 3
            why.append("style match")
        if tags(client["Preferred_Categories"]) & tags(prod["Category"]):
            s += 3
            why.append("category match")
        if prod["Collection"] in owned_colls:
            s += 4
            why.append(f"already owns {prod['Collection']}")
        if s > best_score:
            best, best_score, best_why = prod, s, why
    return best, best_why


def score(client_id, client, play, facts, channel, d):
    dims, evidence = {}, []

    r = 0
    if (tags(client["Preferred_Categories"]) & tags(play["Relevant_Category"])
            or "multiple" in tags(play["Relevant_Category"])):
        r += 45
    interest = str(client["Recent_Interest"]).lower()
    if interest != "nan" and any(
            w in str(play["Relevant_Category"]).lower() or w in play["Name"].lower()
            for w in interest.split()):
        r += 25
        evidence.append(f"Recent interest: {client['Recent_Interest']}.")

    product, why = pick_product(client_id, client, play, d)
    if product is not None:
        r += 30
        evidence.append(f"{product['Product_Name']} - {'; '.join(why)}.")
    elif (play["Opportunity_Type"] == "Relationship Gesture"
            and not pd.isna(client["Occasion_Date"])):
        days_to = (date.fromisoformat(client["Occasion_Date"]) - TODAY).days
        if 0 <= days_to <= 30:
            r += 30
            evidence.append("Gesture carries no product by design.")
    dims["relevance"] = min(100, r)

    t = 40
    if not pd.isna(client["Occasion_Date"]):
        days_to = (date.fromisoformat(client["Occasion_Date"]) - TODAY).days
        if 0 <= days_to <= 30:
            t = 100
            evidence.append(f"{client['Occasion_Type']} in {days_to} days.")
        elif days_to <= 75:
            t = 60
    if not pd.isna(play["Window_End"]):
        left = (date.fromisoformat(play["Window_End"]) - TODAY).days
        if 0 <= left <= 14:
            t = min(100, t + 20)
            evidence.append(f"Window closes in {left} days.")
    if facts["days_since_contact"] > 90:
        t = min(100, t + 25)
        evidence.append(f"Silent for {facts['days_since_contact']} days.")
    dims["timing"] = min(100, t)

    hit = facts["channel_response"].get(channel)
    if hit:
        replied, sent = (int(x) for x in hit.split("/"))
        dims["channel"] = int(40 + (replied / sent) * 60)
        evidence.append(f"{channel}: {hit} outreach drew a reply.")
    else:
        dims["channel"] = 60

    rank = {"Medium": 1, "High": 2, "Very High": 3}
    want = rank.get(play["Exclusivity_Level"], 1)
    have = TIER_RANK[client["Client_Tier"]]
    e = 100 - abs(want - have) * 25
    if product is not None and product["Allocation_Limited"] == "Yes":
        if have == 3:
            e += 15
            evidence.append(
                f"{product['Product_Name']} is allocation-limited; "
                f"{client['Client_Tier']} standing supports nomination.")
        else:
            e -= 30
    dims["exclusivity"] = max(0, min(100, e))

    strength = {"Developing": 40, "Moderate": 70, "Strong": 100}[
        client["Relationship_Strength"]]
    if play["Opportunity_Type"] == "Relationship Gesture" and strength < 70:
        strength = 30
    dims["relationship"] = strength

    cap = client["Max_Contacts_Quarter"]
    dims["restraint"] = int(
        max(0, cap - facts["contacts_this_quarter"]) / cap * 100)

    total = sum(dims[k] * WEIGHTS[k] for k in WEIGHTS) / 100
    return round(total, 1), dims, evidence, product


def choose_channel(client, play, facts):
    """Prefer the declared channel; override only if it has proven silent."""
    options = allowed_channels(client, play, facts)
    if not options:
        return None, None

    declared = client["Declared_Channel"]
    hit = facts["channel_response"].get(declared)
    if hit:
        replied, sent = (int(x) for x in hit.split("/"))
        if sent >= 2 and replied == 0:
            alts = []
            for ch, h in facts["channel_response"].items():
                if ch == "In Person" or ch not in options:
                    continue
                r, s = (int(x) for x in h.split("/"))
                if s >= 2 and r / s > 0.5:
                    alts.append((r / s, ch, h))
            if alts:
                alts.sort(reverse=True)
                _, winner, wh = alts[0]
                return winner, (
                    f"Declared channel {declared} drew {hit} - no reply ever. "
                    f"{winner} draws {wh}. Overriding to {winner}.")

    return (declared if declared in options else options[0]), None


def when_to_send(client):
    slot = client["Preferred_Contact_Time"]
    label = f"{slot} ({SEND_TIME.get(slot, '11:00')})"
    if "weekend" in str(client["Negative_Preferences"]).lower():
        label += " - weekdays only"
    return label


def draft_message(client, play, product):
    """Deterministic templates, not a language model - on purpose."""
    first = client["Client_Name"].split()[0]
    piece = product["Product_Name"] if product is not None else "the new pieces"
    kind = play["Opportunity_Type"]

    occasion = ""
    if not pd.isna(client["Occasion_Date"]):
        days_to = (date.fromisoformat(client["Occasion_Date"]) - TODAY).days
        if 0 <= days_to <= 30:
            occasion = f" with your {str(client['Occasion_Type']).lower()} approaching"

    if kind == "Private Preview":
        body = (f"Good afternoon {first}, I have set aside a quiet hour at the "
                f"boutique to show you the {piece}. No one else will be in the "
                f"salon. Would one afternoon this week suit you?")
    elif kind == "Early Access":
        body = (f"{first}, a small number of pieces arrive before they are shown "
                f"more widely, and I thought of you for the {piece}. May I hold "
                f"one for your consideration?")
    elif kind == "Event Invitation":
        body = (f"{first}, we are hosting a small preview of the new collection "
                f"and I would love for you to join us. The {piece} will be among "
                f"the pieces shown. May I add your name?")
    elif kind == "Boutique Appointment":
        body = (f"{first}, would you like to come in for an unhurried hour? "
                f"I have put a few things aside, including the {piece}.")
    elif kind == "Relationship Gesture":
        body = (f"{first}, thinking of you{occasion}. Nothing needed from you "
                f"at all - simply wanted to send my warmest wishes.")
    elif kind == "Service Outreach":
        body = (f"{first}, it has been a little while since we last cared for "
                f"your pieces. If useful, I can arrange a complimentary "
                f"conditioning at your convenience.")
    else:
        body = ""

    if "no promotional language" in str(client["Negative_Preferences"]).lower():
        for word in ("exclusive", "special offer", "limited time"):
            body = body.replace(word, "")
    return body


def occasion_exception(client, facts):
    """
    A time-critical occasion may waive cooling-off - never consent, never the
    frequency cap, and never silently. The system asks; the advisor decides.
    """
    if pd.isna(client["Occasion_Date"]):
        return None
    days_to = (date.fromisoformat(client["Occasion_Date"]) - TODAY).days
    if not (0 <= days_to <= 14):
        return None
    if client["Marketing_Consent"] != "Yes":
        return None
    if facts["contacts_this_quarter"] >= client["Max_Contacts_Quarter"]:
        return None
    if facts["days_since_contact"] >= client["Cooling_Off_Days"]:
        return None
    return (f"{client['Occasion_Type']} in {days_to} days. Cooling-off "
            f"({facts['days_since_contact']}/{client['Cooling_Off_Days']} days) "
            f"waived - ADVISOR APPROVAL REQUIRED.")


def build_recommendations(d=None):
    """Score every client against every play; return one decision each."""
    if d is None:
        d = load_data()

    results = []
    for cid in d["clients"]["Client_ID"]:
        client = d["clients_by_id"].loc[cid]
        facts = derive(cid, d)
        exc = occasion_exception(client, facts)

        candidates, blocks = [], []
        for _, play in d["plays"].iterrows():
            ch, note = choose_channel(client, play, facts)
            gate = check_gates(client, play, facts, ch)

            if exc:
                gate = [(l, r) for l, r in gate if "cooling-off" not in r]

            if gate:
                blocks.append(gate)
                continue

            total, dims, ev, prod = score(cid, client, play, facts, ch, d)
            candidates.append({"play": play, "channel": ch, "note": note,
                               "score": total, "dims": dims, "evidence": ev,
                               "product": prod})

        candidates.sort(key=lambda c: -c["score"])

        if not candidates or candidates[0]["score"] < MIN_SCORE:
            reasons = []
            for gate in blocks:
                for level, r in gate:
                    if level == "client" and r not in reasons:
                        reasons.append(r)
            results.append({
                "id": cid, "name": client["Client_Name"],
                "tier": client["Client_Tier"], "action": "NO CONTACT",
                "score": 0, "channel": None, "product": None, "dims": {},
                "evidence": reasons or ["Nothing scored high enough."],
                "exception": None, "alternatives": [], "draft": "",
                "when": None, "tone": None})
            continue

        best = candidates[0]
        results.append({
            "id": cid, "name": client["Client_Name"],
            "tier": client["Client_Tier"], "action": best["play"]["Name"],
            "score": best["score"], "channel": best["channel"],
            "product": None if best["product"] is None
                       else best["product"]["Product_Name"],
            "evidence": ([best["note"]] if best["note"] else []) + best["evidence"],
            "exception": exc,
            "alternatives": [(c["play"]["Name"], c["score"])
                             for c in candidates[1:3]],
            "draft": draft_message(client, best["play"], best["product"]),
            "when": when_to_send(client),
            "tone": best["play"]["Suggested_Tone"],
            "dims": best["dims"]})

    return results


def print_brief(recs):
    acting = sorted([r for r in recs if r["action"] != "NO CONTACT"],
                    key=lambda r: -r["score"])
    holding = [r for r in recs if r["action"] == "NO CONTACT"]

    print("=" * 78)
    print(f"MAISON AURELLE - ADVISOR CO-PILOT     {TODAY.strftime('%A, %d %B %Y')}")
    print("=" * 78)
    print(f"{len(recs)} clients | {len(acting)} actions | "
          f"{len(holding)} held back\n")

    for r in acting:
        flag = "  ** APPROVAL **" if r["exception"] else ""
        print(f"{r['score']:>5}  {r['id']}  {r['name']:20} {r['tier']:11} "
              f"{r['action'][:34]:36} {r['channel']:9}{flag}")

    print(f"\n{'-' * 78}\nHELD BACK - no contact recommended today\n{'-' * 78}")
    for r in holding:
        print(f"  {r['id']}  {r['name']:20} {r['tier']:11} {r['evidence'][0]}")


if __name__ == "__main__":
    print_brief(build_recommendations())
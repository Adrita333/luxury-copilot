### ▶ [Live interactive app](https://luxury-copilot.streamlit.app)
### 📄 [Static daily brief](https://adrita333.github.io/luxury-copilot/)
### 📓 [Full build notebook](https://github.com/Adrita333/luxury-copilot/blob/main/Untitled0.ipynb)

# Luxury Advisor Co-Pilot

A daily brief for luxury client advisors. It reads five tables and produces
one ranked list: which client to approach today, with which piece, on which
channel, at what time, in what tone — and for some clients, a recommendation
to say nothing at all.

## The data

| File | Grain | Rows |
|---|---|---|
| `clients.csv` | one client | 15 |
| `products.csv` | one piece | 25 |
| `opportunities.csv` | one outreach play | 8 |
| `interactions.csv` | one conversation | 52 |
| `purchases.csv` | one receipt line | 60 |

## How it works

**Gates run before scoring and cannot be outvoted.** Consent, cooling-off
periods, frequency caps and explicit refusals are absolute. A system that
scores first and filters afterwards will eventually let a persuasive score
talk it past something a client asked for.

**What survives is scored on six dimensions** — relevance, timing, channel
fit, exclusivity fit, relationship strength and contact restraint.

**Every recommendation carries its evidence**, citing the rows it used.

## Today's output

15 clients reviewed, 12 approaches proposed, 3 deliberately left alone,
1 flagged for advisor approval where a birthday conflicts with a
cooling-off rule.

## Design note

This is a co-pilot, not an agent. It automates the noticing, never the
saying. Drafts are templates rather than generated text, so every
recommendation is auditable — an LLM would sit in the drafting layer,
under the same tone rules, with the advisor still approving every send.

Data is entirely synthetic.

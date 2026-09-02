# Luxury Advisor Co-Pilot

A daily brief for luxury client advisors. It reads five tables and produces
one ranked list: which client to approach today, with which piece, on which
channel, at what time, in what tone — and for some clients, a recommendation
to say nothing at all.

[![The daily brief — twelve ranked approaches, three held back](assets/brief.png)](https://adrita333.github.io/luxury-copilot/)

**[▶ Live app](https://luxury-copilot.streamlit.app)** ·
**[📄 Today's brief](https://adrita333.github.io/luxury-copilot/)** ·
[📓 Build notebook](https://github.com/Adrita333/luxury-copilot/blob/main/Luxury_Advisor.ipynb)

<sub>*The static brief rebuilds itself every morning at 07:00 IST via GitHub Actions —
the date in its header is today's.*</sub>

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
1 flagged for advisor approval where a personal occasion conflicts with a
cooling-off rule.

## Design note

This is a co-pilot, not an agent. It automates the noticing, never the
saying. Drafts are templates rather than generated text, so every
recommendation is auditable — an LLM would sit in the drafting layer,
under the same tone rules, with the advisor still approving every send.

Data is entirely synthetic.

"""
Luxury Advisor Co-Pilot — interface rendering.

Takes recommendations from engine.py and produces one self-contained HTML
file. The layout follows one rule: EVIDENCE IS VISIBLE, THE DRAFT IS
COLLAPSED. If the polished message is the first thing an advisor sees, they
will send it without reading why.
"""

import json
from datetime import date

# Plain string with __DATA__ and __DATE__ placeholders rather than an f-string,
# because CSS is full of braces and an f-string reads every one as a variable.
TEMPLATE = """<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Maison Aurelle - Advisor Co-Pilot</title>

<!-- Link previews. Crawlers for LinkedIn, WhatsApp, Slack and Google do not
     run the script below, so without these tags the only text they can find
     is the "Held back" heading, and every shared link is previewed as though
     nothing was recommended. These are static and describe the real brief. -->
<meta name="description" content="__DESC__">
<meta property="og:type" content="website">
<meta property="og:title" content="Maison Aurelle - Advisor Co-Pilot">
<meta property="og:description" content="__DESC__">
<meta property="og:url" content="https://adrita333.github.io/luxury-copilot/">
<meta property="og:image"
      content="https://raw.githubusercontent.com/Adrita333/luxury-copilot/main/assets/brief.png">
<meta name="twitter:card" content="summary_large_image">
<style>
*{box-sizing:border-box}
body{margin:0;background:#faf8f5;color:#1c1a17;
 font:15px/1.6 Georgia,'Times New Roman',serif}
.wrap{max-width:1080px;margin:0 auto;padding:48px 24px 80px}
header{border-bottom:1px solid #ded6cb;padding-bottom:24px;margin-bottom:8px}
h1{font-size:26px;font-weight:400;letter-spacing:.06em;margin:0 0 6px}
.sub{color:#6b645c;font-size:13px;letter-spacing:.04em}
.bar{position:sticky;top:0;background:#faf8f5;padding:16px 0;
 border-bottom:1px solid #ded6cb;margin-bottom:28px;font-size:13px;
 color:#6b645c;letter-spacing:.04em;z-index:5}
.bar b{color:#1c1a17;font-weight:400}
h2{font-size:12px;text-transform:uppercase;letter-spacing:.16em;
 color:#8a7355;font-weight:400;margin:40px 0 14px}
.card{background:#fff;border:1px solid #e6e0d8;padding:22px 24px;margin-bottom:14px}
.card.done{opacity:.4}
.card.hold{background:transparent;border-style:dashed}
.top{display:flex;justify-content:space-between;align-items:baseline;gap:16px}
.who{font-size:19px}
.tier{font-size:11px;letter-spacing:.14em;text-transform:uppercase;
 color:#8a7355;margin-left:10px}
.score{font-size:13px;color:#6b645c;white-space:nowrap}
.act{margin:12px 0 2px;font-size:16px;color:#3f3a33}
.meta{font-size:13px;color:#6b645c;margin-bottom:14px}
.meta span{margin-right:18px}
.flag{background:#fdf6e6;border-left:3px solid #b07d2b;padding:10px 14px;
 font-size:13px;margin:12px 0}
ul{margin:0 0 14px;padding-left:18px;font-size:13.5px;color:#4a443c}
li{margin-bottom:4px}
details{border-top:1px solid #efeae3;padding-top:12px;margin-bottom:14px}
summary{cursor:pointer;font-size:12px;letter-spacing:.12em;
 text-transform:uppercase;color:#8a7355}
.draft{background:#f7f4ef;padding:16px;margin-top:12px;font-style:italic;color:#3f3a33}
.alt{font-size:12px;color:#8d857b;margin-bottom:14px}
button{font:inherit;font-size:13px;padding:7px 16px;margin-right:8px;
 border:1px solid #cfc6b9;background:#fff;color:#3f3a33;cursor:pointer}
button:hover{border-color:#8a7355}
button.pri{background:#3f3a33;color:#faf8f5;border-color:#3f3a33}
select{font:inherit;font-size:13px;padding:6px;margin-top:10px;
 border:1px solid #cfc6b9;background:#fff;display:none}
.status{font-size:12px;letter-spacing:.1em;text-transform:uppercase;color:#8a7355}
</style></head><body><div class="wrap">
<header><h1>MAISON AURELLE</h1>
<div class="sub">Advisor Co-Pilot &middot; __DATE__ &middot; Isabelle Cheong</div>
</header>
<div class="bar" id="bar"></div>
<h2>Recommended today</h2>
<noscript><p>This brief renders its cards with JavaScript. Enable it, or read
the ranked list in <code>store/</code> in the repository.</p></noscript>
<div id="act"></div>
<h2>Held back &mdash; no contact recommended today</h2>
<div id="hold"></div>
</div>
<script>
const DATA = __DATA__;
const REASONS = ['Wrong timing','Wrong product','Wrong channel',
                 'Relationship reason','Already handled offline'];
let done = 0, dismissed = 0;

function esc(s){return String(s).replace(/[&<>]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;'}[c]));}

function bar(){
  const total = DATA.filter(r=>r.action!=='NO CONTACT').length;
  document.getElementById('bar').innerHTML =
    `<b>${total-done}</b> to review &nbsp;&middot;&nbsp; <b>${done-dismissed}</b> approved` +
    ` &nbsp;&middot;&nbsp; <b>${dismissed}</b> dismissed &nbsp;&middot;&nbsp; ` +
    `<b>${DATA.filter(r=>r.action==='NO CONTACT').length}</b> deliberately not contacted`;
}

function card(r){
  const d = document.createElement('div');
  d.className = 'card' + (r.action==='NO CONTACT' ? ' hold' : '');
  let h = `<div class="top"><div class="who">${esc(r.name)}
      <span class="tier">${esc(r.tier)}</span></div>`;
  if(r.action!=='NO CONTACT') h += `<div class="score">score ${r.score}</div>`;
  h += `</div><div class="act">${esc(r.action)}</div>`;
  if(r.channel) h += `<div class="meta"><span>${esc(r.channel)}</span>
      <span>${esc(r.when||'')}</span><span>${esc(r.tone||'')}</span></div>`;
  if(r.product) h += `<div class="meta"><span>Piece &mdash; ${esc(r.product)}</span></div>`;
  if(r.exception) h += `<div class="flag">${esc(r.exception)}</div>`;
  h += '<ul>' + r.evidence.map(e=>`<li>${esc(e)}</li>`).join('') + '</ul>';
  if(r.draft) h += `<details><summary>Show draft message</summary>
      <div class="draft">${esc(r.draft)}</div></details>`;
  if(r.alternatives.length) h += `<div class="alt">Also considered: ` +
      r.alternatives.map(a=>`${esc(a[0])} (${a[1]})`).join(', ') + `</div>`;
  if(r.action!=='NO CONTACT'){
    h += `<div class="actions">
      <button class="pri">Approve</button><button>Edit</button>
      <button>Snooze</button><button>Dismiss</button>
      <select><option value="">Why dismiss?</option>` +
      REASONS.map(x=>`<option>${x}</option>`).join('') + `</select></div>`;
  }
  d.innerHTML = h;
  const box = d.querySelector('.actions');
  if(box){
    const [ap,ed,sn,di] = box.querySelectorAll('button');
    const sel = box.querySelector('select');
    const finish = (label,isDismiss)=>{
      box.innerHTML = `<span class="status">${label}</span>`;
      d.classList.add('done'); done++; if(isDismiss) dismissed++; bar();
    };
    ap.onclick = ()=>finish('Approved &mdash; queued for send');
    ed.onclick = ()=>finish('Edited &mdash; advisor rewrote the draft');
    sn.onclick = ()=>finish('Snoozed &mdash; resurfaces in 7 days');
    di.onclick = ()=>{ sel.style.display='block'; sel.focus(); };
    sel.onchange = ()=>{ if(sel.value) finish('Dismissed &mdash; '+sel.value, true); };
  }
  return d;
}

DATA.filter(r=>r.action!=='NO CONTACT')
    .sort((a,b)=>b.score-a.score)
    .forEach(r=>document.getElementById('act').appendChild(card(r)));
DATA.filter(r=>r.action==='NO CONTACT')
    .forEach(r=>document.getElementById('hold').appendChild(card(r)));
bar();
</script></body></html>"""


def clean(r):
    """Convert one recommendation into plain JSON-safe types."""
    return {
        "id": r["id"], "name": r["name"], "tier": r["tier"],
        "action": r["action"], "score": float(r["score"]),
        "channel": r["channel"], "product": r["product"],
        "when": r["when"], "tone": r["tone"],
        "evidence": [str(e) for e in r["evidence"]],
        "exception": r["exception"], "draft": r["draft"],
        "alternatives": [[a, float(s)] for a, s in r["alternatives"]],
        "dims": {k: int(v) for k, v in r.get("dims", {}).items()},
    }


def today_stamp():
    """
    The date shown in the header.

    This used to be a literal inside TEMPLATE, so the daily job regenerated
    the page faithfully and stamped the same date on it every time - the
    brief was current and looked ten days stale.

    Built from parts rather than one strftime because "%-d" (day without a
    leading zero) is a GNU extension and is not portable off Linux. The
    runner is UTC; the 07:05 IST schedule is 01:35 UTC on the same calendar
    day, so the date is right.
    """
    d = date.today()
    return f"{d:%A}, {d.day} {d:%B %Y}"


def preview_text(recs):
    """
    The one sentence a link preview gets.

    Built from the same recommendations the page renders, so a shared link
    never describes a different brief from the one it opens.
    """
    approaches = sum(1 for r in recs if r["action"] != "NO CONTACT")
    held = len(recs) - approaches
    return (f"{today_stamp()}. {approaches} client approaches ranked with "
            f"channel, timing and a drafted message; {held} held back, each "
            f"with the reason shown.")


def render(recs):
    """Recommendations in, complete HTML page out."""
    payload = json.dumps([clean(r) for r in recs])
    # __DATE__ and __DESC__ are substituted BEFORE __DATA__ so the injected
    # JSON is never itself scanned for placeholders.
    return (TEMPLATE
            .replace("__DATE__", today_stamp())
            .replace("__DESC__", preview_text(recs))
            .replace("__DATA__", payload))

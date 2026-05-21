#!/usr/bin/env python3
"""Build interactive HTML dashboard — v4: HHLR risk-encircled scan.

Adds:
- Current SI Prime column (color-coded by vendor)
- HHLR Score column (0-10, color-graded green->amber->red)
- Encirclement: top-quartile rows get a red glyph ring on the operator name
- Sortable on HHLR column descending by default
- Hover on HHLR cell shows axis breakdown (L, A, G, D, C)
"""
import csv
import html
import re
from pathlib import Path

CSV_PATH = Path("/home/user/workspace/NA-Nuclear-Utilities/na_nuclear_utilities.csv")
HTML_PATH = Path("/home/user/workspace/NA-Nuclear-Utilities/index.html")

MD_LINK_RE = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")

def md_to_links(text: str):
    if not text:
        return []
    return [(m.group(1).strip(), m.group(2).strip()) for m in MD_LINK_RE.finditer(text)]

def render_source_links(text: str) -> str:
    links = md_to_links(text)
    if not links:
        return ""
    chips = []
    for i, (label, url) in enumerate(links, 1):
        chips.append(f'<a class="srcchip" href="{html.escape(url, quote=True)}" target="_blank" rel="noopener" title="{html.escape(label)}">[{i}]</a>')
    return " " + "".join(chips)

def deployment_cell(value: str, source_md: str) -> str:
    v = (value or "").strip(); vl = v.lower()
    if vl in ("", "unknown"): label, cls = "Unknown", "tag-unknown"
    elif "public cloud" in vl or "grow" in vl: label, cls = "S/4 Public (GROW)", "tag-grow"
    elif "private cloud" in vl or "rise" in vl: label, cls = "S/4 Private (RISE)", "tag-rise"
    elif "on-prem s/4" in vl: label, cls = "On-Prem S/4", "tag-s4onprem"
    elif "ecc" in vl: label, cls = "On-Prem ECC", "tag-ecc"
    else: label, cls = v, "tag-unknown"
    return f'<span class="tag {cls}">{html.escape(label)}</span>{render_source_links(source_md)}'

def signed_cell(value: str) -> str:
    v = (value or "").strip(); vl = v.lower()
    if vl in ("", "unknown"): return '<span class="muted">—</span>'
    if "live" in vl: return '<span class="tag tag-live">Live</span>'
    if "transition" in vl: return '<span class="tag tag-transition">Transition</span>'
    if vl.startswith("yes"): return '<span class="tag tag-signed">Signed</span>'
    if vl.startswith("no") or "still on ecc" in vl: return '<span class="tag tag-no">No</span>'
    return f'<span class="muted">{html.escape(v)}</span>'

def si_cell(prime: str, evidence: str, source_md: str) -> str:
    p = (prime or "").strip()
    if not p or p.lower() == "unknown":
        return '<span class="muted">—</span>'
    pl = p.lower()
    cls = "si-other"
    if "accenture" in pl: cls = "si-acn"
    elif "deloitte" in pl: cls = "si-dt"
    elif "ibm" in pl: cls = "si-ibm"
    elif "capgemini" in pl: cls = "si-cg"
    elif "wipro" in pl: cls = "si-wpr"
    elif "tcs" in pl: cls = "si-tcs"
    elif "cgi" in pl: cls = "si-cgi"
    elif "indra" in pl: cls = "si-other"
    return f'<span class="si-tag {cls}" title="{html.escape(evidence or "")}">{html.escape(p)}</span>{render_source_links(source_md)}'

def exec_chip(role: str, name: str, url: str) -> str:
    n = (name or "").strip()
    if not n or n.lower() == "unknown":
        return f'<span class="exec"><span class="role">{role}</span><span class="muted">—</span></span>'
    li = ""
    if url and url.startswith("http"):
        li = f' <a class="lilink" href="{html.escape(url, quote=True)}" target="_blank" rel="noopener" title="LinkedIn">in</a>'
    return f'<span class="exec"><span class="role">{role}</span>{html.escape(n)}{li}</span>'

def csat_cell(rating: str, source_md: str) -> str:
    r = (rating or "").strip()
    if not r or r.lower() == "unknown":
        return '<span class="muted">—</span>'
    short = r if len(r) <= 180 else r[:177] + "…"
    return f'<span title="{html.escape(r)}">{html.escape(short)}</span>{render_source_links(source_md)}'

def reactor_cell(text: str) -> str:
    t = (text or "").strip()
    if not t: return '<span class="muted">—</span>'
    sites = [s.strip() for s in t.split(";") if s.strip()]
    n = len(sites)
    return f'<span class="reactor-count" title="{html.escape(t)}">{n}</span>'

def hhlr_cell(score: str, L: str, A: str, G: str, D: str, C: str, encircled: str) -> str:
    try:
        sf = float(score)
    except Exception:
        return '<span class="muted">—</span>'
    if sf >= 6.4: cls = "hhlr-red"
    elif sf >= 5.5: cls = "hhlr-amber"
    else: cls = "hhlr-green"
    tooltip = f"L={L} (lock-in) · A={A} (architecture) · G={G} (governance) · D={D} (decision opacity) · C={C} (harm surface)"
    ring = '<span class="encircle" title="Encircled — top quartile HHLR">●</span> ' if encircled.lower() == "yes" else ""
    return f'{ring}<span class="hhlr {cls}" title="{html.escape(tooltip)}">{sf:.1f}</span>'

# Load CSV
with open(CSV_PATH, newline="", encoding="utf-8") as f:
    reader = csv.DictReader(f)
    fieldnames = reader.fieldnames
    rows = list(reader)

total = len(rows)
DEPLOY_KEY = next(c for c in fieldnames if c.startswith("SAP Deployment Class"))
SIGNED_KEY = next(c for c in fieldnames if c.startswith("Signed for S/4"))
CSAT_SRC_KEY = next(c for c in fieldnames if c.startswith("CSAT Source URL"))

# Summary counts
deploy_counts = {"On-Prem ECC": 0, "On-Prem S/4": 0, "S/4 Private (RISE)": 0, "S/4 Public (GROW)": 0, "Unknown": 0}
signed_counts = {"Live": 0, "Signed": 0, "Transition": 0, "No": 0, "Unknown": 0}
country_counts = {}
encircled_count = 0
si_counts = {}

for r in rows:
    d = (r.get(DEPLOY_KEY) or "").lower()
    if "public cloud" in d or "grow" in d: deploy_counts["S/4 Public (GROW)"] += 1
    elif "private cloud" in d or "rise" in d: deploy_counts["S/4 Private (RISE)"] += 1
    elif "on-prem s/4" in d: deploy_counts["On-Prem S/4"] += 1
    elif "ecc" in d: deploy_counts["On-Prem ECC"] += 1
    else: deploy_counts["Unknown"] += 1

    s = (r.get(SIGNED_KEY) or "").lower()
    if "live" in s: signed_counts["Live"] += 1
    elif "transition" in s: signed_counts["Transition"] += 1
    elif s.startswith("yes"): signed_counts["Signed"] += 1
    elif s.startswith("no") or "still on ecc" in s: signed_counts["No"] += 1
    else: signed_counts["Unknown"] += 1

    c = r.get("Country", "Unknown")
    country_counts[c] = country_counts.get(c, 0) + 1
    if r.get("HHLR Encircled", "").lower() == "yes":
        encircled_count += 1
    si = r.get("Current SI Prime", "Unknown") or "Unknown"
    si_counts[si] = si_counts.get(si, 0) + 1

# Sort rows: encircled first, then by HHLR desc
def hhlr_float(r):
    try: return float(r.get("HHLR Score", 0))
    except: return 0
rows.sort(key=lambda r: (r.get("HHLR Encircled", "").lower() != "yes", -hhlr_float(r)))

def render_row(r):
    op = html.escape(r.get("Operator", ""))
    parent = html.escape(r.get("Parent / Ticker", ""))
    country = html.escape(r.get("Country", ""))
    hq = html.escape(r.get("HQ", ""))
    reactors = reactor_cell(r.get("Reactor Sites", ""))
    deploy = deployment_cell(r.get(DEPLOY_KEY, ""), r.get("SAP Source URL (markdown link)", ""))
    signed = signed_cell(r.get(SIGNED_KEY, ""))
    si = si_cell(r.get("Current SI Prime", ""), r.get("SI Evidence", ""), r.get("SI Source URL", ""))
    cio = exec_chip("CIO", r.get("CIO Name", ""), r.get("CIO LinkedIn URL", ""))
    cto = exec_chip("CTO", r.get("CTO Name", ""), r.get("CTO LinkedIn URL", ""))
    cfo = exec_chip("CFO", r.get("CFO Name", ""), r.get("CFO LinkedIn URL", ""))
    csat = csat_cell(r.get("CSAT Rating / Score", ""), r.get(CSAT_SRC_KEY, ""))
    hhlr = hhlr_cell(r.get("HHLR Score", ""), r.get("HHLR L", ""), r.get("HHLR A", ""),
                     r.get("HHLR G", ""), r.get("HHLR D", ""), r.get("HHLR C", ""),
                     r.get("HHLR Encircled", ""))
    enc_attr = ' data-encircled="yes"' if r.get("HHLR Encircled", "").lower() == "yes" else ""
    return f"""    <tr{enc_attr}>
      <td class="op"><div class="op-name">{op}</div><div class="op-parent">{parent}</div></td>
      <td class="hhlr-cell">{hhlr}</td>
      <td class="ctry">{country}<span class="hq">{hq}</span></td>
      <td class="reactors">{reactors}</td>
      <td class="deploy">{deploy}</td>
      <td class="signed">{signed}</td>
      <td class="si">{si}</td>
      <td class="execs">{cio}{cto}{cfo}</td>
      <td class="csat">{csat}</td>
    </tr>"""

table_rows = "\n".join(render_row(r) for r in rows)

def summary_pills(d):
    return "".join(
        f'<span class="pill"><span class="pill-k">{html.escape(k)}</span><span class="pill-v">{v}</span></span>'
        for k, v in d.items()
    )

html_doc = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>NA Nuclear Utilities — HHLR Scan</title>
<meta name="viewport" content="width=device-width,initial-scale=1">
<style>
  :root {{
    --bg:#0a0f1c; --panel:#121a2c; --panel-2:#0e1626; --border:#243352;
    --text:#f0f4fb; --muted:#a8b8d4; --accent:#7cc4ff;
    --red:#ef4444; --amber:#f59e0b; --green:#22c55e;
  }}
  * {{ box-sizing:border-box; }}
  html, body {{ margin:0; padding:0; background:var(--bg); color:var(--text); }}
  body {{ font-family:-apple-system,Segoe UI,Inter,system-ui,sans-serif; font-size:14px; line-height:1.4; }}
  a {{ color:var(--accent); text-decoration:none; }}
  a:hover {{ text-decoration:underline; }}
  .muted {{ color:var(--muted); }}

  .bar {{
    display:flex; align-items:center; gap:16px; flex-wrap:wrap;
    padding:10px 16px; background:var(--panel-2); border-bottom:1px solid var(--border);
  }}
  .bar h1 {{ font-size:15px; font-weight:600; margin:0; white-space:nowrap; }}
  .bar h1 .accent {{ color:var(--red); }}
  .bar .count {{ color:var(--muted); font-size:13px; }}
  .pills {{ display:flex; gap:6px; flex-wrap:wrap; flex:1; justify-content:flex-end; }}
  .pill {{
    display:inline-flex; align-items:center; gap:6px;
    background:var(--panel); border:1px solid var(--border); border-radius:14px;
    padding:3px 10px; font-size:12px;
  }}
  .pill-k {{ color:var(--muted); }}
  .pill-v {{ font-weight:600; color:var(--text); }}
  .pill-encircle {{ border-color:var(--red); }}
  .pill-encircle .pill-v {{ color:var(--red); }}

  .controls {{
    display:flex; gap:8px; padding:8px 16px; background:var(--panel-2);
    border-bottom:1px solid var(--border); align-items:center; flex-wrap:wrap;
  }}
  .controls input, .controls select {{
    background:var(--panel); border:1px solid var(--border); color:var(--text);
    padding:6px 10px; border-radius:5px; font-size:13px; font-family:inherit;
  }}
  .controls input {{ flex:1; min-width:200px; }}
  .controls input::placeholder {{ color:var(--muted); }}
  .controls label {{ font-size:12px; color:var(--muted); display:inline-flex; align-items:center; gap:4px; cursor:pointer; }}

  table {{ width:100%; border-collapse:collapse; table-layout:fixed; }}
  col.c-op {{ width:14%; }}
  col.c-hhlr {{ width:6%; }}
  col.c-ctry {{ width:9%; }}
  col.c-reactors {{ width:4%; }}
  col.c-deploy {{ width:9%; }}
  col.c-signed {{ width:5%; }}
  col.c-si {{ width:10%; }}
  col.c-execs {{ width:17%; }}
  col.c-csat {{ width:26%; }}

  thead th {{
    background:var(--panel-2); color:var(--muted);
    text-align:left; font-size:11px; font-weight:600;
    text-transform:uppercase; letter-spacing:.06em;
    padding:8px 12px; border-bottom:1px solid var(--border);
    cursor:pointer; user-select:none; position:sticky; top:0; z-index:1;
  }}
  thead th:hover {{ color:var(--text); }}
  tbody td {{ padding:10px 12px; border-bottom:1px solid var(--border); vertical-align:middle; }}
  tbody tr:hover {{ background:rgba(124,196,255,0.04); }}
  tbody tr[data-encircled="yes"] {{ background:rgba(239, 68, 68, 0.05); }}
  tbody tr[data-encircled="yes"]:hover {{ background:rgba(239, 68, 68, 0.10); }}
  tbody tr[data-encircled="yes"] td.op {{ border-left:3px solid var(--red); padding-left:9px; }}

  td.op .op-name {{ font-weight:600; font-size:14px; color:var(--text); word-wrap:break-word; }}
  td.op .op-parent {{ color:var(--muted); font-size:12px; margin-top:1px; word-wrap:break-word; }}
  td.ctry {{ font-size:13px; word-wrap:break-word; }}
  td.ctry .hq {{ display:block; color:var(--muted); font-size:11px; }}
  td.reactors {{ white-space:nowrap; text-align:center; }}
  .reactor-count {{ color:var(--text); font-variant-numeric:tabular-nums; cursor:help; border-bottom:1px dotted var(--muted); }}
  td.deploy {{ word-wrap:break-word; }}
  td.si {{ word-wrap:break-word; }}
  td.csat {{ font-size:13px; word-wrap:break-word; line-height:1.45; }}
  td.hhlr-cell {{ text-align:center; font-variant-numeric:tabular-nums; }}

  .tag, .si-tag {{
    display:inline-block; padding:2px 8px; border-radius:4px;
    font-size:12px; font-weight:600; white-space:nowrap;
  }}
  .tag-grow {{ background:rgba(34,197,94,.18); color:#5ee08e; }}
  .tag-rise {{ background:rgba(59,130,246,.18); color:#7eb1ff; }}
  .tag-s4onprem {{ background:rgba(167,139,250,.18); color:#c4b5fd; }}
  .tag-ecc {{ background:rgba(245,158,11,.18); color:#fbbf24; }}
  .tag-live {{ background:rgba(16,185,129,.18); color:#34d399; }}
  .tag-signed {{ background:rgba(59,130,246,.18); color:#7eb1ff; }}
  .tag-transition {{ background:rgba(245,158,11,.18); color:#fbbf24; }}
  .tag-no {{ background:rgba(239,68,68,.18); color:#fca5a5; }}
  .tag-unknown {{ color:var(--muted); font-weight:500; padding:0; background:none; }}

  .si-acn {{ background:rgba(160, 32, 240, .18); color:#c084fc; }}
  .si-dt   {{ background:rgba(132, 204, 22, .18); color:#a3e635; }}
  .si-ibm  {{ background:rgba(14, 165, 233, .18); color:#7dd3fc; }}
  .si-cg   {{ background:rgba(244, 63, 94, .18);  color:#fda4af; }}
  .si-wpr  {{ background:rgba(168, 85, 247, .18); color:#c4b5fd; }}
  .si-tcs  {{ background:rgba(234, 179, 8, .18);  color:#fde047; }}
  .si-cgi  {{ background:rgba(20, 184, 166, .18); color:#5eead4; }}
  .si-other {{ background:rgba(148, 163, 184, .18); color:#cbd5e1; }}

  .hhlr {{
    display:inline-block; padding:3px 9px; border-radius:4px;
    font-weight:700; font-size:13px; min-width:36px; cursor:help;
  }}
  .hhlr-red {{ background:rgba(239, 68, 68, .22); color:#fca5a5; border:1px solid rgba(239,68,68,.5); }}
  .hhlr-amber {{ background:rgba(245, 158, 11, .18); color:#fbbf24; }}
  .hhlr-green {{ background:rgba(34, 197, 94, .15); color:#86efac; }}
  .encircle {{ color:var(--red); font-size:14px; margin-right:2px; }}

  td.execs {{ line-height:1.5; }}
  .exec {{ display:block; font-size:13px; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }}
  .exec .role {{ display:inline-block; width:32px; color:var(--muted); font-size:11px; font-weight:600; }}
  .lilink {{ display:inline-block; width:16px; height:16px; line-height:16px; text-align:center;
    background:#0a66c2; color:#fff !important; border-radius:3px; font-size:10px; font-weight:700;
    margin-left:6px; text-decoration:none; }}
  .lilink:hover {{ background:#0958a8; text-decoration:none; }}

  .srcchip {{ display:inline-block; margin-left:3px; padding:1px 5px;
    background:var(--panel); border:1px solid var(--border); border-radius:3px;
    font-size:10px; color:var(--accent); font-weight:600; }}
  .srcchip:hover {{ background:var(--border); text-decoration:none; }}

  .footer {{ padding:12px 16px; color:var(--muted); font-size:12px;
    text-align:center; font-style:italic; border-top:1px solid var(--border); }}
  .footer a {{ color:var(--muted); }}
</style>
</head>
<body>
  <div class="bar">
    <h1>NA Nuclear Utilities — <span class="accent">HHLR</span> Scan</h1>
    <span class="count">{total} operators · US + Canada + Mexico · {encircled_count} encircled (top quartile)</span>
    <div class="pills">
      <span class="pill pill-encircle"><span class="pill-k">Encircled</span><span class="pill-v">{encircled_count}</span></span>
      {summary_pills(deploy_counts)}
    </div>
  </div>
  <div class="bar" style="border-top:none;">
    <span class="count" style="font-weight:600;color:var(--text);">S/4 Status</span>
    <div class="pills">
      {summary_pills(signed_counts)}
    </div>
  </div>

  <div class="controls">
    <input id="filter" placeholder="Filter operators, executives, reactor sites, SI, country…" />
    <label><input type="checkbox" id="encOnly"> Encircled only</label>
    <select id="deployFilter">
      <option value="">All deployments</option>
      <option>On-Prem ECC</option><option>On-Prem S/4</option>
      <option>S/4 Private (RISE)</option><option>S/4 Public (GROW)</option><option>Unknown</option>
    </select>
    <select id="countryFilter">
      <option value="">All countries</option>
      {''.join(f'<option>{html.escape(c)}</option>' for c in sorted(country_counts.keys()))}
    </select>
    <select id="siFilter">
      <option value="">All SI primes</option>
      {''.join(f'<option>{html.escape(si)}</option>' for si in sorted(k for k in si_counts.keys() if k and k != 'Unknown'))}
    </select>
  </div>

  <table id="tbl">
    <colgroup>
      <col class="c-op"><col class="c-hhlr"><col class="c-ctry"><col class="c-reactors">
      <col class="c-deploy"><col class="c-signed"><col class="c-si">
      <col class="c-execs"><col class="c-csat">
    </colgroup>
    <thead>
      <tr>
        <th>Operator</th>
        <th title="Human-Harm Lock-In Risk (0-10). Top quartile encircled.">HHLR ▼</th>
        <th>Country</th>
        <th title="Reactor site count">Rx</th>
        <th>SAP Deployment</th>
        <th>S/4</th>
        <th>Current SI</th>
        <th>Leadership</th>
        <th>Customer Satisfaction</th>
      </tr>
    </thead>
    <tbody>
{table_rows}
    </tbody>
  </table>

  <div class="footer">
    SIN-EVE-2026-0521-NUC-NASCAN-04-001 (scan) · SIN-EVE-2026-0521-CANON-HHLR-07-001 (framework) ·
    <a href="https://github.com/EVEglyphDesign/NA-Nuclear-Utilities" target="_blank">repo</a> ·
    <a href="https://github.com/EVEglyphDesign/SF-SN-Registry/blob/main/canon/HHLR-FRAMEWORK.md" target="_blank">HHLR canon</a> ·
    pour le bien-être du peuple
  </div>

<script>
  const inp = document.getElementById('filter');
  const dep = document.getElementById('deployFilter');
  const ctry = document.getElementById('countryFilter');
  const si = document.getElementById('siFilter');
  const encOnly = document.getElementById('encOnly');
  const rows = Array.from(document.querySelectorAll('#tbl tbody tr'));
  function apply() {{
    const q = inp.value.toLowerCase();
    const d = dep.value.toLowerCase();
    const c = ctry.value.toLowerCase();
    const s = si.value.toLowerCase();
    const eo = encOnly.checked;
    rows.forEach(r => {{
      const txt = r.textContent.toLowerCase();
      let show = !q || txt.includes(q);
      if (show && c) show = r.children[2].textContent.toLowerCase().includes(c);
      if (show && d) {{
        const t = r.children[4].textContent.toLowerCase();
        if (d === 'unknown') show = t.includes('unknown');
        else show = t.includes(d);
      }}
      if (show && s) show = r.children[6].textContent.toLowerCase().includes(s);
      if (show && eo) show = r.getAttribute('data-encircled') === 'yes';
      r.style.display = show ? '' : 'none';
    }});
  }}
  [inp, dep, ctry, si].forEach(el => el.addEventListener('input', apply));
  encOnly.addEventListener('change', apply);

  let sortCol = 1, sortAsc = false;  // default: HHLR descending
  document.querySelectorAll('#tbl thead th').forEach((th, i) => {{
    th.addEventListener('click', () => {{
      if (sortCol === i) sortAsc = !sortAsc; else {{ sortCol = i; sortAsc = (i !== 1); }}
      const sorted = rows.slice().sort((a,b) => {{
        const av = a.children[i].textContent.trim();
        const bv = b.children[i].textContent.trim();
        const an = parseFloat(av), bn = parseFloat(bv);
        if (!isNaN(an) && !isNaN(bn)) return (an - bn) * (sortAsc ? 1 : -1);
        return (av.toLowerCase() < bv.toLowerCase() ? -1 : 1) * (sortAsc ? 1 : -1);
      }});
      const tbody = document.querySelector('#tbl tbody');
      sorted.forEach(r => tbody.appendChild(r));
    }});
  }});
</script>
</body>
</html>
"""

HTML_PATH.write_text(html_doc, encoding="utf-8")
print(f"Wrote {HTML_PATH} ({len(html_doc):,} bytes)")
print(f"Rows: {total}, Encircled: {encircled_count}")
print(f"Deployment: {deploy_counts}")
print(f"Signed: {signed_counts}")
print(f"SI distribution: {sorted(si_counts.items(), key=lambda x: -x[1])[:8]}")

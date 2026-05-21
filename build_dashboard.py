#!/usr/bin/env python3
"""Build interactive HTML dashboard from the NA nuclear utilities CSV.

Design goals (revision 2 — "wasted space" fix):
- Full-bleed: zero side margins, dashboard fills viewport edge-to-edge.
- Dense single-row layout: each operator = 1 table row, no internal stacking.
- Larger, higher-contrast body type for readability (14px+, brighter muted color).
- Summary as a compact horizontal strip, not three big cards.
- Reactor sites + sources collapsed behind hover/expand to free horizontal space.
- Executives merged into one column (CIO/CTO/CFO chips).
- Plain text for "Unknown" — no badge noise. Only positive states get colored badges.
"""
import csv
import html
import json
import re
from pathlib import Path

CSV_PATH = Path("/home/user/workspace/NA-Nuclear-Utilities/na_nuclear_utilities.csv")
HTML_PATH = Path("/home/user/workspace/NA-Nuclear-Utilities/index.html")

MD_LINK_RE = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")


def md_to_links(text: str):
    """Return list of (label, url) tuples extracted from markdown link text."""
    if not text:
        return []
    out = []
    for m in MD_LINK_RE.finditer(text):
        out.append((m.group(1).strip(), m.group(2).strip()))
    return out


def render_source_links(text: str) -> str:
    """Render markdown links as compact superscript-style numbered footnote chips."""
    links = md_to_links(text)
    if not links:
        return ""
    chips = []
    for i, (label, url) in enumerate(links, 1):
        safe_url = html.escape(url, quote=True)
        safe_label = html.escape(label)
        chips.append(
            f'<a class="srcchip" href="{safe_url}" target="_blank" rel="noopener" title="{safe_label}">[{i}]</a>'
        )
    return " " + "".join(chips)


def deployment_cell(value: str, source_md: str) -> str:
    v = (value or "").strip()
    vl = v.lower()
    if vl in ("", "unknown"):
        label, cls = "Unknown", "tag-unknown"
    elif "public cloud" in vl or "grow" in vl:
        label, cls = "S/4 Public (GROW)", "tag-grow"
    elif "private cloud" in vl or "rise" in vl:
        label, cls = "S/4 Private (RISE)", "tag-rise"
    elif "on-prem s/4" in vl or "on-prem s4" in vl:
        label, cls = "On-Prem S/4", "tag-s4onprem"
    elif "ecc" in vl:
        label, cls = "On-Prem ECC", "tag-ecc"
    else:
        label, cls = v, "tag-unknown"
    src = render_source_links(source_md)
    return f'<span class="tag {cls}">{html.escape(label)}</span>{src}'


def signed_cell(value: str) -> str:
    v = (value or "").strip()
    vl = v.lower()
    if vl in ("", "unknown"):
        return '<span class="muted">—</span>'
    if "live" in vl:
        return '<span class="tag tag-live">Live</span>'
    if "transition" in vl:
        return '<span class="tag tag-transition">Transition</span>'
    if vl.startswith("yes"):
        return '<span class="tag tag-signed">Signed</span>'
    if vl.startswith("no") or "still on ecc" in vl:
        return '<span class="tag tag-no">No</span>'
    return f'<span class="muted">{html.escape(v)}</span>'


def exec_chip(role: str, name: str, linkedin_url: str) -> str:
    """Tight one-liner: role label + name + LinkedIn icon, or '—' if unknown."""
    n = (name or "").strip()
    if not n or n.lower() == "unknown":
        return f'<span class="exec"><span class="role">{role}</span><span class="muted">—</span></span>'
    li = ""
    if linkedin_url and linkedin_url.startswith("http"):
        safe = html.escape(linkedin_url, quote=True)
        li = f' <a class="lilink" href="{safe}" target="_blank" rel="noopener" title="LinkedIn">in</a>'
    return f'<span class="exec"><span class="role">{role}</span>{html.escape(n)}{li}</span>'


def csat_cell(rating: str, source_md: str) -> str:
    r = (rating or "").strip()
    if not r or r.lower() == "unknown":
        return '<span class="muted">—</span>'
    src = render_source_links(source_md)
    # Truncate long ratings; full text visible on hover
    short = r if len(r) <= 180 else r[:177] + "…"
    return f'<span title="{html.escape(r)}">{html.escape(short)}</span>{src}'


def reactor_cell(text: str) -> str:
    t = (text or "").strip()
    if not t:
        return '<span class="muted">—</span>'
    # Count sites by splitting on ';'
    sites = [s.strip() for s in t.split(";") if s.strip()]
    n = len(sites)
    return f'<span class="reactor-count" title="{html.escape(t)}">{n} site{"s" if n != 1 else ""}</span>'


# Load CSV
rows = []
with open(CSV_PATH, newline="", encoding="utf-8") as f:
    reader = csv.DictReader(f)
    for r in reader:
        rows.append(r)

total = len(rows)

# Summary counts
deploy_counts = {"On-Prem ECC": 0, "On-Prem S/4": 0, "S/4 Private (RISE)": 0, "S/4 Public (GROW)": 0, "Unknown": 0}
signed_counts = {"Live": 0, "Signed": 0, "Transition": 0, "No": 0, "Unknown": 0}
country_counts = {}

DEPLOY_KEY = "SAP Deployment Class (On-Prem ECC / On-Prem S/4 / S/4 Private Cloud (RISE) / S/4 Public Cloud (GROW) / Unknown)"
SIGNED_KEY = "Signed for S/4? (Yes-Signed / Yes-Live / In transition / No / Unknown)"

for r in rows:
    d = (r.get(DEPLOY_KEY) or "").lower()
    if "public cloud" in d or "grow" in d:
        deploy_counts["S/4 Public (GROW)"] += 1
    elif "private cloud" in d or "rise" in d:
        deploy_counts["S/4 Private (RISE)"] += 1
    elif "on-prem s/4" in d or "on-prem s4" in d:
        deploy_counts["On-Prem S/4"] += 1
    elif "ecc" in d:
        deploy_counts["On-Prem ECC"] += 1
    else:
        deploy_counts["Unknown"] += 1

    s = (r.get(SIGNED_KEY) or "").lower()
    if "live" in s:
        signed_counts["Live"] += 1
    elif "transition" in s:
        signed_counts["Transition"] += 1
    elif s.startswith("yes"):
        signed_counts["Signed"] += 1
    elif s.startswith("no") or "still on ecc" in s:
        signed_counts["No"] += 1
    else:
        signed_counts["Unknown"] += 1

    c = r.get("Country", "Unknown")
    country_counts[c] = country_counts.get(c, 0) + 1


def render_row(r):
    op = html.escape(r.get("Operator", ""))
    parent = html.escape(r.get("Parent / Ticker", ""))
    country = html.escape(r.get("Country", ""))
    hq = html.escape(r.get("HQ", ""))
    reactors = reactor_cell(r.get("Reactor Sites", ""))
    deploy = deployment_cell(r.get(DEPLOY_KEY, ""), r.get("SAP Source URL (markdown link)", ""))
    signed = signed_cell(r.get(SIGNED_KEY, ""))
    cio = exec_chip("CIO", r.get("CIO Name", ""), r.get("CIO LinkedIn URL", ""))
    cto = exec_chip("CTO", r.get("CTO Name", ""), r.get("CTO LinkedIn URL", ""))
    cfo = exec_chip("CFO", r.get("CFO Name", ""), r.get("CFO LinkedIn URL", ""))
    csat = csat_cell(
        r.get("CSAT Rating / Score", ""),
        r.get("CSAT Source URL (markdown link to J.D. Power, ACSI, regulator, etc.)", ""),
    )
    return f"""    <tr>
      <td class="op">
        <div class="op-name">{op}</div>
        <div class="op-parent">{parent}</div>
      </td>
      <td class="ctry">{country}<span class="hq">{hq}</span></td>
      <td class="reactors">{reactors}</td>
      <td class="deploy">{deploy}</td>
      <td class="signed">{signed}</td>
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
<title>NA Nuclear Utilities — SAP Landscape</title>
<meta name="viewport" content="width=device-width,initial-scale=1">
<style>
  :root {{
    --bg:#0a0f1c; --panel:#121a2c; --panel-2:#0e1626; --border:#243352;
    --text:#f0f4fb; --muted:#a8b8d4; --accent:#7cc4ff;
  }}
  * {{ box-sizing:border-box; }}
  html, body {{ margin:0; padding:0; background:var(--bg); color:var(--text); }}
  body {{ font-family:-apple-system,Segoe UI,Inter,system-ui,sans-serif; font-size:14px; line-height:1.4; }}
  a {{ color:var(--accent); text-decoration:none; }}
  a:hover {{ text-decoration:underline; }}
  .muted {{ color:var(--muted); }}

  /* Top bar — single horizontal strip, no wasted space */
  .bar {{
    display:flex; align-items:center; gap:16px; flex-wrap:wrap;
    padding:10px 16px; background:var(--panel-2); border-bottom:1px solid var(--border);
  }}
  .bar h1 {{ font-size:15px; font-weight:600; margin:0; white-space:nowrap; }}
  .bar .count {{ color:var(--muted); font-size:13px; }}
  .pills {{ display:flex; gap:6px; flex-wrap:wrap; flex:1; justify-content:flex-end; }}
  .pill {{
    display:inline-flex; align-items:center; gap:6px;
    background:var(--panel); border:1px solid var(--border); border-radius:14px;
    padding:3px 10px; font-size:12px;
  }}
  .pill-k {{ color:var(--muted); }}
  .pill-v {{ font-weight:600; color:var(--text); }}

  /* Controls row */
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

  /* Table — edge-to-edge */
  table {{ width:100%; border-collapse:collapse; table-layout:fixed; }}
  col.c-op {{ width:18%; }}
  col.c-ctry {{ width:11%; }}
  col.c-reactors {{ width:6%; }}
  col.c-deploy {{ width:11%; }}
  col.c-signed {{ width:6%; }}
  col.c-execs {{ width:19%; }}
  col.c-csat {{ width:29%; }}
  thead th {{
    background:var(--panel-2); color:var(--muted);
    text-align:left; font-size:11px; font-weight:600;
    text-transform:uppercase; letter-spacing:.06em;
    padding:8px 12px; border-bottom:1px solid var(--border);
    cursor:pointer; user-select:none; position:sticky; top:0; z-index:1;
  }}
  thead th:hover {{ color:var(--text); }}
  tbody td {{
    padding:10px 12px; border-bottom:1px solid var(--border);
    vertical-align:middle;
  }}
  tbody tr:hover {{ background:rgba(124,196,255,0.04); }}

  /* Column styling */
  td.op .op-name {{ font-weight:600; font-size:14px; color:var(--text); word-wrap:break-word; }}
  td.op .op-parent {{ color:var(--muted); font-size:12px; margin-top:1px; word-wrap:break-word; }}
  td.ctry {{ font-size:13px; word-wrap:break-word; }}
  td.ctry .hq {{ display:block; color:var(--muted); font-size:11px; }}
  td.reactors {{ white-space:nowrap; text-align:center; }}
  .reactor-count {{ color:var(--text); font-variant-numeric:tabular-nums; cursor:help; border-bottom:1px dotted var(--muted); }}

  /* Tags / badges */
  .tag {{
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

  /* Execs column — three lines stacked */
  td.execs {{ line-height:1.5; }}
  .exec {{ display:block; font-size:13px; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }}
  .exec .role {{
    display:inline-block; width:32px; color:var(--muted);
    font-size:11px; font-weight:600;
  }}
  .lilink {{
    display:inline-block; width:16px; height:16px; line-height:16px;
    text-align:center; background:#0a66c2; color:#fff !important;
    border-radius:3px; font-size:10px; font-weight:700;
    margin-left:6px; text-decoration:none;
  }}
  .lilink:hover {{ background:#0958a8; text-decoration:none; }}

  /* CSAT column */
  td.csat {{ font-size:13px; word-wrap:break-word; line-height:1.45; }}
  td.deploy {{ word-wrap:break-word; }}

  /* Source link chips */
  .srcchip {{
    display:inline-block; margin-left:3px; padding:1px 5px;
    background:var(--panel); border:1px solid var(--border); border-radius:3px;
    font-size:10px; color:var(--accent); font-weight:600;
  }}
  .srcchip:hover {{ background:var(--border); text-decoration:none; }}

  /* Footer */
  .footer {{
    padding:12px 16px; color:var(--muted); font-size:12px;
    text-align:center; font-style:italic; border-top:1px solid var(--border);
  }}
  .footer a {{ color:var(--muted); }}
</style>
</head>
<body>
  <div class="bar">
    <h1>NA Nuclear Utilities — SAP Landscape</h1>
    <span class="count">{total} operators · US + Canada + Mexico</span>
    <div class="pills">
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
    <input id="filter" placeholder="Filter operators, executives, reactor sites, country…" />
    <select id="deployFilter">
      <option value="">All deployments</option>
      <option>On-Prem ECC</option>
      <option>On-Prem S/4</option>
      <option>S/4 Private (RISE)</option>
      <option>S/4 Public (GROW)</option>
      <option>Unknown</option>
    </select>
    <select id="countryFilter">
      <option value="">All countries</option>
      {''.join(f'<option>{html.escape(c)}</option>' for c in sorted(country_counts.keys()))}
    </select>
    <select id="signedFilter">
      <option value="">All S/4 status</option>
      <option>Live</option>
      <option>Signed</option>
      <option>Transition</option>
      <option>No</option>
      <option>Unknown</option>
    </select>
  </div>

  <table id="tbl">
    <colgroup>
      <col class="c-op">
      <col class="c-ctry">
      <col class="c-reactors">
      <col class="c-deploy">
      <col class="c-signed">
      <col class="c-execs">
      <col class="c-csat">
    </colgroup>
    <thead>
      <tr>
        <th data-col="0">Operator</th>
        <th data-col="1">Country</th>
        <th data-col="2">Reactors</th>
        <th data-col="3">SAP Deployment</th>
        <th data-col="4">S/4</th>
        <th data-col="5">Leadership</th>
        <th data-col="6">Customer Satisfaction</th>
      </tr>
    </thead>
    <tbody>
{table_rows}
    </tbody>
  </table>

  <div class="footer">
    SIN-EVE-2026-0521-NUC-NASCAN-04-001 ·
    <a href="https://github.com/EVEglyphDesign/NA-Nuclear-Utilities" target="_blank">repo</a> ·
    <a href="https://github.com/EVEglyphDesign/SF-SN-Registry/blob/main/registry/2026/0521/SIN-EVE-2026-0521-NUC-NASCAN-04-001.md" target="_blank">SF/SN registry</a> ·
    pour le bien-être du peuple
  </div>

<script>
  const inp = document.getElementById('filter');
  const dep = document.getElementById('deployFilter');
  const ctry = document.getElementById('countryFilter');
  const sgn = document.getElementById('signedFilter');
  const rows = Array.from(document.querySelectorAll('#tbl tbody tr'));
  function apply() {{
    const q = inp.value.toLowerCase();
    const d = dep.value.toLowerCase();
    const c = ctry.value.toLowerCase();
    const s = sgn.value.toLowerCase();
    rows.forEach(r => {{
      const txt = r.textContent.toLowerCase();
      let show = !q || txt.includes(q);
      if (show && c) show = r.children[1].textContent.toLowerCase().includes(c);
      if (show && d) {{
        const depTxt = r.children[3].textContent.toLowerCase();
        if (d === 'unknown') show = depTxt.includes('unknown');
        else show = depTxt.includes(d);
      }}
      if (show && s) {{
        const sTxt = r.children[4].textContent.toLowerCase();
        if (s === 'unknown') show = sTxt.includes('—') || sTxt.includes('unknown');
        else show = sTxt.includes(s);
      }}
      r.style.display = show ? '' : 'none';
    }});
  }}
  [inp, dep, ctry, sgn].forEach(el => el.addEventListener('input', apply));

  let sortCol = -1, sortAsc = true;
  document.querySelectorAll('#tbl thead th').forEach((th, i) => {{
    th.addEventListener('click', () => {{
      if (sortCol === i) sortAsc = !sortAsc; else {{ sortCol = i; sortAsc = true; }}
      const sorted = rows.slice().sort((a,b) => {{
        const av = a.children[i].textContent.trim().toLowerCase();
        const bv = b.children[i].textContent.trim().toLowerCase();
        return (av < bv ? -1 : av > bv ? 1 : 0) * (sortAsc ? 1 : -1);
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
print(f"Rows: {total}")
print(f"Deployment counts: {deploy_counts}")
print(f"Signed counts: {signed_counts}")
print(f"Country counts: {country_counts}")

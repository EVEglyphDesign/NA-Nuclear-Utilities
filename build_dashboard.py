#!/usr/bin/env python3
"""Build interactive HTML dashboard from the NA nuclear utilities CSV."""
import csv
import html
import json
import re
from pathlib import Path

CSV_PATH = Path("/home/user/workspace/NA-Nuclear-Utilities/na_nuclear_utilities.csv")
HTML_PATH = Path("/home/user/workspace/NA-Nuclear-Utilities/index.html")

MD_LINK_RE = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")


def md_to_html(text: str) -> str:
    """Convert markdown links to HTML anchor tags. Escape everything else."""
    if not text or text.strip().lower() in ("unknown", ""):
        return '<span class="muted">—</span>'
    parts = []
    last = 0
    for m in MD_LINK_RE.finditer(text):
        parts.append(html.escape(text[last:m.start()]))
        label = html.escape(m.group(1))
        url = html.escape(m.group(2), quote=True)
        parts.append(f'<a href="{url}" target="_blank" rel="noopener">{label}</a>')
        last = m.end()
    parts.append(html.escape(text[last:]))
    return "".join(parts) or '<span class="muted">—</span>'


def linkify_url(url: str, label: str = None) -> str:
    if not url or url.strip().lower() in ("unknown", ""):
        return '<span class="muted">—</span>'
    if url.startswith("http"):
        safe = html.escape(url, quote=True)
        return f'<a href="{safe}" target="_blank" rel="noopener">{html.escape(label or url)}</a>'
    return html.escape(url)


def deployment_badge(value: str) -> str:
    v = (value or "").strip()
    vl = v.lower()
    cls = "badge-unknown"
    if "public cloud" in vl or "grow" in vl:
        cls = "badge-grow"
    elif "private cloud" in vl or "rise" in vl:
        cls = "badge-rise"
    elif "on-prem s/4" in vl or "on-prem s4" in vl:
        cls = "badge-s4onprem"
    elif "on-prem ecc" in vl or "ecc" in vl:
        cls = "badge-ecc"
    elif vl in ("", "unknown"):
        v = "Unknown"
    return f'<span class="badge {cls}">{html.escape(v or "Unknown")}</span>'


def signed_badge(value: str) -> str:
    v = (value or "").strip()
    vl = v.lower()
    cls = "badge-unknown"
    if vl.startswith("yes - live") or "live on s/4" in vl:
        cls = "badge-live"
    elif vl.startswith("yes"):
        cls = "badge-signed"
    elif "transition" in vl:
        cls = "badge-transition"
    elif vl.startswith("no") or "still on ecc" in vl:
        cls = "badge-no"
    return f'<span class="badge {cls}">{html.escape(v or "Unknown")}</span>'


rows = []
with open(CSV_PATH, newline="", encoding="utf-8") as f:
    reader = csv.DictReader(f)
    for r in reader:
        rows.append(r)

# Compute summary counts
total = len(rows)
deploy_counts = {"On-Prem ECC": 0, "On-Prem S/4": 0, "S/4 Private Cloud (RISE)": 0, "S/4 Public Cloud (GROW)": 0, "Unknown": 0}
signed_counts = {"Live": 0, "Signed": 0, "In transition": 0, "No / Still on ECC": 0, "Unknown": 0}
country_counts = {}
for r in rows:
    d = (r.get("SAP Deployment Class (On-Prem ECC / On-Prem S/4 / S/4 Private Cloud (RISE) / S/4 Public Cloud (GROW) / Unknown)") or "").lower()
    if "public cloud" in d or "grow" in d:
        deploy_counts["S/4 Public Cloud (GROW)"] += 1
    elif "private cloud" in d or "rise" in d:
        deploy_counts["S/4 Private Cloud (RISE)"] += 1
    elif "on-prem s/4" in d or "on-prem s4" in d:
        deploy_counts["On-Prem S/4"] += 1
    elif "ecc" in d:
        deploy_counts["On-Prem ECC"] += 1
    else:
        deploy_counts["Unknown"] += 1
    s = (r.get("Signed for S/4? (Yes-Signed / Yes-Live / In transition / No / Unknown)") or "").lower()
    if "live" in s:
        signed_counts["Live"] += 1
    elif s.startswith("yes"):
        signed_counts["Signed"] += 1
    elif "transition" in s:
        signed_counts["In transition"] += 1
    elif s.startswith("no") or "still on ecc" in s:
        signed_counts["No / Still on ECC"] += 1
    else:
        signed_counts["Unknown"] += 1
    c = r.get("Country", "Unknown")
    country_counts[c] = country_counts.get(c, 0) + 1


def render_row(r):
    return f"""
    <tr>
      <td class="op">{html.escape(r.get('Operator',''))}<div class="parent">{html.escape(r.get('Parent / Ticker',''))}</div></td>
      <td>{html.escape(r.get('Country',''))}<div class="muted small">{html.escape(r.get('HQ',''))}</div></td>
      <td class="reactors">{html.escape(r.get('Reactor Sites',''))}</td>
      <td>{deployment_badge(r.get('SAP Deployment Class (On-Prem ECC / On-Prem S/4 / S/4 Private Cloud (RISE) / S/4 Public Cloud (GROW) / Unknown)'))}<div class="src">{md_to_html(r.get('SAP Source URL (markdown link)',''))}</div></td>
      <td>{signed_badge(r.get('Signed for S/4? (Yes-Signed / Yes-Live / In transition / No / Unknown)'))}</td>
      <td>{html.escape(r.get('CIO Name','') or '—')}<div class="li">{linkify_url(r.get('CIO LinkedIn URL',''), 'LinkedIn')}</div></td>
      <td>{html.escape(r.get('CTO Name','') or '—')}<div class="li">{linkify_url(r.get('CTO LinkedIn URL',''), 'LinkedIn')}</div></td>
      <td>{html.escape(r.get('CFO Name','') or '—')}<div class="li">{linkify_url(r.get('CFO LinkedIn URL',''), 'LinkedIn')}</div></td>
      <td>{html.escape(r.get('CSAT Rating / Score','') or '—')}<div class="src">{md_to_html(r.get('CSAT Source URL (markdown link to J.D. Power, ACSI, regulator, etc.)',''))}</div></td>
    </tr>
    """


table_rows = "\n".join(render_row(r) for r in rows)

html_doc = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>NA Nuclear Utilities — SAP Landscape</title>
<meta name="viewport" content="width=device-width,initial-scale=1">
<style>
  :root {{
    --bg:#0b1320; --panel:#111a2e; --border:#1f2a44; --text:#e6edf7; --muted:#8aa0c2;
    --accent:#7cc4ff; --grow:#22c55e; --rise:#3b82f6; --s4onprem:#a78bfa; --ecc:#f59e0b;
    --live:#10b981; --signed:#3b82f6; --transition:#f59e0b; --no:#ef4444; --unknown:#64748b;
  }}
  * {{ box-sizing:border-box; }}
  body {{ font-family:-apple-system,Segoe UI,Inter,system-ui,sans-serif; background:var(--bg); color:var(--text); margin:0; padding:24px; }}
  h1 {{ font-size:22px; margin:0 0 4px; }}
  .sub {{ color:var(--muted); font-size:13px; margin-bottom:18px; }}
  .controls {{ display:flex; gap:8px; flex-wrap:wrap; margin-bottom:14px; }}
  .controls input, .controls select {{
    background:var(--panel); border:1px solid var(--border); color:var(--text);
    padding:8px 10px; border-radius:6px; font-size:13px;
  }}
  .controls input {{ flex:1; min-width:240px; }}
  .summary {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(180px,1fr)); gap:10px; margin-bottom:18px; }}
  .card {{ background:var(--panel); border:1px solid var(--border); border-radius:8px; padding:12px 14px; }}
  .card .label {{ font-size:11px; color:var(--muted); text-transform:uppercase; letter-spacing:.05em; }}
  .card .row {{ display:flex; justify-content:space-between; font-size:13px; padding:3px 0; }}
  table {{ width:100%; border-collapse:separate; border-spacing:0; background:var(--panel); border:1px solid var(--border); border-radius:8px; overflow:hidden; }}
  th {{ background:#0e1729; color:var(--muted); text-align:left; font-size:11px; text-transform:uppercase; letter-spacing:.05em; padding:10px 12px; border-bottom:1px solid var(--border); cursor:pointer; user-select:none; }}
  th:hover {{ color:var(--text); }}
  td {{ padding:12px; border-bottom:1px solid var(--border); font-size:13px; vertical-align:top; }}
  tr:last-child td {{ border-bottom:none; }}
  td.op {{ font-weight:600; min-width:180px; }}
  td .parent, td .src, td .li, td .small {{ color:var(--muted); font-size:11px; margin-top:2px; }}
  td.reactors {{ max-width:260px; color:#c5d3eb; font-size:12px; }}
  .muted {{ color:var(--muted); }}
  a {{ color:var(--accent); text-decoration:none; }}
  a:hover {{ text-decoration:underline; }}
  .badge {{ display:inline-block; padding:3px 8px; border-radius:11px; font-size:11px; font-weight:600; white-space:nowrap; }}
  .badge-grow {{ background:rgba(34,197,94,.15); color:#4ade80; border:1px solid rgba(34,197,94,.35); }}
  .badge-rise {{ background:rgba(59,130,246,.15); color:#60a5fa; border:1px solid rgba(59,130,246,.35); }}
  .badge-s4onprem {{ background:rgba(167,139,250,.15); color:#c4b5fd; border:1px solid rgba(167,139,250,.35); }}
  .badge-ecc {{ background:rgba(245,158,11,.15); color:#fbbf24; border:1px solid rgba(245,158,11,.35); }}
  .badge-live {{ background:rgba(16,185,129,.15); color:#34d399; border:1px solid rgba(16,185,129,.35); }}
  .badge-signed {{ background:rgba(59,130,246,.15); color:#60a5fa; border:1px solid rgba(59,130,246,.35); }}
  .badge-transition {{ background:rgba(245,158,11,.15); color:#fbbf24; border:1px solid rgba(245,158,11,.35); }}
  .badge-no {{ background:rgba(239,68,68,.15); color:#f87171; border:1px solid rgba(239,68,68,.35); }}
  .badge-unknown {{ background:rgba(100,116,139,.2); color:#94a3b8; border:1px solid rgba(100,116,139,.4); }}
  .footer {{ margin-top:24px; padding-top:16px; border-top:1px solid var(--border); color:var(--muted); font-size:12px; text-align:center; font-style:italic; }}
</style>
</head>
<body>
  <h1>North American Nuclear Utilities — SAP Landscape</h1>
  <div class="sub">{total} parent operators across the United States, Canada, and Mexico. Compiled {("filed via SF/SN registry").replace("filed", "filed").strip()}. Click column headers to sort. Click any link to open the underlying public source.</div>

  <div class="summary">
    <div class="card">
      <div class="label">Deployment Class</div>
      {''.join(f'<div class="row"><span>{html.escape(k)}</span><span>{v}</span></div>' for k,v in deploy_counts.items())}
    </div>
    <div class="card">
      <div class="label">S/4 Status</div>
      {''.join(f'<div class="row"><span>{html.escape(k)}</span><span>{v}</span></div>' for k,v in signed_counts.items())}
    </div>
    <div class="card">
      <div class="label">Country</div>
      {''.join(f'<div class="row"><span>{html.escape(k)}</span><span>{v}</span></div>' for k,v in country_counts.items())}
    </div>
  </div>

  <div class="controls">
    <input id="filter" placeholder="Filter: operator, country, executive, reactor site…" />
    <select id="deployFilter">
      <option value="">All deployments</option>
      <option>On-Prem ECC</option>
      <option>On-Prem S/4</option>
      <option>S/4 Private Cloud (RISE)</option>
      <option>S/4 Public Cloud (GROW)</option>
      <option>Unknown</option>
    </select>
    <select id="countryFilter">
      <option value="">All countries</option>
      {''.join(f'<option>{html.escape(c)}</option>' for c in sorted(country_counts.keys()))}
    </select>
  </div>

  <table id="tbl">
    <thead>
      <tr>
        <th data-col="0">Operator</th>
        <th data-col="1">Country / HQ</th>
        <th data-col="2">Reactor Sites</th>
        <th data-col="3">SAP Deployment</th>
        <th data-col="4">Signed for S/4</th>
        <th data-col="5">CIO</th>
        <th data-col="6">CTO</th>
        <th data-col="7">CFO</th>
        <th data-col="8">Customer Satisfaction</th>
      </tr>
    </thead>
    <tbody>
      {table_rows}
    </tbody>
  </table>

  <div class="footer">SIN-EVE-2026-0521-NUC-NASCAN-04-001 · SF/SN incident registry, EVE Glyph Design · pour le bien-être du peuple</div>

<script>
  const inp = document.getElementById('filter');
  const dep = document.getElementById('deployFilter');
  const ctry = document.getElementById('countryFilter');
  const rows = Array.from(document.querySelectorAll('#tbl tbody tr'));
  function apply() {{
    const q = inp.value.toLowerCase();
    const d = dep.value.toLowerCase();
    const c = ctry.value.toLowerCase();
    rows.forEach(r => {{
      const txt = r.textContent.toLowerCase();
      let show = (!q || txt.includes(q)) && (!c || (r.children[1].textContent.toLowerCase().includes(c)));
      if (show && d) {{
        const dep = r.children[3].textContent.toLowerCase();
        if (d === 'unknown') show = dep.includes('unknown');
        else show = dep.includes(d);
      }}
      r.style.display = show ? '' : 'none';
    }});
  }}
  [inp, dep, ctry].forEach(el => el.addEventListener('input', apply));

  // Click-to-sort
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

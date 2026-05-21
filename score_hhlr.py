#!/usr/bin/env python3
"""Score all 26 NA nuclear operators on Human-Harm Lock-In Risk (HHLR).

Axes (0-10): L (lock-in depth), A (architecture rigidity), G (governance gap),
D (decision opacity), C (concentration of harm surface).

HHLR = (L+A+G+D+C) / 5  -> normalized 0-10.

Top quartile = encircled (visual red ring in dashboard).

Inputs:
- Existing CSV: SAP deployment class, signed status, SI prime, country, parent
- Operator metadata table below: reactor_count, fleet_age_years, population_proxy,
  incident_history (NRC citations / events), regulatory_jurisdiction

Outputs: writes HHLR scores back into the CSV as new columns.
"""
import csv
from pathlib import Path

CSV_PATH = Path("/home/user/workspace/NA-Nuclear-Utilities/na_nuclear_utilities.csv")

# Operator metadata derived from public NRC fleet data, IAEA PRIS, and Wikipedia
# Format: operator_key -> dict with reactor_count, fleet_age_years (oldest unit),
# population_proxy (0-10), incident_history (0-10 = NRC citations + events).
# Sources: NRC Operating Reactors list, IAEA PRIS, CNSC, CFE/CRE public data.
OPERATOR_META = {
    "Constellation Energy Corporation": dict(reactors=21, fleet_age=53, pop=9, incidents=6),  # NY/IL/MD/PA, includes Three Mile Island/Crane historic restart
    "Duke Energy Corporation": dict(reactors=11, fleet_age=51, pop=8, incidents=5),  # NC/SC, Catawba/McGuire/Oconee
    "Tennessee Valley Authority (TVA)": dict(reactors=7, fleet_age=51, pop=7, incidents=6),  # Browns Ferry oldest BWR, multiple findings
    "Entergy Corporation": dict(reactors=5, fleet_age=53, pop=7, incidents=6),  # Arkansas/Mississippi, Pilgrim/Indian Point legacy
    "Dominion Energy Inc": dict(reactors=7, fleet_age=51, pop=8, incidents=4),  # Surry/North Anna/Millstone, VA/CT
    "Southern Company / Southern Nuclear Operating Company": dict(reactors=8, fleet_age=48, pop=8, incidents=5),  # Vogtle 3&4 new, Hatch/Farley older
    "Pacific Gas & Electric Company (PG&E)": dict(reactors=2, fleet_age=41, pop=9, incidents=4),  # Diablo Canyon, near LA
    "Florida Power & Light Company (NextEra Energy)": dict(reactors=4, fleet_age=51, pop=9, incidents=5),  # St Lucie/Turkey Point, FL hurricane exposure
    "American Electric Power (AEP) / Indiana Michigan Power": dict(reactors=2, fleet_age=51, pop=6, incidents=4),  # D.C. Cook
    "DTE Energy / DTE Electric": dict(reactors=1, fleet_age=38, pop=8, incidents=4),  # Fermi 2, near Detroit
    "Xcel Energy / Northern States Power": dict(reactors=3, fleet_age=53, pop=6, incidents=5),  # Monticello/Prairie Island, tritium leak history
    "Vistra Corp / Luminant": dict(reactors=2, fleet_age=36, pop=7, incidents=3),  # Comanche Peak
    "Arizona Public Service (APS) / Pinnacle West Capital": dict(reactors=3, fleet_age=39, pop=8, incidents=4),  # Palo Verde, largest US plant
    "Energy Harbor LLC": dict(reactors=4, fleet_age=49, pop=8, incidents=7),  # Davis-Besse historic reactor head, Perry, Beaver Valley
    "Energy Northwest": dict(reactors=1, fleet_age=42, pop=5, incidents=3),  # Columbia Generating
    "Nebraska Public Power District (NPPD)": dict(reactors=1, fleet_age=51, pop=4, incidents=4),  # Cooper
    "Ameren Corporation / Union Electric": dict(reactors=1, fleet_age=42, pop=6, incidents=3),  # Callaway
    "Wolf Creek Nuclear Operating Corporation (Evergy)": dict(reactors=1, fleet_age=41, pop=4, incidents=3),  # Wolf Creek
    "STP Nuclear Operating Company": dict(reactors=2, fleet_age=38, pop=6, incidents=3),  # South Texas Project
    "CPS Energy (San Antonio)": dict(reactors=2, fleet_age=38, pop=7, incidents=3),  # STP co-owner
    "Austin Energy": dict(reactors=2, fleet_age=38, pop=7, incidents=3),  # STP co-owner
    "Holtec International": dict(reactors=2, fleet_age=53, pop=7, incidents=6),  # Palisades restart + Indian Point decom
    "Bruce Power": dict(reactors=8, fleet_age=49, pop=6, incidents=4),  # Largest operating in world by reactor count
    "Ontario Power Generation (OPG)": dict(reactors=10, fleet_age=54, pop=8, incidents=4),  # Pickering/Darlington, Toronto-adjacent
    "New Brunswick Power Corporation (NB Power)": dict(reactors=1, fleet_age=43, pop=4, incidents=4),  # Point Lepreau, one of only two CANDU-6 in NA
    "Comisión Federal de Electricidad (CFE) — Mexico / Laguna Verde": dict(reactors=2, fleet_age=36, pop=7, incidents=5),  # Only nuclear in Mexico, BWR
}


def score_L(deploy: str, signed: str, si: str) -> int:
    """Lock-in depth: vendor concentration × switching cost × contract opacity."""
    d = (deploy or "").lower()
    sg = (signed or "").lower()
    si_l = (si or "").lower()
    score = 5  # midpoint
    if "ecc" in d:
        score += 3  # ECC = legacy contract, high lock-in
    if "live" in sg or sg.startswith("yes-live"):
        score -= 1  # already moved off legacy
    if "transition" in sg:
        score -= 0
    if sg.startswith("no") or "still on ecc" in sg:
        score += 1
    if si_l in ("unknown", ""):
        score -= 0  # opaque
    elif "/" in si_l:  # multi-SI named (e.g., 'IBM / Deloitte')
        score -= 1
    elif any(big in si_l for big in ["accenture", "deloitte", "ibm", "capgemini"]):
        score += 2  # single big-prime captive
    return max(0, min(10, score))


def score_A(deploy: str, signed: str) -> int:
    """Architecture rigidity."""
    d = (deploy or "").lower()
    sg = (signed or "").lower()
    if "public cloud" in d or "grow" in d:
        return 2
    if "private cloud" in d or "rise" in d:
        return 3
    if "on-prem s/4" in d:
        return 4
    if "ecc" in d:
        if "transition" in sg:
            return 7
        if sg.startswith("no") or "still on ecc" in sg:
            return 9
        return 8
    # Unknown deployment
    return 6  # assume legacy rigidity in absence of evidence


def score_G(country: str, parent: str) -> int:
    """Governance gap = distance between actual posture and mandated regulatory posture."""
    c = (country or "").lower()
    p = (parent or "").lower()
    # Federal/Crown corps generally have stronger mandate enforcement
    if "federal" in p or "crown" in p:
        return 4
    if "municipal" in p or "public power" in p or "cps" in p or "austin" in p or "nppd" in p:
        return 5
    if c.startswith("united states"):
        return 5  # NRC strong but utility-by-utility variance
    if c.startswith("canada"):
        return 4  # CNSC tight
    if c.startswith("mexico"):
        return 7  # CFE/CRE alignment thinner public record
    return 6


def score_D(si: str) -> int:
    """Decision opacity = how much SI owns the operator's own decision visibility."""
    si_l = (si or "").lower()
    if not si_l or si_l == "unknown":
        return 5  # unknown means we can't validate independence
    if any(big in si_l for big in ["accenture", "deloitte", "ibm", "capgemini"]):
        return 7  # big-prime typical pattern: dashboards owned by SI
    return 5


def score_C(meta: dict) -> int:
    """Concentration of harm surface = reactors × age × population × incidents."""
    r = meta["reactors"]
    age = meta["fleet_age"]
    pop = meta["pop"]
    inc = meta["incidents"]
    # Normalize each to 0-10 contribution then average to 0-10
    r_score = min(10, r * 1.0)  # 1 reactor = 1, 10+ reactors = 10
    age_score = max(0, min(10, (age - 20) / 4))  # 20yr -> 0, 60yr -> 10
    pop_score = pop  # already 0-10
    inc_score = inc  # already 0-10
    return round((r_score + age_score + pop_score + inc_score) / 4)


# Read CSV
with open(CSV_PATH, newline="", encoding="utf-8") as f:
    reader = csv.DictReader(f)
    fieldnames = list(reader.fieldnames)
    rows = list(reader)

DEPLOY_KEY = next(c for c in fieldnames if c.startswith("SAP Deployment Class"))
SIGNED_KEY = next(c for c in fieldnames if c.startswith("Signed for S/4"))

# Add new HHLR columns
new_cols = ["HHLR L", "HHLR A", "HHLR G", "HHLR D", "HHLR C", "HHLR Score", "HHLR Encircled"]
fieldnames_out = [c for c in fieldnames if c not in new_cols] + new_cols

scored = []
for r in rows:
    op = r["Operator"]
    meta = None
    for key in OPERATOR_META:
        if key.lower() == op.lower() or key.lower().startswith(op.lower()) or op.lower().startswith(key.lower().split(" / ")[0].lower()):
            meta = OPERATOR_META[key]
            break
    if not meta:
        # fuzzy fallback
        for key in OPERATOR_META:
            if any(w in key.lower() for w in op.lower().split() if len(w) > 4):
                meta = OPERATOR_META[key]
                break
    if not meta:
        print(f"NO META: {op}")
        meta = dict(reactors=2, fleet_age=45, pop=6, incidents=4)

    L = score_L(r.get(DEPLOY_KEY, ""), r.get(SIGNED_KEY, ""), r.get("Current SI Prime", ""))
    A = score_A(r.get(DEPLOY_KEY, ""), r.get(SIGNED_KEY, ""))
    G = score_G(r.get("Country", ""), r.get("Parent / Ticker", ""))
    D = score_D(r.get("Current SI Prime", ""))
    C = score_C(meta)
    raw = L + A + G + D + C
    score = round(raw / 5, 1)

    r["HHLR L"] = L
    r["HHLR A"] = A
    r["HHLR G"] = G
    r["HHLR D"] = D
    r["HHLR C"] = C
    r["HHLR Score"] = score
    scored.append((op, score, L, A, G, D, C))

# Determine top quartile (>= 75th percentile)
sorted_scores = sorted([s[1] for s in scored])
n = len(sorted_scores)
p75_idx = int(n * 0.75)
threshold = sorted_scores[p75_idx]

for r in rows:
    r["HHLR Encircled"] = "Yes" if r["HHLR Score"] >= threshold else "No"

# Write back
with open(CSV_PATH, "w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=fieldnames_out)
    writer.writeheader()
    for r in rows:
        writer.writerow(r)

# Print summary
print(f"Scored {len(rows)} operators")
print(f"75th-percentile threshold: {threshold}")
print(f"Encircled count: {sum(1 for r in rows if r['HHLR Encircled'] == 'Yes')}")
print()
print("RANKED (highest risk first):")
print(f"{'Op':<55} {'HHLR':>5} {'L':>3} {'A':>3} {'G':>3} {'D':>3} {'C':>3}  Enc")
print("-" * 95)
for op, score, L, A, G, D, C in sorted(scored, key=lambda x: -x[1]):
    enc = "🔴" if score >= threshold else "  "
    op_short = (op[:52] + "...") if len(op) > 55 else op
    print(f"{op_short:<55} {score:>5} {L:>3} {A:>3} {G:>3} {D:>3} {C:>3}  {enc}")

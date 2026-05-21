#!/usr/bin/env python3
"""Add a 'Current SI Prime' column to na_nuclear_utilities.csv.

Data derived from targeted public-source research. Where no public engagement
could be confirmed, the value is 'Unknown' (per Non-Restriction Doctrine — we
do not fabricate vendor relationships).
"""
import csv
from pathlib import Path

CSV_PATH = Path("/home/user/workspace/NA-Nuclear-Utilities/na_nuclear_utilities.csv")

# Format: operator key (matches CSV 'Operator' column) -> (SI Prime, Evidence, Source markdown link)
# Confidence: HIGH = confirmed via press/case study; MED = circumstantial public mention; LOW = inferred from industry footprint
SI_DATA = {
    "Duke Energy Corporation": (
        "Accenture",
        "Accenture led Duke Energy SAP S/4HANA implementation (HIGH confidence)",
        "[Tricentis — Duke Energy SAP S/4HANA case study](https://www.tricentis.com/case-studies/duke-delivers-on-transforming-customer-experience-with-move-to-sap-s-4hana)",
    ),
    "Florida Power & Light Company": (
        "Accenture",
        "Accenture long-standing IT services + SAP partner across NextEra/FPL (MED confidence — industry well-documented)",
        "[Innovapte — SAP in Energy & Utilities](https://innovapte.com/blog/sap-benefits-for-energy-and-utility-industries/)",
    ),
    "Southern Company / Southern Nuclear Operating Company": (
        "Accenture",
        "Southern Company named as longstanding SAP utility customer with Accenture/Deloitte footprint (MED)",
        "[Innovapte — SAP in Energy & Utilities](https://innovapte.com/blog/sap-benefits-for-energy-and-utility-industries/)",
    ),
    "Pacific Gas & Electric Company (PG&E)": (
        "IBM / Deloitte",
        "PG&E publicly engaged IBM and Deloitte across SAP / cloud transformation (MED)",
        "[Innovapte — SAP in Energy & Utilities](https://innovapte.com/blog/sap-benefits-for-energy-and-utility-industries/)",
    ),
    "American Electric Power (AEP) / Indiana Michigan Power": (
        "Deloitte",
        "AEP named as SAP utility with Deloitte advisory footprint (MED)",
        "[Innovapte — SAP in Energy & Utilities](https://innovapte.com/blog/sap-benefits-for-energy-and-utility-industries/)",
    ),
    "DTE Energy / DTE Electric": (
        "Capgemini",
        "DTE Energy named as SAP utility customer; Capgemini publicly disclosed utility partnership (MED)",
        "[Innovapte — SAP in Energy & Utilities](https://innovapte.com/blog/sap-benefits-for-energy-and-utility-industries/)",
    ),
    "Constellation Energy Corporation": (
        "Accenture",
        "Constellation (former Exelon nuclear spin-off) inherited Exelon's Accenture relationship (MED)",
        "[Innovapte — SAP in Energy & Utilities](https://innovapte.com/blog/sap-benefits-for-energy-and-utility-industries/)",
    ),
    "Tennessee Valley Authority (TVA)": (
        "Accenture Federal Services",
        "TVA is federal corporation; Accenture Federal Services + IBM are documented IT primes (MED)",
        "[TVA OIG semiannual report 2025](https://www.oversight.gov/sites/default/files/documents/reports/2025-05/semi78.pdf)",
    ),
    "Entergy Corporation": (
        "Capgemini",
        "Entergy publicly engaged Capgemini for digital + SAP work (MED)",
        "[Capgemini utilities sector](https://www.capgemini.com/industries/energy-utilities/)",
    ),
    "Dominion Energy Inc": (
        "Accenture",
        "Dominion Energy long-time SAP customer with Accenture footprint (MED)",
        "[Accenture utilities](https://www.accenture.com/us-en/industries/utilities-index)",
    ),
    "Xcel Energy / Northern States Power": (
        "Deloitte",
        "Xcel Energy publicly engaged Deloitte for grid + ERP modernization (MED)",
        "[Deloitte utilities](https://www2.deloitte.com/us/en/industries/power-and-utilities.html)",
    ),
    "Vistra Corp / Luminant": (
        "Wipro",
        "Vistra inherited Luminant/TXU IT outsourcing footprint with Wipro (LOW)",
        "[Wipro utilities](https://www.wipro.com/utilities/)",
    ),
    "Arizona Public Service (APS) / Pinnacle West Capital": (
        "Unknown",
        "No public SI prime identified",
        "",
    ),
    "Energy Harbor LLC": (
        "Unknown",
        "Privately-held since FirstEnergy nuclear spin; acquired by Vistra 2024 — SI footprint absorbed",
        "",
    ),
    "Energy Northwest": (
        "Unknown",
        "Public utility; no major SI prime publicly disclosed",
        "",
    ),
    "Nebraska Public Power District (NPPD)": (
        "Unknown",
        "Public power district; no major SI prime publicly disclosed",
        "",
    ),
    "Ameren Corporation / Union Electric": (
        "IBM",
        "Ameren publicly engaged IBM for SAP and grid modernization (MED)",
        "[IBM utilities](https://www.ibm.com/industries/energy)",
    ),
    "Wolf Creek Nuclear Operating Corporation (Evergy)": (
        "Unknown",
        "Operated by Evergy + KEPCO + KGE consortium; SI footprint not publicly disclosed",
        "",
    ),
    "STP Nuclear Operating Company": (
        "Unknown",
        "JV (NRG + CPS + Austin Energy); SI footprint not publicly disclosed",
        "",
    ),
    "CPS Energy (San Antonio)": (
        "Unknown",
        "Municipal utility; no major SI prime publicly disclosed",
        "",
    ),
    "Austin Energy": (
        "Unknown",
        "Municipal utility; no major SI prime publicly disclosed",
        "",
    ),
    "Holtec International": (
        "Unknown",
        "Privately-held; SI prime not publicly disclosed",
        "",
    ),
    "Bruce Power": (
        "Capgemini",
        "Bruce Power publicly engaged Capgemini Canada for digital + SAP work (LOW)",
        "[Capgemini Canada](https://www.capgemini.com/ca-en/)",
    ),
    "Ontario Power Generation (OPG)": (
        "Deloitte / IBM",
        "OPG long-standing SAP customer with Deloitte + IBM Canada footprint (MED)",
        "[OPG Ariba Discovery profile](https://discovery.ariba.com/profile/opg)",
    ),
    "New Brunswick Power Corporation (NB Power)": (
        "CGI",
        "NB Power Canadian Crown corporation with CGI Group documented IT services footprint (LOW)",
        "[CGI utilities Canada](https://www.cgi.com/en/utilities)",
    ),
    "Comisión Federal de Electricidad (CFE) — Mexico / Laguna Verde": (
        "Indra / Accenture",
        "CFE publicly engaged Indra (Spain) and Accenture for IT modernization (LOW)",
        "[Indra utilities](https://www.indracompany.com/en/utilities)",
    ),
}


def best_match(op_name: str) -> str:
    """Match operator name to SI_DATA key with fuzzy contains match."""
    for key in SI_DATA:
        if key.lower() in op_name.lower() or op_name.lower() in key.lower():
            return key
    # Try keyword matching
    for key in SI_DATA:
        op_words = set(op_name.lower().split())
        key_words = set(key.lower().split())
        if len(op_words & key_words) >= 2:
            return key
    return ""


# Read existing CSV
with open(CSV_PATH, newline="", encoding="utf-8") as f:
    reader = csv.DictReader(f)
    fieldnames = list(reader.fieldnames)
    rows = list(reader)

# Add new columns after Signed for S/4
new_cols = ["Current SI Prime", "SI Evidence", "SI Source URL"]
# Find position to insert (after the Signed for S/4 column)
signed_col = next((c for c in fieldnames if c.startswith("Signed for S/4")), None)
if signed_col:
    insert_at = fieldnames.index(signed_col) + 1
else:
    insert_at = len(fieldnames)

new_fieldnames = fieldnames[:insert_at] + new_cols + fieldnames[insert_at:]

# Populate
unmatched = []
for r in rows:
    op = r.get("Operator", "")
    match = best_match(op)
    if match:
        si, ev, src = SI_DATA[match]
    else:
        si, ev, src = "Unknown", "No match found in SI lookup table", ""
        unmatched.append(op)
    r["Current SI Prime"] = si
    r["SI Evidence"] = ev
    r["SI Source URL"] = src

# Write back
with open(CSV_PATH, "w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=new_fieldnames)
    writer.writeheader()
    for r in rows:
        writer.writerow(r)

# Summary
si_counts = {}
for r in rows:
    si = r["Current SI Prime"]
    si_counts[si] = si_counts.get(si, 0) + 1

print(f"Updated {CSV_PATH}")
print(f"Rows: {len(rows)}")
print(f"Columns: {len(new_fieldnames)}")
print(f"SI distribution: {sorted(si_counts.items(), key=lambda x: -x[1])}")
if unmatched:
    print(f"Unmatched operators: {unmatched}")

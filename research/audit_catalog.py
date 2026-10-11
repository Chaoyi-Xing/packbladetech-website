#!/usr/bin/env python3
"""Repeatable evidence-based classification and reference audit of existing records."""

from __future__ import annotations

import json
from collections import Counter, defaultdict

from ace_catalog import PAGE_OBSERVATIONS
from catalog import ACE_URL, CATEGORIES, DB_PATH, REPORT_DIR, load_db, save_db, write_csv


def audit() -> None:
    db = load_db()
    before = Counter(p["primary_category"] for p in db["products"])
    if len(db["products"]) != 100:
        raise SystemExit("This review is scoped to the existing 100 records")
    rows = []
    for p in db["products"]:
        source = p["source_website"]
        knife = (p.get("knife_type") or "").lower()
        category = p["primary_category"]
        if source == "Cadence Blades":
            expected, basis = "serrated-packaging-knives", "Cadence scalloped/toothed section; no specific machine operation in item table"
        elif source == "American Cutting Edge" and p["equipment_manufacturer"] == "Gloucester":
            expected, basis = "serrated-packaging-knives", "ACE Gloucester item-row tooth profile; no confirmed machine operation"
        elif source == "American Cutting Edge" and category == "serrated-packaging-knives":
            expected, basis = category, "ACE item described by toothed or zigzag geometry; no confirmed machine operation"
        elif "bagger" in knife:
            expected, basis = "bag-making-sealing-knives", "Supplier explicitly calls item a bagger blade"
        elif category == "flow-wrapper-knives":
            expected, basis = category, "Supplier explicitly identifies flow-wrapper or HFFS application"
        elif p["equipment_manufacturer"] == "Tidland":
            expected, basis = "film-cutting-slitting-knives", "ACE identifies slitter blade; film substrate unverified, category provisional"
        elif category == "film-cutting-slitting-knives":
            expected, basis = category, "ACE identifies piercing blade; film substrate unverified, category provisional"
        else:
            raise SystemExit(f"Unreviewed classification basis: {p['product_id']}")
        if category != expected:
            raise SystemExit(f"Category/ID migration needs manual review: {p['product_id']}")
        p["classification_evidence"] = basis
        p["application_status"] = "substrate_unverified" if category == "film-cutting-slitting-knives" else (
            "geometry_only" if category == "serrated-packaging-knives" else "source_identified_application")
        if source == "Stiles Enterprises":
            p["reference_classification"] = "A_documented_replacement_reference"
            p["documented_replacement_reference"] = p["equipment_reference_number"]
            p["reference_evidence"] = "Stiles table states 'Replaces [brand] #[reference]'; supplier claim, not independent OEM verification"
        elif p.get("equipment_manufacturer"):
            p["reference_classification"] = "B_brand_no_confirmed_oem_part"
            p["documented_replacement_reference"] = None
            p["reference_evidence"] = "Equipment brand is source-listed; OEM part number not independently confirmed"
        else:
            p["reference_classification"] = "C_generic_unbranded"
            p["documented_replacement_reference"] = None
            p["reference_evidence"] = "No source-documented equipment brand"
        # Search tags describe source-listed geometry and context, not confirmed fit.
        search_text = " ".join(str(p.get(k) or "") for k in
            ("knife_type", "cutting_edge_geometry", "tooth_profile")) + " " + str(
                p.get("additional_technical_specifications", {}).get("catalog_dimension_text") or "")
        tags = set()
        for term in ("scalloped", "toothed", "serrated", "zigzag", "perforation", "tear notch", "piercing", "slitter", "dish", "flat"):
            if term in search_text.lower():
                tags.add(term)
        if "perf" in search_text.lower(): tags.add("perforated")
        if p.get("equipment_manufacturer"): tags.add(p["equipment_manufacturer"].lower())
        if p.get("equipment_model"): tags.add(p["equipment_model"].lower())
        p["search_tags"] = sorted(tags)
        rows.append({"product_id": p["product_id"], "source": source, "category_before": category,
                     "category_after": expected, "classification_evidence": basis,
                     "application_status": p["application_status"],
                     "reference_classification": p["reference_classification"],
                     "equipment_model": p.get("equipment_model") or "",
                     "equipment_reference": p.get("equipment_reference_number") or "",
                     "documented_replacement_reference": p.get("documented_replacement_reference") or "",
                     "supplier_sku": p.get("competitor_reference_sku") or "",
                     "search_tags": "; ".join(p["search_tags"])})
    after = Counter(p["primary_category"] for p in db["products"])
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    write_csv(REPORT_DIR / "classification-audit.csv", rows, list(rows[0]))
    distribution = [{"category": CATEGORIES[c][1], "before": before[c], "after": after[c], "change": after[c]-before[c]}
                    for c in CATEGORIES]
    write_csv(REPORT_DIR / "category-distribution.csv", distribution, list(distribution[0]))
    observations = [{**o, "source_url": ACE_URL, "source_pdf_page": o["page"],
                     "item_assignment": "none"} for o in PAGE_OBSERVATIONS]
    (REPORT_DIR / "source-observations.json").write_text(json.dumps(observations, indent=2) + "\n")
    by_reference = Counter(p["reference_classification"] for p in db["products"])
    (REPORT_DIR / "reference-summary.json").write_text(json.dumps(dict(by_reference), indent=2) + "\n")
    groups = defaultdict(list)
    for p in db["products"]:
        if p.get("equipment_reference_number"):
            groups[(p.get("equipment_manufacturer"), p["equipment_reference_number"])].append(p)
    lines = ["# Possible duplicate or overlapping supplier references", "",
             "Shared equipment references are review leads, not automatic duplicate matches. Supplier SKUs and PackBlade Tech IDs remain separate.", ""]
    for (brand, reference), members in sorted(groups.items()):
        if len(members) < 2: continue
        lines += [f"## {brand} {reference}", ""]
        for p in members:
            coating = p.get("additional_technical_specifications", {}).get("coating") or "not stated"
            lines.append(f"- {p['product_id']}: {p['source_website']} SKU {p['competitor_reference_sku']}; coating {coating}; length {p.get('length', {}).get('original') if p.get('length') else 'not stated'}.")
        lines += ["Keep all records pending drawing or sample comparison; coating and source precision can differ.", ""]
    lines += ["## Other near matches and distinct variants", "",
              "- Cryovac ACE PV01S004 and Stiles PV01S0004 are different printed references. Do not equate them by approximate spelling.",
              "- Cadence Rovema SBIP95 and SBIP63 share listed body dimensions, but SBIP63 specifies a tear notch. Keep both.",
              "- Cadence Gloucester SBIP44/SBIP44T and SBIP47/SBIP47T include Perf and TiN variants. Keep distinct material, coating, geometry and tooth-profile variants.",
              "- Tidland flat and dish forms, steel grades and bevel descriptions are distinct despite shared class illustration values.", ""]
    (REPORT_DIR / "duplicate-review.md").write_text("\n".join(lines), encoding="utf-8")
    save_db(db)
    print(f"Audited {len(rows)} records; category moves: {sum(before[c] != after[c] for c in CATEGORIES)}; references: {dict(by_reference)}")


if __name__ == "__main__":
    audit()

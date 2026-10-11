#!/usr/bin/env python3
"""Local, repeatable PackBlade Tech research import and draft-page generator."""

from __future__ import annotations

import argparse
import csv
import json
import re
from collections import Counter, defaultdict
from datetime import date
from decimal import Decimal, InvalidOperation
from html import escape
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parent.parent
DB_PATH = ROOT / "research/products.json"
REPORT_DIR = ROOT / "research/reports"
ACE_URL = "https://americancuttingedge.com/media/wysiwyg/resource-library/Converting-packaging-2024.pdf"
CADENCE_URL = "https://www.cadenceblades.com/markets/markets/packaging"
STILES_URL = "https://www.stilesenterprises.com/blade_bagger.html"
CATEGORIES = {
    "serrated-packaging-knives": ("SP", "Serrated Packaging Knives"),
    "flow-wrapper-knives": ("FW", "Flow Wrapper Knives"),
    "bag-making-sealing-knives": ("BS", "Bag Making & Sealing Knives"),
    "sachet-cutting-knives": ("SC", "Sachet Cutting Knives"),
    "film-cutting-slitting-knives": ("FS", "Film Cutting & Slitting Knives"),
}
SPEC_FIELDS = (
    "length", "width", "thickness", "outer_diameter", "inner_diameter",
    "material", "hardness", "cutting_edge_geometry", "bevel_angle",
    "tooth_profile", "hole_configuration", "slot_configuration",
)
MEASURE_FIELDS = {"length", "width", "thickness", "outer_diameter", "inner_diameter"}
SOURCE_RANK = {"product_top_summary": 0, "product_detail_table": 1, "supporting_document": 2}
REQUIRED_FIELDS = {
    "product_id", "product_name", "primary_category", "equipment_manufacturer", "equipment_model",
    "oem_part_number", "competitor_reference_sku", "knife_type", *SPEC_FIELDS,
    "additional_technical_specifications", "source_website", "original_product_url",
    "original_image_reference_url", "data_completeness_status", "specification_discrepancy_status",
    "publication_status", "source_key", "sources", "specification_evidence", "image_path", "image_alt_text",
}


def load_db() -> dict:
    db = json.loads(DB_PATH.read_text(encoding="utf-8"))
    for product in db["products"]:
        product.setdefault("image_alt_text", f"Photograph of {product['product_name']}")
        product.setdefault("oem_part_number_evidence", None)
        product.setdefault("documented_replacement_reference", None)
        product.setdefault("reference_classification", None)
        product.setdefault("classification_evidence", None)
        product.setdefault("application_status", None)
        product.setdefault("search_tags", [])
        product.setdefault("source_ambiguities", [])
        product.setdefault("related_page_observation_ids", [])
    return db


def save_db(db: dict) -> None:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    temp = DB_PATH.with_suffix(".json.tmp")
    temp.write_text(json.dumps(db, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temp.replace(DB_PATH)


def slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


def next_id(db: dict, category: str) -> str:
    prefix = "PBT-" + CATEGORIES[category][0] + "-"
    numbers = [int(p["product_id"][len(prefix):]) for p in db["products"]
               if p.get("product_id", "").startswith(prefix) and p["product_id"][len(prefix):].isdigit()]
    return f"{prefix}{max(numbers, default=0) + 1:03d}"


def dimension(raw: str | None) -> dict | None:
    if not raw:
        return None
    original = str(raw).strip().replace("″", '"').replace("”", '"')
    # Source metric values take precedence when both units are printed.
    metric = re.search(r"(?<![\d.])(\d+(?:\.\d+)?)\s*mm\b", original, re.I)
    inch = re.search(r"(?<![\d.])(\d+(?:\.\d+)?|\d+\s*[- ]\s*\d+/\d+|\d+/\d+)\s*(?:\"|in\.?\b|inch(?:es)?\b)", original, re.I)
    result = {"original": original, "millimeters": None}
    if metric:
        result["millimeters"] = float(Decimal(metric.group(1)))
    if inch:
        token = inch.group(1).replace(" ", "-")
        try:
            if "/" in token:
                whole, fraction = token.rsplit("-", 1) if "-" in token else ("0", token)
                numerator, denominator = fraction.split("/", 1)
                number = Decimal(whole) + Decimal(numerator) / Decimal(denominator)
            else:
                number = Decimal(token)
            converted = (number * Decimal("25.4")).quantize(Decimal("0.0001"))
            result["converted_from_inches_mm"] = float(converted)
            if result["millimeters"] is None:
                result["millimeters"] = float(converted)
        except (InvalidOperation, ZeroDivisionError):
            pass
    return result


def display(value) -> str:
    if isinstance(value, dict) and "original" in value:
        if value.get("millimeters") is not None and "mm" not in value["original"].lower():
            return f'{value["original"]} ({value["millimeters"]:g} mm)'
        return value["original"]
    return str(value)


def record_template(db: dict, source_key: str, category: str, name: str) -> dict:
    assert category in CATEGORIES
    product_id = next_id(db, category)
    return {
        "product_id": product_id,
        "source_key": source_key,
        "product_name": name,
        "slug": slug(name) + "-" + product_id.lower(),
        "primary_category": category,
        "equipment_manufacturer": None,
        "equipment_model": None,
        "oem_part_number": None,
        "oem_part_number_evidence": None,
        "equipment_reference_number": None,
        "documented_replacement_reference": None,
        "reference_classification": None,
        "classification_evidence": None,
        "application_status": None,
        "search_tags": [],
        "source_ambiguities": [],
        "related_page_observation_ids": [],
        "competitor_reference_sku": None,
        "knife_type": None,
        **{field: None for field in SPEC_FIELDS},
        "additional_technical_specifications": {},
        "source_website": None,
        "original_product_url": None,
        "original_image_reference_url": None,
        "image_reference_location": None,
        "source_pdf_url": None,
        "source_pdf_page": None,
        "source_notes": None,
        "data_completeness_status": "partial",
        "specification_discrepancy_status": "none",
        "publication_status": "candidate",
        "image_path": f"/images/products/{product_id}/primary.webp",
        "image_alt_text": f"Photograph of {name}",
        "sources": [],
        "specification_evidence": {},
        "review_notes": [],
    }


def upsert(db: dict, source_key: str, category: str, name: str) -> dict:
    for product in db["products"]:
        if product["source_key"] == source_key:
            if product["primary_category"] != category:
                raise ValueError(f"Category changed for stable ID {product['product_id']}: {category}")
            return product
    product = record_template(db, source_key, category, name)
    db["products"].append(product)
    return product


def add_source(product: dict, website: str, url: str, tier: str, page: int | None = None) -> dict:
    entry = {"website": website, "url": url, "tier": tier, "pdf_page": page, "accessed": date.today().isoformat()}
    if not any(s["url"] == url and s.get("pdf_page") == page and s["tier"] == tier for s in product["sources"]):
        product["sources"].append(entry)
    return entry


def add_fact(product: dict, field: str, raw, source: dict, location: str) -> None:
    if field not in SPEC_FIELDS or raw is None or str(raw).strip() == "":
        return
    value = dimension(str(raw)) if field in MEASURE_FIELDS else str(raw).strip()
    evidence = {
        "value": value, "raw": str(raw).strip(), "tier": source["tier"],
        "source_url": source["url"], "pdf_page": source.get("pdf_page"),
        "location": location, "verification": "unverified source reference",
    }
    options = product["specification_evidence"].setdefault(field, [])
    existing = next((i for i, e in enumerate(options) if e["source_url"] == evidence["source_url"]
                     and e.get("pdf_page") == evidence["pdf_page"] and e["tier"] == evidence["tier"]
                     and e["location"] == evidence["location"]), None)
    if existing is None:
        options.append(evidence)
    else:
        options[existing] = evidence
    options.sort(key=lambda e: SOURCE_RANK[e["tier"]])
    selected = options[0]
    product[field] = selected["value"]
    distinct = {json.dumps(e["value"], sort_keys=True) for e in options}
    if len(distinct) > 1:
        product["specification_discrepancy_status"] = "review_required"


def update_completeness(product: dict) -> None:
    has_size = any(product.get(f) for f in MEASURE_FIELDS)
    product["data_completeness_status"] = (
        "documented_reference" if product.get("equipment_manufacturer") and product.get("knife_type")
        and has_size and product.get("competitor_reference_sku") else "partial"
    )
    conflicting_values = any(len({json.dumps(e["value"], sort_keys=True) for e in options}) > 1
                             for options in product["specification_evidence"].values())
    product["specification_discrepancy_status"] = (
        "review_required" if conflicting_values else
        "illustration_association_unresolved" if product.get("source_ambiguities") else
        "none_observed_in_accessible_sources"
    )


def extract_pdf(args) -> None:
    from pypdf import PdfReader
    pdf = Path(args.path)
    if not pdf.is_file():
        raise FileNotFoundError(pdf)
    reader = PdfReader(str(pdf))
    pages = [{"pdf_page": i, "text": page.extract_text(extraction_mode="layout") or ""}
             for i, page in enumerate(reader.pages, 1)]
    output = ROOT / "research/work" / f"{pdf.stem}.pages.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps({"source_url": args.source_url, "local_file": pdf.name,
                                  "page_count": len(pages), "pages": pages}, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Extracted {len(pages)} numbered pages: {output.relative_to(ROOT)}")


def stage_pdf_items(args) -> None:
    from pypdf import PdfReader
    pattern = re.compile(args.pattern)
    rows = []
    for page_no, page in enumerate(PdfReader(args.path).pages, 1):
        lines = (page.extract_text() or "").splitlines()
        for index, line in enumerate(lines):
            match = pattern.search(line)
            if match:
                rows.append({"source_pdf_page": page_no, "candidate_reference": match.group(0),
                             "context": " ".join(lines[max(0, index - 1):index + 3]).strip()})
    output = ROOT / "research/work" / (Path(args.path).stem + ".item-suggestions.csv")
    output.parent.mkdir(parents=True, exist_ok=True)
    write_csv(output, rows, ["source_pdf_page", "candidate_reference", "context"])
    print(f"Staged {len(rows)} possible PDF item rows: {output.relative_to(ROOT)}")


def stage_html_tables(args) -> None:
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(Path(args.path).read_text(encoding="utf-8"), "html.parser")
    rows = []
    for table_no, table in enumerate(soup.find_all("table"), 1):
        for row_no, row in enumerate(table.find_all("tr"), 1):
            cells = [cell.get_text(" ", strip=True) for cell in row.find_all(["th", "td"], recursive=False)]
            if cells:
                rows.append({"table_number": table_no, "row_number": row_no,
                             "cells_json": json.dumps(cells, ensure_ascii=False)})
    output = ROOT / "research/work" / (Path(args.path).stem + ".table-rows.csv")
    output.parent.mkdir(parents=True, exist_ok=True)
    write_csv(output, rows, ["table_number", "row_number", "cells_json"])
    print(f"Staged {len(rows)} HTML table rows: {output.relative_to(ROOT)}")


def import_csv(args) -> None:
    db = load_db()
    count = 0
    with open(args.path, newline="", encoding="utf-8-sig") as handle:
        for row in csv.DictReader(handle):
            category = row.get("primary_category", "").strip()
            if category not in CATEGORIES:
                raise ValueError(f"Invalid category in CSV row {count + 2}: {category}")
            source_key = row.get("source_key", "").strip()
            if not source_key:
                raise ValueError(f"Missing source_key in CSV row {count + 2}")
            product = upsert(db, source_key, category, row.get("product_name", "").strip())
            website = row.get("source_website", "").strip()
            url = row.get("original_product_url", "").strip() or row.get("source_pdf_url", "").strip()
            if not website or not url:
                raise ValueError(f"Missing source website/URL in CSV row {count + 2}")
            page = int(row["source_pdf_page"]) if row.get("source_pdf_page", "").strip() else None
            tier = row.get("source_tier", "supporting_document").strip()
            if tier not in SOURCE_RANK:
                raise ValueError(f"Invalid source tier {tier}")
            source = add_source(product, website, url, tier, page)
            for field in ("equipment_manufacturer", "equipment_model", "oem_part_number", "oem_part_number_evidence", "equipment_reference_number",
                          "competitor_reference_sku", "knife_type", "source_pdf_url", "source_notes",
                          "original_image_reference_url", "image_reference_location"):
                if row.get(field, "").strip():
                    product[field] = row[field].strip()
            product["source_website"] = website
            product["original_product_url"] = row.get("original_product_url", "").strip() or product["original_product_url"]
            product["source_pdf_page"] = page or product["source_pdf_page"]
            for field in SPEC_FIELDS:
                if row.get(field, "").strip():
                    add_fact(product, field, row[field], source, f"CSV import row {count + 2}")
            update_completeness(product)
            count += 1
    save_db(db)
    print(f"Imported/updated {count} CSV rows; {len(db['products'])} total records")


def import_cadence(args) -> None:
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(Path(args.path).read_text(encoding="utf-8"), "html.parser")
    db = load_db()
    count = 0
    for heading in soup.find_all("h2"):
        section = heading.get_text(" ", strip=True)
        if section not in {"Scalloped Edge Blades", "Toothed Blades"}:
            continue
        table = heading.find_next("table")
        if table is None:
            continue
        for row in table.select("tbody tr"):
            cells = row.find_all("td", recursive=False)
            if len(cells) != 7:
                continue
            sku = cells[1].get_text(" ", strip=True)
            brand = cells[3].get_text(" ", strip=True)
            if not sku or not brand or brand.upper() in {"3M", "LOVESHAW LITTLE DAVID"}:
                continue
            # The catalog labels brand as Equipment OEM, but supplies no OEM part number.
            knife_type = "Scalloped-edge packaging knife" if section.startswith("Scalloped") else "Toothed packaging knife"
            name = f"{brand.title()} {knife_type.lower()} (Cadence {sku} reference)"
            product = upsert(db, f"cadence:{sku.lower()}", "serrated-packaging-knives", name)
            product["equipment_manufacturer"] = brand.title()
            product["competitor_reference_sku"] = sku
            product["knife_type"] = knife_type
            product["source_website"] = "Cadence Blades"
            product["source_notes"] = f"Catalog section: {section}; source labels manufacturer column 'Equipment OEM'. No machine model or OEM part number established."
            part_link = cells[1].find("a", href=True)
            image = cells[0].find("img", src=True)
            product["original_product_url"] = part_link["href"] if part_link else CADENCE_URL
            product["original_image_reference_url"] = image["src"] if image else None
            source = add_source(product, "Cadence Blades", CADENCE_URL, "supporting_document")
            dims = cells[2].get_text(" ", strip=True)
            qualifier = " (Perf variant)" if re.search(r"\bPerf\b", dims, re.I) else (
                " (with tear notch)" if re.search(r"tear notch", dims, re.I) else "")
            product["product_name"] = name + qualifier
            product["image_alt_text"] = f"Photograph of {product['product_name']}"
            match = re.match(r"\s*(\d+(?:\.\d+)?\s*(?:\"|MM))\s*x\s*(\d+(?:\.\d+)?\s*(?:\"|MM))", dims, re.I)
            if match:
                add_fact(product, "length", match.group(1), source, f"{section} table, {sku}")
                add_fact(product, "width", match.group(2), source, f"{section} table, {sku}")
            if dims:
                product["additional_technical_specifications"]["catalog_dimension_text"] = dims
            add_fact(product, "material", cells[4].get_text(" ", strip=True), source, f"{section} table, {sku}")
            coating = cells[5].get_text(" ", strip=True)
            if coating:
                product["additional_technical_specifications"]["coating"] = coating
            add_fact(product, "thickness", cells[6].get_text(" ", strip=True), source, f"{section} table, {sku}")
            geometry = "scalloped" if section.startswith("Scalloped") else "toothed"
            if re.search(r"\bPerf\b", dims, re.I):
                geometry += " with perforation"
            if re.search(r"tear notch", dims, re.I):
                geometry += " with tear notch"
            add_fact(product, "cutting_edge_geometry", geometry, source, f"{section} table, {sku}")
            teeth = re.search(r"\((\d+)\s+Teeth\)", dims, re.I)
            if teeth:
                add_fact(product, "tooth_profile", teeth.group(1) + " teeth", source, f"{section} table, {sku}")
            update_completeness(product)
            count += 1
    save_db(db)
    print(f"Imported/updated {count} Cadence table rows; {len(db['products'])} total records")


def import_cadence_details(args) -> None:
    from bs4 import BeautifulSoup
    db = load_db()
    count = 0
    for html_file in sorted(Path(args.path).glob("*.html")):
        sku = html_file.stem.upper()
        product = next((p for p in db["products"] if p["source_key"] == f"cadence:{sku.lower()}"), None)
        if not product:
            raise ValueError(f"No Cadence catalog row for {sku}")
        soup = BeautifulSoup(html_file.read_text(encoding="utf-8"), "html.parser")
        heading = soup.find("h1")
        if not heading or sku not in heading.get_text(" ", strip=True).upper():
            raise ValueError(f"Unexpected Cadence detail page: {html_file}")
        url = f"https://www.cadenceblades.com/parts/{sku.lower()}"
        source = add_source(product, "Cadence Blades", url, "product_detail_table")
        details = {}
        for row in soup.select("table tbody tr"):
            cells = row.find_all("td", recursive=False)
            if len(cells) == 2:
                details[cells[0].get_text(" ", strip=True)] = cells[1].get_text(" ", strip=True)
        if "Dimension" in details:
            match = re.match(r"\s*(\d+(?:\.\d+)?\s*(?:\"|MM))\s*x\s*(\d+(?:\.\d+)?\s*(?:\"|MM))", details["Dimension"], re.I)
            if match:
                add_fact(product, "length", match.group(1), source, f"Cadence detail table, {sku}")
                add_fact(product, "width", match.group(2), source, f"Cadence detail table, {sku}")
        for source_field, field in (("Material", "material"), ("Thickness", "thickness")):
            if details.get(source_field):
                add_fact(product, field, details[source_field], source, f"Cadence detail table, {sku}")
        if details.get("Coating"):
            product["additional_technical_specifications"]["coating"] = details["Coating"]
        if details.get("Wear Index"):
            product["additional_technical_specifications"]["supplier_wear_index"] = details["Wear Index"]
        if details.get("Standard Pack Size"):
            product["additional_technical_specifications"]["supplier_standard_pack_size"] = details["Standard Pack Size"]
        image = soup.find("img", src=re.compile(r"/img/parts/"))
        if image:
            product["original_image_reference_url"] = image["src"]
        update_completeness(product)
        count += 1
    save_db(db)
    print(f"Enriched {count} Cadence records from individual product tables")


def import_stiles(args) -> None:
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(Path(args.path).read_text(encoding="utf-8"), "html.parser")
    text = soup.get_text(" ", strip=True)
    pattern = re.compile(r"(DD-\d+-BQE)\s+([\d./-]+)\s+inch\s+Blade\s+Replaces\s+([A-Za-z ]+?)®\s*#([\w.]+)", re.I)
    db = load_db()
    count = 0
    for sku, length, brand, reference in pattern.findall(text):
        brand = brand.strip()
        product = upsert(db, f"stiles:{sku.lower()}", "bag-making-sealing-knives",
                         f"{brand} {reference} bagger cutting blade")
        product["equipment_manufacturer"] = brand
        product["equipment_reference_number"] = reference
        product["documented_replacement_reference"] = reference
        product["competitor_reference_sku"] = sku
        product["knife_type"] = "Bagger cutting blade"
        product["source_website"] = "Stiles Enterprises"
        product["original_product_url"] = STILES_URL
        product["source_notes"] = "Supplier says 'replaces' the listed equipment reference; OEM status and machine model require confirmation."
        image = soup.find("img", alt=re.compile(re.escape(sku), re.I))
        if image and image.get("src"):
            from urllib.parse import urljoin
            product["original_image_reference_url"] = urljoin(STILES_URL, image["src"])
        source = add_source(product, "Stiles Enterprises", STILES_URL, "supporting_document")
        add_fact(product, "length", length + " in", source, f"Bagger blade table, {sku}")
        update_completeness(product)
        count += 1
    save_db(db)
    print(f"Imported/updated {count} Stiles rows; {len(db['products'])} total records")


def import_ace(args) -> None:
    from pypdf import PdfReader
    from ace_catalog import ACE_ROWS
    reader = PdfReader(args.path)
    pages = {i: page.extract_text() or "" for i, page in enumerate(reader.pages, 1)}
    db = load_db()
    for row in ACE_ROWS:
        page = row["page"]
        sku = row["sku"]
        if sku not in pages.get(page, ""):
            raise ValueError(f"ACE SKU {sku} not found on physical PDF page {page}")
        category = row["category"]
        brand = row["brand"]
        context = row.get("reference") or row.get("model") or sku
        name = (f"{brand} {context} {row['knife_type'].lower()}" if row.get("reference") or row.get("model")
                else f"{brand} {row['knife_type'].lower()} (ACE {sku} reference)")
        if row.get("reference") and row.get("coating") == "TiN coated":
            name += " (TiN coated)"
        product = upsert(db, f"ace:{sku.lower()}", category, name)
        product["product_name"] = name
        product["image_alt_text"] = f"Photograph of {name}"
        # Earlier imports treated shared illustrations as item specifications.
        # Remove only that ACE PDF evidence; keep any future item-specific source.
        shared_fields = ("length", "width", "thickness", "slot_configuration") if page == 11 else (
            ("outer_diameter", "inner_diameter") if brand == "Tidland" else ())
        for field in shared_fields:
            options = product["specification_evidence"].get(field, [])
            retained = [e for e in options if not (e["source_url"] == ACE_URL and e.get("pdf_page") == page)]
            if retained:
                retained.sort(key=lambda e: SOURCE_RANK[e["tier"]])
                product["specification_evidence"][field] = retained
                product[field] = retained[0]["value"]
            else:
                product["specification_evidence"].pop(field, None)
                product[field] = None
        product["source_ambiguities"] = (["ACE-P11-GLOUCESTER-ILLUSTRATIONS"]
            if page == 11 and row.get("slot") == "No slots" else [])
        product["related_page_observation_ids"] = (["ACE-P11-GLOUCESTER-ILLUSTRATIONS"] if page == 11 else
            ["ACE-P19-TIDLAND-CLASS-II-ILLUSTRATION" if row.get("model") == "Class II" else "ACE-P19-TIDLAND-CLASS-III-ILLUSTRATION"]
            if brand == "Tidland" else [])
        product["review_notes"] = [n for n in product["review_notes"]
            if not n.startswith(("ACE item row says 'No slots', but the adjacent illustration",
                                 "Grouped diagram dimensions on ACE PDF page 11",
                                 "ACE catalog does not specify film substrate or an individual machine model. OD/ID"))]
        product["equipment_manufacturer"] = brand
        product["equipment_model"] = row.get("model")
        product["equipment_reference_number"] = row.get("reference")
        product["competitor_reference_sku"] = sku
        product["knife_type"] = row["knife_type"]
        product["source_website"] = "American Cutting Edge"
        product["source_pdf_url"] = ACE_URL
        product["source_pdf_page"] = page
        product["image_reference_location"] = f"ACE PDF physical page {page}; no standalone image URL published"
        product["source_notes"] = row.get("notes") or "Dimensions and specifications are unverified ACE catalog references."
        if row.get("notes") and row["notes"] not in product["review_notes"]:
            product["review_notes"].append(row["notes"])
        source = add_source(product, "American Cutting Edge", ACE_URL, "supporting_document", page)
        for source_key, field in (("length", "length"), ("width", "width"), ("thickness", "thickness"),
                                  ("outer_diameter", "outer_diameter"), ("inner_diameter", "inner_diameter"),
                                  ("material", "material"), ("edge", "cutting_edge_geometry"),
                                  ("tooth", "tooth_profile"), ("slot", "slot_configuration"),
                                  ("holes", "hole_configuration")):
            if row.get(source_key):
                add_fact(product, field, row[source_key], source, f"ACE PDF physical page {page}, item {sku}")
        if row.get("coating"):
            product["additional_technical_specifications"]["coating"] = row["coating"]
        if row.get("other_dimensions"):
            product["additional_technical_specifications"]["diagram_dimensions"] = row["other_dimensions"]
        else:
            product["additional_technical_specifications"].pop("diagram_dimensions", None)
        update_completeness(product)
    save_db(db)
    print(f"Imported/updated {len(ACE_ROWS)} ACE PDF candidate knives; {len(db['products'])} total records")


def import_technopack(args) -> None:
    from bs4 import BeautifulSoup
    from urllib.parse import urljoin
    db = load_db()
    count = 0
    for html_file in sorted(Path(args.path).glob("*.html")):
        soup = BeautifulSoup(html_file.read_text(encoding="utf-8"), "html.parser")
        title = next((h for h in soup.find_all("h1") if "Knife" in h.get_text(" ", strip=True)), None)
        if not title:
            raise ValueError(f"No product H1 in {html_file}")
        name = title.get_text(" ", strip=True)
        if "Knife" not in name:
            raise ValueError(f"Not a knife product: {html_file}: {name}")
        text = soup.get_text(" ", strip=True)
        sku_match = re.search(r"Model:\s*(P-[A-Z0-9.\-]+)\s+by\s+JORES", text, re.I)
        if not sku_match:
            raise ValueError(f"No JORES supplier model/SKU in {html_file}")
        sku = sku_match.group(1)
        model = ", ".join(dict.fromkeys(re.findall(r"E-FW(?:MAX|I)?-\d+", name, re.I)))
        if not model:
            raise ValueError(f"No equipment model in {html_file}")
        canonical = soup.find("link", rel="canonical")
        url = canonical.get("href") if canonical else f"https://technopackcorp.com/products/{html_file.stem}"
        product = upsert(db, f"technopack:{sku.lower()}", "flow-wrapper-knives", f"Jores {model} {name.split(' for ')[0].lower()}")
        product["equipment_manufacturer"] = "Jores Technologies"
        product["equipment_model"] = model
        product["competitor_reference_sku"] = sku
        product["knife_type"] = name.split(" for ")[0]
        product["source_website"] = "Technopack / Jores Technologies"
        product["original_product_url"] = url
        product["source_notes"] = "Supplier page lists knife type and machine model; blade dimensions are not published. PackBlade compatibility requires separate confirmation."
        for image in soup.find_all("img", alt=True):
            if (name.lower() in image["alt"].lower() or "Knife Set for Horizontal Flow Wrapper" in image["alt"]) and (image.get("src") or "").strip():
                image_url = urljoin(url, image["src"].strip())
                product["original_image_reference_url"] = image_url
                if sku.lower() not in image_url.lower():
                    note = "Reference image filename does not match the listed supplier SKU; confirm image identity before use."
                    product["image_reference_location"] = note
                    if note not in product["review_notes"]:
                        product["review_notes"].append(note)
                break
        source = add_source(product, "Technopack / Jores Technologies", url, "product_top_summary")
        if name.lower().startswith("straight"):
            add_fact(product, "cutting_edge_geometry", "straight", source, "product title")
        elif name.lower().startswith("zig-zag"):
            add_fact(product, "cutting_edge_geometry", "zigzag", source, "product title")
        update_completeness(product)
        count += 1
    save_db(db)
    print(f"Imported/updated {count} Technopack product pages; {len(db['products'])} total records")


def import_diehling(args) -> None:
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(Path(args.path).read_text(encoding="utf-8"), "html.parser")
    text = soup.get_text(" ", strip=True)
    match = re.search(r"(SP71CS0525-DD)\s+Flow wrapper cutoff blade,\s*([\d.]+)\"\s*x\s*([\d.]+)\"\s*x\s*([\d.]+)\"", text, re.I)
    if not match:
        raise ValueError("Expected PFM cutoff blade row was not found")
    sku, length, width, thickness = match.groups()
    db = load_db()
    name = f"PFM flow wrapper cutoff blade (Diehling {sku} reference)"
    product = upsert(db, f"diehling:{sku.lower()}", "flow-wrapper-knives", name)
    product["product_name"] = name
    product["image_alt_text"] = f"Photograph of {name}"
    product["equipment_manufacturer"] = "PFM"
    product["competitor_reference_sku"] = sku
    product["knife_type"] = "Flow wrapper cutoff blade"
    product["source_website"] = "Diehling Direct"
    product["original_product_url"] = "https://diehlingdirect.com/blades/pfm/"
    product["source_notes"] = "PFM brand and three dimensions listed; machine model, material and edge geometry are not stated."
    source = add_source(product, "Diehling Direct", product["original_product_url"], "supporting_document")
    for field, raw in (("length", length), ("width", width), ("thickness", thickness)):
        add_fact(product, field, raw + " in", source, f"PFM blade listing, {sku}")
    update_completeness(product)
    save_db(db)
    print(f"Imported/updated 1 Diehling flow-wrapper blade; {len(db['products'])} total records")


def validate(args) -> None:
    db = load_db()
    errors = []
    ids, keys, urls = set(), set(), set()
    for p in db["products"]:
        label = p.get("product_id", "<missing ID>")
        missing = REQUIRED_FIELDS - p.keys()
        if missing: errors.append(f"{label}: missing fields {', '.join(sorted(missing))}")
        if label in ids: errors.append(f"Duplicate ID: {label}")
        ids.add(label)
        if p["source_key"] in keys: errors.append(f"Duplicate source key: {p['source_key']}")
        keys.add(p["source_key"])
        cat = p.get("primary_category")
        if cat not in CATEGORIES: errors.append(f"{label}: invalid category {cat}")
        elif not label.startswith("PBT-" + CATEGORIES[cat][0] + "-"):
            errors.append(f"{label}: category/ID prefix mismatch")
        url = f"/products/{cat}/{p['slug']}/"
        if url in urls: errors.append(f"Duplicate URL: {url}")
        urls.add(url)
        if p.get("publication_status") not in {"candidate", "review", "approved", "rejected"}:
            errors.append(f"{label}: invalid publication status")
        if p.get("publication_status") in {"review", "approved"} and p.get("data_completeness_status") != "documented_reference":
            errors.append(f"{label}: review page lacks brand, type, dimension, or supplier SKU")
        if p.get("oem_part_number") and not p.get("oem_part_number_evidence"):
            errors.append(f"{label}: OEM part number lacks explicit source evidence")
        if p.get("reference_classification") not in {"A_documented_replacement_reference", "B_brand_no_confirmed_oem_part", "C_generic_unbranded"}:
            errors.append(f"{label}: missing audited reference classification")
        if p.get("reference_classification") == "A_documented_replacement_reference" and not p.get("documented_replacement_reference"):
            errors.append(f"{label}: documented replacement class lacks source reference")
        if p.get("publication_status") == "review" and p.get("application_status") == "substrate_unverified":
            errors.append(f"{label}: unverified film application cannot enter shortlist")
        if not p.get("original_product_url") and not (p.get("source_pdf_url") and p.get("source_pdf_page")):
            errors.append(f"{label}: missing traceable product URL or PDF URL/page")
        for field, options in p.get("specification_evidence", {}).items():
            if options:
                preferred = sorted(options, key=lambda e: SOURCE_RANK[e["tier"]])[0]["value"]
                if p.get(field) != preferred:
                    errors.append(f"{label}: selected {field} differs from highest-priority source evidence")
    if errors:
        raise SystemExit("\n".join(errors))
    print(f"Validated {len(db['products'])} products, {len(ids)} stable IDs, {len(urls)} unique URLs")


def select_review(args) -> None:
    ids = {line.strip() for line in Path(args.path).read_text(encoding="utf-8").splitlines()
           if line.strip() and not line.startswith("#")}
    db = load_db()
    known = {p["product_id"] for p in db["products"]}
    unknown = ids - known
    if unknown:
        raise ValueError(f"Unknown shortlist IDs: {', '.join(sorted(unknown))}")
    for product in db["products"]:
        if product["publication_status"] in {"candidate", "review"}:
            product["publication_status"] = "review" if product["product_id"] in ids else "candidate"
    save_db(db)
    print(f"Selected {len(ids)} locally reviewable product pages")


def yaml_string(value: str) -> str:
    return json.dumps(str(value), ensure_ascii=False)


def product_markdown(p: dict) -> str:
    category_title = CATEGORIES[p["primary_category"]][1]
    name = p["product_name"]
    context = p.get("equipment_model") or p.get("equipment_reference_number") or p.get("competitor_reference_sku")
    coating = p.get("additional_technical_specifications", {}).get("coating")
    description = (f"{p['knife_type']} listed for {p['equipment_manufacturer']}"
                   + (f" reference {context}" if context else "")
                   + (f", {coating}" if coating and coating != "Uncoated" else "")
                   + ". Review source specifications and confirm the installed part before quotation.")
    review = p["publication_status"] == "review"
    frontmatter = ["---", f"title: {yaml_string(name)}", f"seo_title: {yaml_string(name + ' | PackBlade Tech')}",
                   f"description: {yaml_string(description)}", "layout: page",
                   f"product_id: {yaml_string(p['product_id'])}", f"primary_category: {yaml_string(p['primary_category'])}",
                   f"product_category_title: {yaml_string(category_title)}", "---", "<!-- Generated by research/catalog.py. Edit research/products.json and rerun render. -->"]
    if review:
        frontmatter[5:5] = ["noindex: true", "sitemap: false"]
    lines = frontmatter + [f"# {name}", "", "<p class=\"page-intro\">A supplier catalog knife reference for quotation review. Check the installed part and machine documentation before selecting a replacement.</p>", "", "## Product information", "", "<table class=\"product-specs\"><tbody>"]
    image_file = ROOT / "source" / p["image_path"].lstrip("/")
    if image_file.is_file():
        lines[lines.index("## Product information"):lines.index("## Product information")] = [
            f'<figure class="product-photo"><img src="{escape(p["image_path"])}" alt="{escape(p.get("image_alt_text") or name)}"></figure>', ""
        ]
    info = [("Product name", name), ("PackBlade Tech reference SKU", p["product_id"]),
            ("Equipment brand", p["equipment_manufacturer"]), ("Equipment model", p["equipment_model"]),
            ("Supplier-stated replacement reference" if p.get("documented_replacement_reference") else "Source-listed equipment reference", p["equipment_reference_number"]),
            ("Supplier reference SKU", p["competitor_reference_sku"]), ("Knife category", category_title)]
    for label, value in info:
        if value:
            lines.append(f"<tr><th>{escape(label)}</th><td>{escape(str(value))}</td></tr>")
    lines += ["</tbody></table>", "", "## Technical specifications", "", "<table class=\"product-specs\"><tbody>"]
    labels = {"length": "Length", "width": "Width", "thickness": "Thickness", "outer_diameter": "Outer diameter",
              "inner_diameter": "Inner diameter", "material": "Material", "hardness": "Hardness",
              "cutting_edge_geometry": "Cutting edge", "bevel_angle": "Bevel angle", "tooth_profile": "Tooth profile",
              "hole_configuration": "Hole configuration", "slot_configuration": "Slot configuration"}
    for field, label in labels.items():
        if p.get(field):
            lines.append(f"<tr><th>{label}</th><td>{escape(display(p[field]))}</td></tr>")
    for key, value in p.get("additional_technical_specifications", {}).items():
        if not key.startswith(("catalog_", "supplier_")) and value:
            lines.append(f"<tr><th>{escape(key.replace('_', ' ').title())}</th><td>{escape(str(value))}</td></tr>")
    lines += ["</tbody></table>", "", "## Knife reference", ""]
    facts = [display(p[f]) for f in ("length", "width", "thickness") if p.get(f)]
    sentence = f"The source lists this {p['knife_type'].lower()} under {p['equipment_manufacturer']}"
    if context: sentence += f" reference {context}"
    sentence += "."
    if facts: sentence += " Published size references include " + ", ".join(facts) + "."
    if p.get("material"): sentence += f" The listed material is {p['material']}."
    if p.get("documented_replacement_reference"):
        sentence += " The supplier states that this item replaces the named equipment reference; the OEM status of that number has not been independently verified."
    lines += [sentence, "", "<div class=\"product-note\">Reference specifications are unverified source data. Final dimensions, edge details and machine compatibility must be confirmed against the installed blade, drawing or sample before quotation.</div>", "", "## Request a quote", "", "Email [sales@packbladetech.com](mailto:sales@packbladetech.com) with your machine model, existing blade part number, drawing, dimensions, photographs or a sample reference. Include the quantity required.", "", f"[Browse {category_title}](/products/{p['primary_category']}/) · [How to measure a packaging knife](/guides/identify-measure-packaging-machine-knives/)", ""]
    if p.get("specification_discrepancy_status") == "review_required":
        position = lines.index("## Request a quote")
        lines[position:position] = ["<p><strong>Source discrepancy:</strong> One or more source values differ. See the research record and confirm the installed part before quotation.</p>", ""]
    if p.get("source_ambiguities"):
        position = lines.index("## Request a quote")
        lines[position:position] = ["<p><strong>Illustration association unresolved:</strong> The catalog item row and adjacent grouped illustration must be checked against a drawing or sample. Diagram details are not assigned to this SKU.</p>", ""]
    return "\n".join(lines)


def write_csv(path: Path, rows: list[dict], fields: list[str]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def render(args) -> None:
    db = load_db()
    validate(args)
    selected = [p for p in db["products"] if p["publication_status"] in {"review", "approved"}]
    cards = []
    expected_files = set()
    for p in selected:
        path = ROOT / "source/products" / p["primary_category"] / p["slug"] / "index.md"
        expected_files.add(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(product_markdown(p), encoding="utf-8")
        summary_parts = [p.get("equipment_manufacturer")]
        if p.get("equipment_model"): summary_parts.append("Model " + p["equipment_model"])
        elif p.get("documented_replacement_reference"):
            summary_parts.append("Supplier-stated replacement " + p["documented_replacement_reference"])
        elif p.get("equipment_reference_number"):
            summary_parts.append("Source reference " + p["equipment_reference_number"])
        if p.get("competitor_reference_sku"): summary_parts.append("Supplier " + p["competitor_reference_sku"])
        if p.get("length"): summary_parts.append(display(p["length"]))
        cards.append({"product_id": p["product_id"], "product_name": p["product_name"],
                      "primary_category": p["primary_category"],
                      "url": f"/products/{p['primary_category']}/{p['slug']}/",
                      "summary": " · ".join(str(x) for x in summary_parts if x)})
    cards.sort(key=lambda c: c["product_id"])
    for path in (ROOT / "source/products").glob("*/*/index.md"):
        if path not in expected_files and "<!-- Generated by research/catalog.py." in path.read_text(encoding="utf-8"):
            path.unlink()
            try:
                path.parent.rmdir()
            except OSError:
                pass
    (ROOT / "source/_data/catalog_cards.json").write_text(json.dumps(cards, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    write_csv(REPORT_DIR / "shortlist.csv", [
        {"product_id": p["product_id"], "product_name": p["product_name"], "category": p["primary_category"],
         "source_key": p["source_key"], "url": f"/products/{p['primary_category']}/{p['slug']}/",
         "review_notes": "; ".join(p.get("review_notes", []))} for p in selected],
        ["product_id", "product_name", "category", "source_key", "url", "review_notes"])
    write_csv(REPORT_DIR / "image-references.csv", [
        {"product_id": p["product_id"], "source_website": p.get("source_website"),
         "original_image_reference_url": p.get("original_image_reference_url"),
         "image_reference_location": p.get("image_reference_location"),
         "published_image_path": p.get("image_path"), "image_alt_text": p.get("image_alt_text"),
         "review_notes": "; ".join(p.get("review_notes", [])),
         "image_published": (ROOT / "source" / p["image_path"].lstrip("/")).exists()}
        for p in db["products"]],
        ["product_id", "source_website", "original_image_reference_url", "image_reference_location", "published_image_path", "image_alt_text", "review_notes", "image_published"])
    discrepancy_rows = []
    for p in db["products"]:
        for field, options in p.get("specification_evidence", {}).items():
            if len({json.dumps(e["value"], sort_keys=True) for e in options}) > 1:
                discrepancy_rows.append({"product_id": p["product_id"], "field": field,
                                         "selected_value": display(options[0]["value"]), "selected_tier": options[0]["tier"],
                                         "selected_location": options[0]["location"],
                                         "all_values": " | ".join(f"{e['raw']} [{e['tier']}, {e['location']}, {e['source_url']}]" for e in options),
                                         "status": "unverified source reference; confirm before quotation"})
        for observation_id in p.get("source_ambiguities", []):
            if observation_id == "ACE-P11-GLOUCESTER-ILLUSTRATIONS":
                evidence = p.get("specification_evidence", {}).get("slot_configuration", [])
                row = next((e for e in evidence if e.get("source_url") == ACE_URL and e.get("pdf_page") == 11), None)
                discrepancy_rows.append({"product_id": p["product_id"], "field": "slot_configuration",
                    "selected_value": display(p["slot_configuration"]), "selected_tier": "supporting_document",
                    "selected_location": row["location"] if row else "ACE PDF physical page 11 item row",
                    "all_values": "Item row: No slots | Page-level grouped illustration: elongated slots shown; no item-number association | " + ACE_URL,
                    "status": "unresolved illustration association; diagram not assigned to SKU; confirm against drawing or sample"})
    write_csv(REPORT_DIR / "specification-discrepancies.csv", discrepancy_rows,
              ["product_id", "field", "selected_value", "selected_tier", "selected_location", "all_values", "status"])
    ref_groups = defaultdict(list)
    for p in db["products"]:
        if p.get("equipment_reference_number"):
            ref_groups[(p.get("equipment_manufacturer"), p["equipment_reference_number"])].append(p["product_id"])
    potential_duplicates = [{"manufacturer": k[0], "equipment_reference": k[1], "product_ids": v}
                            for k, v in ref_groups.items() if len(v) > 1]
    summary = {"total_candidates": len(db["products"]), "review_pages": len(selected),
               "by_source": dict(Counter(p["source_website"] for p in db["products"])),
               "by_category": dict(Counter(p["primary_category"] for p in db["products"])),
               "review_by_category": dict(Counter(p["primary_category"] for p in selected)),
               "completeness": dict(Counter(p["data_completeness_status"] for p in db["products"])),
               "reference_image_urls": sum(bool(p.get("original_image_reference_url")) for p in db["products"]),
               "verified_oem_part_numbers": sum(bool(p.get("oem_part_number")) for p in db["products"]),
               "documented_supplier_replacement_references": sum(bool(p.get("documented_replacement_reference")) for p in db["products"]),
               "reference_classes": dict(Counter(p["reference_classification"] for p in db["products"])),
               "missing_fields": {f: sum(not p.get(f) for p in db["products"]) for f in SPEC_FIELDS},
               "potential_duplicate_references": potential_duplicates,
               "discrepancies": len(discrepancy_rows)}
    (REPORT_DIR / "coverage.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(f"Rendered {len(selected)} local noindex product pages; {len(db['products'])} candidate records")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    for name, fn in (("extract-pdf", extract_pdf), ("stage-pdf-items", stage_pdf_items),
                     ("stage-html-tables", stage_html_tables), ("import-csv", import_csv),
                     ("import-cadence", import_cadence), ("import-cadence-details", import_cadence_details),
                     ("import-stiles", import_stiles),
                     ("import-ace", import_ace), ("import-technopack", import_technopack),
                     ("import-diehling", import_diehling)):
        cmd = sub.add_parser(name)
        cmd.add_argument("path")
        if name == "extract-pdf": cmd.add_argument("--source-url", required=True)
        if name == "stage-pdf-items": cmd.add_argument("--pattern", default=r"\b[A-Z0-9]+(?:-[A-Z0-9]+){2,}\b")
        cmd.set_defaults(func=fn)
    sub.add_parser("validate").set_defaults(func=validate)
    sub.add_parser("render").set_defaults(func=render)
    cmd = sub.add_parser("select-review")
    cmd.add_argument("path")
    cmd.set_defaults(func=select_review)
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()

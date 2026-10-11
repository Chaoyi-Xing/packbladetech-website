#!/usr/bin/env python3
"""Check the local Hexo output before any publication."""

from __future__ import annotations

import json
from pathlib import Path
from urllib.parse import unquote, urlparse
from xml.etree import ElementTree

from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parent.parent
PUBLIC = ROOT / "public"
DOMAIN = "https://packbladetech.com"
CATEGORIES = (
    "serrated-packaging-knives", "flow-wrapper-knives", "bag-making-sealing-knives",
    "sachet-cutting-knives", "film-cutting-slitting-knives",
)


def local_file(source: Path, href: str) -> Path | None:
    parsed = urlparse(href)
    if parsed.scheme in {"http", "https", "mailto", "tel"} or href.startswith("#") or href.startswith("//"):
        return None
    if parsed.path.startswith("/"):
        target = PUBLIC / unquote(parsed.path).lstrip("/")
    else:
        target = source.parent / unquote(parsed.path)
    if target.is_dir() or not target.suffix:
        target /= "index.html"
    return target.resolve()


def main() -> None:
    errors = []
    pages = sorted(PUBLIC.rglob("*.html"))
    products = [p for p in pages if len(p.relative_to(PUBLIC).parts) == 4 and p.parts[-4] == "products"]
    for page in pages:
        soup = BeautifulSoup(page.read_text(encoding="utf-8"), "html.parser")
        relative = page.relative_to(PUBLIC).as_posix()
        expected = DOMAIN + "/" + relative.removesuffix("index.html")
        canonical = soup.find("link", rel="canonical")
        if not canonical or canonical.get("href") != expected:
            errors.append(f"Canonical mismatch: {relative}")
        for link in soup.find_all(["a", "img", "link"]):
            href = link.get("href") or link.get("src")
            if not href:
                continue
            if href.startswith("mailto:") and href != "mailto:sales@packbladetech.com":
                errors.append(f"Wrong email: {relative}: {href}")
            target = local_file(page, href)
            if target and not target.is_file():
                errors.append(f"Broken local link: {relative}: {href}")
        if page in products:
            robots = soup.find("meta", attrs={"name": "robots"})
            if not robots or "noindex" not in robots.get("content", ""):
                errors.append(f"Draft product is indexable: {relative}")
    sitemap = ElementTree.parse(PUBLIC / "sitemap.xml")
    urls = {node.text for node in sitemap.iter() if node.tag.endswith("loc")}
    for category in CATEGORIES:
        path = PUBLIC / "products" / category / "index.html"
        if not path.is_file(): errors.append(f"Missing category: {category}")
        if DOMAIN + "/products/" + category + "/" not in urls:
            errors.append(f"Category missing from sitemap: {category}")
    for product in products:
        rel = product.relative_to(PUBLIC).as_posix().removesuffix("index.html")
        if DOMAIN + "/" + rel in urls:
            errors.append(f"Draft in sitemap: {rel}")
    records = json.loads((ROOT / "research/products.json").read_text())["products"]
    draft_titles, draft_descriptions = set(), set()
    for record in (p for p in records if p["publication_status"] == "review"):
        page = PUBLIC / "products" / record["primary_category"] / record["slug"] / "index.html"
        if not page.is_file():
            errors.append(f"Missing draft page: {record['product_id']}")
            continue
        soup = BeautifulSoup(page.read_text(encoding="utf-8"), "html.parser")
        h1 = soup.find("h1")
        if not h1 or h1.get_text(strip=True) != record["product_name"]:
            errors.append(f"Product H1 mismatch: {record['product_id']}")
        description = soup.find("meta", attrs={"name": "description"})
        if not description or record["knife_type"] not in description.get("content", ""):
            errors.append(f"Product meta description mismatch: {record['product_id']}")
        title_text = soup.title.get_text(strip=True) if soup.title else ""
        description_text = description.get("content", "") if description else ""
        if title_text in draft_titles: errors.append(f"Duplicate draft SEO title: {title_text}")
        if description_text in draft_descriptions: errors.append(f"Duplicate draft meta description: {record['product_id']}")
        draft_titles.add(title_text)
        draft_descriptions.add(description_text)
        if record["product_id"] not in soup.get_text(" ", strip=True):
            errors.append(f"Product ID missing from page: {record['product_id']}")
        if not soup.find("a", href="mailto:sales@packbladetech.com"):
            errors.append(f"RFQ email missing: {record['product_id']}")
        if record.get("documented_replacement_reference") and "Supplier-stated replacement reference" not in soup.get_text(" ", strip=True):
            errors.append(f"Replacement reference mislabeled: {record['product_id']}")
    if (PUBLIC / "products/custom-machine-knives/index.html").exists():
        errors.append("Legacy sixth category is still generated")
    for guide in ("identify-measure-packaging-machine-knives", "serrated-vs-straight-packaging-knives",
                  "select-flow-wrapping-replacement-knives"):
        if DOMAIN + "/guides/" + guide + "/" not in urls:
            errors.append(f"Guide missing from sitemap: {guide}")
    corpus = "\n".join(page.read_text(encoding="utf-8").lower() for page in pages)
    for forbidden in ("hk bladetech", "hkbladetech", "@hkbladetech"):
        if forbidden in corpus: errors.append(f"Old brand/contact found: {forbidden}")
    if not (PUBLIC / "robots.txt").read_text().strip().endswith(DOMAIN + "/sitemap.xml"):
        errors.append("robots.txt sitemap URL mismatch")
    if any(PUBLIC.rglob("*.jpg")) or any(PUBLIC.rglob("*.png")):
        errors.append("Unexpected raster image published; review source and license")
    expected_drafts = sum(p["publication_status"] == "review" for p in records)
    if len(products) != expected_drafts:
        errors.append(f"Expected {expected_drafts} draft pages, found {len(products)}")
    if errors:
        raise SystemExit("\n".join(errors))
    print(f"Verified {len(pages)} HTML pages, {len(products)} noindex product drafts, five categories, three guides, local links, canonicals, sitemap, email and image policy")


if __name__ == "__main__":
    main()

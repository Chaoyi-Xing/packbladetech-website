# PackBlade Tech product research

This directory holds **research references**, not verified PackBlade Tech manufacturing specifications. Only records with `publication_status: "review"` produce local draft pages. Draft pages use `noindex` and are excluded from the sitemap until reviewed and approved. Neither this workflow nor `npm run build` deploys the site. The GitHub Pages workflow still deploys on a push to `main`, so do not push this branch for research review.

## Sources and local files

- Put downloaded supplier PDF/HTML files in `research/sources/`. This directory is ignored by Git; the source URL and PDF page number remain in each database record.
- `research/work/` holds extracted page text and staging files. It is ignored by Git so full third-party catalog text is not committed.
- The normalized, editable source of truth is `research/products.json`. Product IDs, competitor SKUs, equipment reference numbers, and source URLs are separate fields.
- `research/reports/` holds the shortlist, image reference list, discrepancy report, and coverage summary.
- `research/reports/classification-audit.csv` records the evidence and before/after category for every candidate. `category-distribution.csv` and `reference-summary.json` summarize the audit.
- `research/reports/source-observations.json` preserves shared ACE PDF diagrams separately from individual item facts. The Gloucester slot review and possible overlaps are in `specification-discrepancies.csv` and `duplicate-review.md`.
- Product photographs must be authentic or licensed and placed under `source/images/products/<PBT-ID>/`. No competitor images are copied into public assets.

## Install and run

```sh
python3 -m venv research/.venv
research/.venv/bin/pip install -r research/requirements.txt
research/.venv/bin/python research/catalog.py extract-pdf research/sources/Converting-packaging-2024.pdf --source-url https://americancuttingedge.com/media/wysiwyg/resource-library/Converting-packaging-2024.pdf
research/.venv/bin/python research/catalog.py stage-pdf-items research/sources/Converting-packaging-2024.pdf
research/.venv/bin/python research/catalog.py stage-html-tables research/sources/another-catalog.html
research/.venv/bin/python research/catalog.py import-ace research/sources/Converting-packaging-2024.pdf
research/.venv/bin/python research/catalog.py import-cadence research/sources/cadence-packaging.html
research/.venv/bin/python research/catalog.py import-cadence-details research/sources/cadence-details
research/.venv/bin/python research/catalog.py import-stiles research/sources/stiles-bagger.html
research/.venv/bin/python research/catalog.py import-technopack research/sources/technopack
research/.venv/bin/python research/catalog.py import-diehling research/sources/diehling-pfm.html
research/.venv/bin/python research/catalog.py import-csv research/sources/normalized-products.csv
research/.venv/bin/python research/audit_catalog.py
research/.venv/bin/python research/catalog.py select-review research/shortlist_ids.txt
research/.venv/bin/python research/catalog.py validate
research/.venv/bin/python research/catalog.py render
npm run build
research/.venv/bin/python -m unittest discover -s research -p 'test_*.py'
research/.venv/bin/python research/verify_site.py
```

`extract-pdf` preserves numbered pages as a structured staging file. `stage-pdf-items` proposes reference-bearing lines with page numbers, and `stage-html-tables` exports rows from a manually supplied HTML file. Review and map staging rows to the columns in `normalized-products-template.csv` before import; automatic guesses are never published. `import-ace` checks every mapped item number against the local PDF page before importing 33 scoped entries. A Cloudflare challenge prevents scripted download of the ACE file, so the local PDF is required. HTML adapters demonstrate source-specific parsing; additional supplier tables can use the same normalized record and evidence functions.

Run `audit_catalog.py` after imports to refresh application evidence, secondary search tags, A/B/C reference classes, category distribution and duplicate review. Existing category assignments and IDs remain stable; a new source-supported application requiring an ID-prefix change must be reviewed manually. Supplier-stated replacement references are stored separately from independently verified OEM part numbers.

The PDF page number is the **physical PDF page, starting at 1**. If a printed page number differs, retain it in `source_notes`. Source precedence for conflicts is: product-page top summary, product-page technical table, then supporting catalog/documentation. The database keeps all values under `specification_evidence`; selected values remain unverified source references. `render` recreates pages and reports deterministically; existing IDs survive repeated imports. `research/shortlist_ids.txt` controls which records produce local review pages.

## Review before any publication

Each candidate needs a single primary category from the five approved categories. A supplier's "Equipment OEM" label or replacement reference is not, by itself, proof of an OEM part number or fit. Confirm brand, model, part reference, dimensions, edge geometry, material, and compatibility against the buyer's machine documentation or sample before quotation. Never copy third-party marketing text or product photographs into the site.

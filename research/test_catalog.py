import unittest

from catalog import add_fact, add_source, dimension, load_db, upsert, update_completeness


class CatalogRulesTest(unittest.TestCase):
    def test_exact_inch_conversion(self):
        self.assertEqual(dimension("0.039 in")["millimeters"], 0.9906)
        self.assertEqual(dimension("12-1/2 in")["millimeters"], 317.5)

    def test_source_priority_preserves_conflict(self):
        db = {"products": []}
        product = upsert(db, "fixture:one", "bag-making-sealing-knives", "Fixture blade")
        catalog = add_source(product, "PDF", "https://example.com/catalog.pdf", "supporting_document", 3)
        table = add_source(product, "Page", "https://example.com/blade", "product_detail_table")
        top = add_source(product, "Page", "https://example.com/blade", "product_top_summary")
        add_fact(product, "hardness", "44–46 HRC", catalog, "PDF row")
        add_fact(product, "hardness", "42–44 HRC", table, "technical table")
        add_fact(product, "hardness", "36–38 HRC", top, "top summary")
        self.assertEqual(product["hardness"], "36–38 HRC")
        self.assertEqual(len(product["specification_evidence"]["hardness"]), 3)
        self.assertEqual(product["specification_discrepancy_status"], "review_required")

    def test_reimport_keeps_id(self):
        db = {"products": []}
        original = upsert(db, "fixture:one", "flow-wrapper-knives", "Fixture blade")
        again = upsert(db, "fixture:one", "flow-wrapper-knives", "Fixture blade")
        self.assertIs(original, again)
        self.assertEqual(original["product_id"], "PBT-FW-001")
        self.assertEqual(len(db["products"]), 1)

    def test_same_source_location_replaces_corrected_value(self):
        db = {"products": []}
        product = upsert(db, "fixture:two", "flow-wrapper-knives", "Fixture blade")
        source = add_source(product, "PDF", "https://example.com/catalog.pdf", "supporting_document", 2)
        add_fact(product, "length", "10 in", source, "item row")
        add_fact(product, "length", "11 in", source, "item row")
        update_completeness(product)
        self.assertEqual(len(product["specification_evidence"]["length"]), 1)
        self.assertEqual(product["length"]["millimeters"], 279.4)
        self.assertEqual(product["specification_discrepancy_status"], "none_observed_in_accessible_sources")

    def test_grouped_ace_drawings_are_not_item_specifications(self):
        products = {p["product_id"]: p for p in load_db()["products"]}
        gloucester = products["PBT-SP-005"]
        self.assertEqual(gloucester["slot_configuration"], "No slots")
        self.assertIsNone(gloucester["length"])
        self.assertEqual(gloucester["source_ambiguities"], ["ACE-P11-GLOUCESTER-ILLUSTRATIONS"])
        self.assertIsNone(products["PBT-FS-003"]["outer_diameter"])
        self.assertEqual(products["PBT-FS-003"]["publication_status"], "candidate")

    def test_supplier_reference_and_geometry_variants_remain_distinct(self):
        products = {p["product_id"]: p for p in load_db()["products"]}
        self.assertEqual(products["PBT-BS-007"]["documented_replacement_reference"], "10137A0437")
        self.assertIsNone(products["PBT-BS-007"]["oem_part_number"])
        self.assertNotEqual(products["PBT-SP-051"]["cutting_edge_geometry"], products["PBT-SP-052"]["cutting_edge_geometry"])


if __name__ == "__main__":
    unittest.main()

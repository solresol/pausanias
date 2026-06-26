import unittest
import zipfile
from tempfile import TemporaryDirectory

from manto_importer import (
    MAX_RAW_CELL_CHARS,
    candidate_date_text,
    compact_record_for_storage,
    edge_candidates,
    extract_latest_year,
    iter_zip_records,
    source_filter_status,
)
from manto_release import release_from_zenodo_record


class MantoPipelineTests(unittest.TestCase):
    def test_release_from_zenodo_record_selects_zip(self):
        release = release_from_zenodo_record(
            {
                "id": 19446255,
                "conceptrecid": 19446254,
                "doi": "10.5281/zenodo.19446255",
                "conceptdoi": "10.5281/zenodo.19446254",
                "created": "2026-04-22T05:05:25Z",
                "modified": "2026-06-10T23:36:10Z",
                "metadata": {
                    "title": "MANTO data release",
                    "version": "v.1",
                    "license": {"id": "cc-by-nc-4.0"},
                },
                "files": [
                    {"key": "readme.txt", "links": {"self": "https://example.test/readme"}},
                    {
                        "key": "publication-2616.zip",
                        "size": 123,
                        "checksum": "md5:abc",
                        "links": {"self": "https://example.test/zip"},
                    },
                ],
            }
        )
        self.assertEqual(release.record_id, 19446255)
        self.assertEqual(release.concept_record_id, 19446254)
        self.assertEqual(release.file_key, "publication-2616.zip")
        self.assertEqual(release.license_id, "cc-by-nc-4.0")

    def test_extract_latest_year_handles_bce_and_centuries(self):
        self.assertEqual(extract_latest_year("Herodotus 450 BCE"), -450)
        self.assertEqual(extract_latest_year("5th century BCE"), -401)
        self.assertEqual(extract_latest_year("2nd century CE"), 200)
        self.assertIsNone(extract_latest_year("undated source"))

    def test_source_filter_is_strict_pre_pausanias(self):
        self.assertEqual(source_filter_status("Herodotus", -430), (True, None))
        self.assertEqual(
            source_filter_status("Pausanias, Periegesis", 170),
            (False, "pausanias_source"),
        )
        self.assertEqual(
            source_filter_status("Unknown source", None),
            (False, "unknown_source_date"),
        )
        self.assertEqual(
            source_filter_status("Later source", 300),
            (False, "source_not_pre_pausanias"),
        )

    def test_edge_candidates_prefers_object_classification_and_relations(self):
        record = {
            "Object ID": "100",
            "Classification ID": "200",
            "Source Object ID": "300",
            "Target Object ID": "400",
        }
        self.assertEqual(
            edge_candidates(record, "100"),
            [
                ("100", "200", "object_classification"),
                ("300", "400", "object_relation"),
                ("100", "200", "record_classification"),
            ],
        )

    def test_edge_candidates_handles_relation_specific_object_id_columns(self):
        record = {
            "Object ID": "8188398",
            "Place of birth of - Object ID": "8188419",
            "Place of birth of": (
                "start-attributes [object=7140_11296585]Callimachus, Hymn to Zeus[/object] "
                "[object=11356_11309899]Early Classical (ca. 480-450 BCE)[/object] end-path"
            ),
        }
        self.assertIn(
            ("8188398", "8188419", "place_of_birth_of"),
            edge_candidates(record, "8188398"),
        )
        self.assertIn("480-450 BCE", candidate_date_text(record, ""))

    def test_iter_zip_records_handles_no_header_object_definition_csv(self):
        with TemporaryDirectory() as tmpdir:
            zip_path = f"{tmpdir}/manto.zip"
            csv_text = (
                'nodegoat-key,8182080,"Aigisthos",11299338,'
                '"[object=6580_10159511]Tomb[/object]"\n'
            )
            with zipfile.ZipFile(zip_path, "w") as archive:
                archive.writestr(
                    "data/entity_6580/related_entities_object_definitions_27385.csv",
                    csv_text,
                )

            records = list(iter_zip_records(zip_path))

        self.assertEqual(len(records), 1)
        _, _, record_number, record = records[0]
        self.assertEqual(record_number, 1)
        self.assertEqual(record["Object ID"], "8182080")
        self.assertEqual(record["Related entities - Object ID"], "11299338")
        self.assertIn(
            ("8182080", "11299338", "related_entities"),
            edge_candidates(record, "8182080"),
        )

    def test_compact_record_for_storage_truncates_large_cells(self):
        large_value = "x" * (MAX_RAW_CELL_CHARS + 10)
        compacted = compact_record_for_storage({"Object ID": "1", "Large": large_value})

        self.assertEqual(compacted["Object ID"], "1")
        self.assertEqual(len(compacted["Large"]), MAX_RAW_CELL_CHARS)
        self.assertEqual(compacted["_truncated_fields"]["Large"], len(large_value))


if __name__ == "__main__":
    unittest.main()

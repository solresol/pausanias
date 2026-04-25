import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from check_proper_noun_spellings import (
    Policy,
    TextRow,
    build_unambiguous_replacements,
    find_deprecated_variants,
    import_decisions_from_review_tsv,
    replace_unambiguous_variants,
    replace_deprecated_variants,
)


class ProperNounSpellingTests(unittest.TestCase):
    def setUp(self):
        self.policy = Policy(
            reference_form="Πειραιεύς",
            entity_type="place",
            wikidata_qid="Q58976",
            preferred_english="Piraeus",
            allowed_variants=(),
            deprecated_variants=("Peiraeus",),
        )

    def test_finds_deprecated_variant_with_word_boundaries(self):
        findings = find_deprecated_variants(
            TextRow(
                passage_id="1.1.2",
                source_table="translations",
                source_column="english_translation",
                source_key="1.1.2",
                text="Peiraeus was a harbor; not AntiPeiraeusian.",
                update_key=("1.1.2",),
            ),
            self.policy,
        )

        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0].observed_variant, "Peiraeus")
        self.assertEqual(findings[0].source_table, "translations")

    def test_replaces_deprecated_variant_without_touching_substrings(self):
        updated, replacements = replace_deprecated_variants(
            "Peiraeus and AntiPeiraeusian are different strings.",
            self.policy,
        )

        self.assertEqual(replacements, 1)
        self.assertEqual(updated, "Piraeus and AntiPeiraeusian are different strings.")

    def test_import_review_tsv_chooses_dominant_prose_spelling(self):
        with TemporaryDirectory() as tmpdir:
            review_tsv = Path(tmpdir) / "review.tsv"
            review_tsv.write_text(
                "category\treference_form\tentity_type\tpreferred\tvariants\t"
                "preferred_hits\tvariant_hits\tqid\tlabel\tpassages\n"
                "mixed_prose_spellings\tΚάδμος\tperson\tKadmos\t"
                "Cadmus (47); Cadmos (2)\t4\t49\tQ13053204\tKadmos\t9.5.1\n"
                "db_preferred_differs_from_prose\tστάδιον\tplace\tstadion\t"
                "stadium (8)\t0\t8\tQ16331589\tstadion\t5.14.9\n",
                encoding="utf-8",
            )

            decisions = import_decisions_from_review_tsv(review_tsv)

        self.assertEqual(len(decisions), 1)
        self.assertEqual(decisions[0].preferred_english, "Cadmus")
        self.assertEqual(decisions[0].deprecated_variants, ("Cadmos", "Kadmos"))

    def test_import_review_tsv_applies_conflict_override(self):
        with TemporaryDirectory() as tmpdir:
            review_tsv = Path(tmpdir) / "review.tsv"
            review_tsv.write_text(
                "category\treference_form\tentity_type\tpreferred\tvariants\t"
                "preferred_hits\tvariant_hits\tqid\tlabel\tpassages\n"
                "mixed_prose_spellings\tἈφροδίτη Οὐρανία\tdeity\t"
                "Aphrodite Ourania\tAphrodite Urania (3)\t3\t3\t\t\t1.14.7\n",
                encoding="utf-8",
            )

            decisions = import_decisions_from_review_tsv(review_tsv)

        self.assertEqual(decisions[0].preferred_english, "Aphrodite Urania")
        self.assertEqual(decisions[0].deprecated_variants, ("Aphrodite Ourania",))

    def test_unambiguous_replacements_skip_other_canonical_terms(self):
        policies = [
            Policy("Ἡρακλῆς", "person", None, "Heracles", (), ("Herakles",)),
            Policy("Αἴγεια", "place", None, "Aegeira", (), ("Aigeira",)),
            Policy("Αἴγειρα", "place", None, "Aigeira", (), ("Aegeira",)),
            Policy("Παιωνία", "other", None, "Paionia", (), ("Paeonia",)),
            Policy(
                "Ἀθηνᾶ Παιωνία",
                "deity",
                None,
                "Athena Paeonia",
                (),
                ("Athena Paionia",),
            ),
        ]

        replacements = build_unambiguous_replacements(policies)
        updated, count = replace_unambiguous_variants(
            "Herakles the Theban went to Aigeira. Athena Paionia stayed whole.",
            replacements,
        )

        self.assertEqual(
            replacements,
            {
                "Herakles": "Heracles",
                "Athena Paionia": "Athena Paeonia",
            },
        )
        self.assertEqual(count, 2)
        self.assertEqual(
            updated,
            "Heracles the Theban went to Aigeira. Athena Paeonia stayed whole.",
        )


if __name__ == "__main__":
    unittest.main()

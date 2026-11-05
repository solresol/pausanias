import os
import stat
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from PIL import Image

from build_graphic_book import build_pages, write_index, write_pdf
from website.generators import generate_llm_grammar_pages, generate_translation_pages


class GraphicBookReaderTests(unittest.TestCase):
    def test_new_public_book_is_readable_under_private_umask(self):
        with TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            root_mode = stat.S_IMODE(root.stat().st_mode)
            images = root / "private-images" / "1" / "28"
            images.mkdir(parents=True)
            Image.new("RGB", (2, 2), "white").save(images / "6.png")
            output = root / "site" / "graphic-book"
            private_log = root / "private.log"
            previous = os.umask(0o077)
            try:
                private_log.write_text("private diagnostics")
                pages = build_pages(root / "private-images", output)
                write_index(output, "Title", "Byline", pages, "book.pdf")
                write_pdf(output, pages, "book.pdf", root / "absent-title.png")
                # Public artifact handling must not relax the caller's umask.
                (root / "later-private.log").write_text("still private")
            finally:
                os.umask(previous)
            for relative in ["index.html", "1/28/6.html", "images/1/28/6.png", "book.pdf"]:
                self.assertEqual(stat.S_IMODE((output / relative).stat().st_mode), 0o644)
            for relative in ["site", "site/graphic-book", "site/graphic-book/1", "site/graphic-book/1/28",
                             "site/graphic-book/images", "site/graphic-book/images/1/28"]:
                self.assertEqual(stat.S_IMODE((root / relative).stat().st_mode), 0o755)
            self.assertEqual(stat.S_IMODE(root.stat().st_mode), root_mode)
            self.assertEqual(stat.S_IMODE(private_log.stat().st_mode), 0o600)
            self.assertEqual(stat.S_IMODE((root / "later-private.log").stat().st_mode), 0o600)
            self.assertEqual(private_log.read_text(), "private diagnostics")
            self.assertIn("Passage 1.28.6", (output / "1/28/6.html").read_text())
            self.assertTrue((output / "book.pdf").read_bytes().startswith(b"%PDF"))

    def test_existing_public_modes_and_private_files_are_preserved(self):
        with TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            image_dir = root / "images" / "1" / "28"
            image_dir.mkdir(parents=True)
            (image_dir / "6.png").write_bytes(b"fake image")
            output = root / "site" / "graphic-book"
            pages = build_pages(root / "images", output)
            write_index(output, "Title", "Byline", pages, "book.pdf")
            (output / "index.html").chmod(0o664)
            (output / "1/28").chmod(0o775)
            private = root / "private.key"
            private.write_text("unrelated private content")
            private.chmod(0o600)
            previous = os.umask(0o077)
            try:
                write_index(output, "Title", "Byline", pages, "book.pdf")
            finally:
                os.umask(previous)
            self.assertEqual(stat.S_IMODE((output / "index.html").stat().st_mode), 0o664)
            self.assertEqual(stat.S_IMODE((output / "1/28").stat().st_mode), 0o775)
            self.assertEqual(stat.S_IMODE(private.stat().st_mode), 0o600)
            self.assertEqual(private.read_text(), "unrelated private content")

    def test_builds_reader_pages_with_direct_passage_urls(self):
        with TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            image_dir = root / "images"
            output_dir = root / "site" / "graphic-book"
            (image_dir / "1" / "1").mkdir(parents=True)
            (image_dir / "1" / "1" / "3.png").write_bytes(b"fake image")
            (image_dir / "1" / "1" / "4.png").write_bytes(b"fake image")

            pages = build_pages(image_dir, output_dir)
            write_index(output_dir, "Graphic Title", "by Pausanias", pages, "book.pdf")

            index_html = (output_dir / "index.html").read_text(encoding="utf-8")
            passage_html = (output_dir / "1" / "1" / "3.html").read_text(encoding="utf-8")

            self.assertIn('href="1/1/3.html"', index_html)
            self.assertNotIn('class="graphic-page"', index_html)
            self.assertIn("Passage 1.1.3 (1 of 2)", passage_html)
            self.assertIn('href="4.html"', passage_html)
            self.assertIn('src="../../images/1/1/3.png?', passage_html)
            self.assertIn('href="../../../translation/1/1/3.html"', passage_html)

    def test_translation_pages_link_to_graphic_page_when_image_exists(self):
        with TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            output_dir = root / "site"
            image_dir = root / "graphic-images"
            (output_dir / "css").mkdir(parents=True)
            (image_dir / "1" / "1").mkdir(parents=True)
            (image_dir / "1" / "1" / "3.png").write_bytes(b"fake image")

            passages = [
                {
                    "id": "1.1.3",
                    "greek": "Greek text 3",
                    "english": "English text 3",
                    "is_mythic": None,
                    "is_skeptical": None,
                },
                {
                    "id": "1.1.4",
                    "greek": "Greek text 4",
                    "english": "English text 4",
                    "is_mythic": None,
                    "is_skeptical": None,
                },
            ]

            generate_translation_pages(
                passages,
                nouns_by_passage={},
                noun_passages={},
                output_dir=output_dir,
                title="Pausanias",
                graphic_book_image_dir=image_dir,
            )

            linked_html = (output_dir / "translation" / "1" / "1" / "3.html").read_text(
                encoding="utf-8"
            )
            unlinked_html = (output_dir / "translation" / "1" / "1" / "4.html").read_text(
                encoding="utf-8"
            )

            self.assertIn('href="../../../graphic-book/1/1/3.html"', linked_html)
            self.assertIn("Open graphic version of this passage", linked_html)
            self.assertNotIn("graphic-book/1/1/4.html", unlinked_html)
            self.assertNotIn("Open graphic version of this passage", unlinked_html)

    def test_translation_pages_link_to_grammar_page_when_parse_exists(self):
        with TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir) / "site"
            (output_dir / "css").mkdir(parents=True)

            passages = [
                {
                    "id": "1.1.3",
                    "greek": "Greek text 3",
                    "english": "English text 3",
                    "is_mythic": None,
                    "is_skeptical": None,
                },
                {
                    "id": "1.1.4",
                    "greek": "Greek text 4",
                    "english": "English text 4",
                    "is_mythic": None,
                    "is_skeptical": None,
                },
            ]

            generate_translation_pages(
                passages,
                nouns_by_passage={},
                noun_passages={},
                output_dir=output_dir,
                title="Pausanias",
                grammar_passage_ids={"1.1.3"},
            )

            linked_html = (output_dir / "translation" / "1" / "1" / "3.html").read_text(
                encoding="utf-8"
            )
            unlinked_html = (output_dir / "translation" / "1" / "1" / "4.html").read_text(
                encoding="utf-8"
            )

            self.assertIn('href="../../../grammar/1/1/3.html"', linked_html)
            self.assertIn("Open grammar parses for this passage", linked_html)
            self.assertNotIn("grammar/1/1/4.html", unlinked_html)
            self.assertNotIn("Open grammar parses for this passage", unlinked_html)

    def test_translation_pages_do_not_show_passage_classifier_badges(self):
        with TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir) / "site"
            (output_dir / "css").mkdir(parents=True)

            passages = [
                {
                    "id": "1.1.3",
                    "greek": "Greek text 3",
                    "english": "English text 3",
                    "is_mythic": True,
                    "is_skeptical": False,
                },
            ]

            generate_translation_pages(
                passages,
                nouns_by_passage={},
                noun_passages={},
                output_dir=output_dir,
                title="Pausanias",
            )

            passage_html = (output_dir / "translation" / "1" / "1" / "3.html").read_text(
                encoding="utf-8"
            )

            self.assertNotIn("classification-badges", passage_html)
            self.assertNotIn("badge-mythic", passage_html)
            self.assertNotIn("Mythic", passage_html)
            self.assertNotIn("Non-skeptical", passage_html)

    def test_generates_passage_level_grammar_pages(self):
        with TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir) / "site"
            (output_dir / "css").mkdir(parents=True)
            grammar_data = {
                "model": "gpt-5.4-mini",
                "passages": [
                    {
                        "passage_id": "1.1.3",
                        "book": 1,
                        "chapter": 1,
                        "section": 3,
                        "input_tokens": 12,
                        "output_tokens": 34,
                        "token_count": 2,
                        "sentences": [
                            {
                                "passage_id": "1.1.3",
                                "sentence_number": 1,
                                "greek_sentence": "λέγει .",
                                "sentence_note": "Simple finite predicate.",
                                "input_tokens": 12,
                                "output_tokens": 34,
                                "tokens": [
                                    {
                                        "token_order": 1,
                                        "token_id": "1",
                                        "form": "λέγει",
                                        "lemma": "λέγω",
                                        "upos": "VERB",
                                        "xpos": "v3spia---",
                                        "feats_raw": "Mood=Ind",
                                        "head_token_id": "0",
                                        "deprel": "root",
                                        "confidence": "high",
                                        "note": "",
                                    },
                                    {
                                        "token_order": 2,
                                        "token_id": "2",
                                        "form": ".",
                                        "lemma": ".",
                                        "upos": "PUNCT",
                                        "xpos": "_",
                                        "feats_raw": "_",
                                        "head_token_id": "1",
                                        "deprel": "punct",
                                        "confidence": "high",
                                        "note": "",
                                    },
                                ],
                            }
                        ],
                    }
                ],
                "passage_ids": {"1.1.3"},
                "sentence_count": 1,
                "token_count": 2,
                "input_tokens": 12,
                "output_tokens": 34,
                "prompt_versions": ["greek-sentence-grammar-v1"],
                "created_at_min": "2026-06-13T00:00:00+00:00",
                "created_at_max": "2026-06-13T00:00:00+00:00",
            }

            generate_llm_grammar_pages(grammar_data, output_dir, "Pausanias")

            index_html = (output_dir / "grammar" / "index.html").read_text(encoding="utf-8")
            passage_html = (output_dir / "grammar" / "1" / "1" / "3.html").read_text(
                encoding="utf-8"
            )

            self.assertIn("gpt-5.4-mini", index_html)
            self.assertIn('href="1/index.html"', index_html)
            self.assertIn("grammar-parse-tree", passage_html)
            self.assertIn("grammar-token-table", passage_html)
            self.assertIn('href="../../../translation/1/1/3.html"', passage_html)


if __name__ == "__main__":
    unittest.main()

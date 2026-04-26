import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from build_graphic_book import build_pages, write_index
from website.generators import generate_translation_pages


class GraphicBookReaderTests(unittest.TestCase):
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


if __name__ == "__main__":
    unittest.main()

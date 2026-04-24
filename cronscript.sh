#!/bin/sh

cd $(dirname $0)
git pull -q

PAUSANIAS_QUIET_EMPTY=1 uv run mythic_sceptic_analyser.py --stop 50
PAUSANIAS_QUIET_EMPTY=1 uv run extract_proper_nouns.py --stop 50
uv run link_wikidata.py --stop-after 100
uv run translate_pausanias.py --stop 50
uv run split_sentences.py --stop 20
uv run summarise_passages.py --stop-after 50
uv run find_predictors.py
uv run find_sentence_predictors.py
uv run analyse_noun_network.py 
uv run sentence_mythic_sceptic_analyser.py --stop 25
uv run create_website.py
GRAPHIC_BOOK_IMAGE_DIR="${GRAPHIC_BOOK_IMAGE_DIR:-$HOME/pausanias-graphic-book/images}"
if [ ! -d "$GRAPHIC_BOOK_IMAGE_DIR" ]; then
  GRAPHIC_BOOK_IMAGE_DIR="graphic_book/images"
fi
uv run build_graphic_book.py --image-dir "$GRAPHIC_BOOK_IMAGE_DIR" --output-dir pausanias_site/graphic-book
rsync -az pausanias_site/ merah:/var/www/vhosts/pausanias.symmachus.org/htdocs/
rsync -az pausanias.sqlite merah:/var/www/vhosts/pausanias.symmachus.org/htdocs/

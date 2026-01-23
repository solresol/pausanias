#!/bin/sh

cd $(dirname $0)
git pull -q

uv run mythic_sceptic_analyser.py --stop 50
uv run extract_proper_nouns.py --stop 50
uv run link_wikidata.py --stop-after 100
uv run translate_pausanias.py --stop 50
uv run split_sentences.py --stop 5
uv run summarise_passages.py --stop-after 50
uv run find_predictors.py
uv run find_sentence_predictors.py
uv run analyse_noun_network.py 
uv run sentence_mythic_sceptic_analyser.py --stop 25
uv run create_website.py
rsync -avz pausanias_site/ merah:/var/www/vhosts/pausanias.symmachus.org/htdocs/
rsync -avz pausanias.sqlite merah:/var/www/vhosts/pausanias.symmachus.org/htdocs/

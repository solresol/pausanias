#!/bin/sh

cd $(dirname $0)

uv run mythic_sceptic_analyser.py --stop 50
uv run extract_proper_nouns.py --stop 50
uv run translate_pausanias.py --stop 50
uv run find_predictors.py
uv run create_website.py
rsync -avz pausanias_site/ merah:/var/www/vhosts/pausanias.symmachus.org/htdocs/

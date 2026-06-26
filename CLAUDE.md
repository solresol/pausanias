# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

Digital-humanities tooling over the Greek text of Pausanias' *Ἑλλάδος Περιήγησις*
(*Description of Greece*). Scripts import the corpus, use LLMs to classify and
translate it, run statistical/network analyses, and generate a static website
plus a graphic book. The research goal is stylometric and content analysis —
e.g. how "mythic" vs. historical and how skeptical each passage/sentence is, and
testing whether sections like Book 4 (Messenian Wars) are stylistic outliers.
See `TODO.md` for the live research agenda.

## Running scripts

- Use `uv run` — never bare `python`. Scripts are runnable directly:
  `uv run extract_proper_nouns.py`. Do not use `uv run python script.py`.
- Manage dependencies with `uv add` / `uv remove`; commit the resulting
  `pyproject.toml` and `uv.lock`. There is no `requirements.txt` and none is wanted.
- Most pipeline scripts accept `--stop=N` / `--stop-after=N` to process only N
  items — use this for cheap, partial runs (LLM calls cost money/tokens).
- Run tests with `uv run pytest` (or a single file: `uv run pytest tests/test_lemma_text.py`).

## Database

PostgreSQL, `dbname=pausanias`, user `gregb`. The **live** database is on
`raksasa`; the local default only works if a local server is running.

- Connection is resolved by `pausanias_db.get_database_url()`:
  `--database-url` arg → `PAUSANIAS_DATABASE_URL` → `DATABASE_URL` → `dbname=pausanias`.
- For local work against the live DB, open an SSH tunnel to raksasa's socket and
  point scripts at it:
  ```
  ssh -N -L 6543:/var/run/postgresql/.s.PGSQL.5432 raksasa
  uv run some_script.py --database-url "host=127.0.0.1 port=6543 dbname=pausanias user=gregb"
  ```
- Canonical schema is `database/schema.sql` (~60 tables, all `CREATE TABLE IF NOT
  EXISTS`); `pausanias_db.initialize_schema()` applies it. Shared helpers
  (`connect`, `read_sql_query`, `add_database_argument`, `table_exists`,
  `column_exists`) live in `pausanias_db.py` — reuse them instead of reconnecting ad hoc.
- Greg dislikes using PostgreSQL `JSON` or `JSONB` as an application-data escape
  hatch. Do not add new JSON/JSONB columns, JSONB staging CTEs, or
  `jsonb_to_recordset` write paths unless he explicitly approves that design.
  Prefer normal relational tables with typed columns, foreign keys, and indexes;
  use child tables or typed raw-text columns for variable key/value data.
- The root `pausanias.sqlite` is a legacy artifact; `migrate_sqlite_to_postgres.py`
  was the one-time migration. Current work is Postgres-only.

## LLM usage

Scripts call OpenAI (the `openai` package) for classification, translation,
sentence splitting, lemmatization, and tagging. Models are passed via flags
(e.g. `--model gpt-5.4-mini`). Heavier passes use OpenAI's **batch API** (see
`sentence_tag_batch.py`, which submits batches and polls with `--fetch-batches`).
Token spend is tracked in per-task tables (e.g. `content_queries`). Requires an
OpenAI API key in the environment.

## Pipeline / data flow

The daily pipeline is `cronscript.sh` (run via `./cronscript.sh`); its order is
the authoritative dependency graph:

1. `pausanias_importer.py <text>` — load passages into the `passages` table.
2. `mythic_sceptic_analyser.py` — LLM labels each passage mythic / skeptical.
3. `extract_proper_nouns.py` → `link_wikidata.py` — find proper nouns, link to Wikidata.
4. `translate_pausanias.py` — English translations.
5. `split_sentences.py` — split passages into aligned Greek/English sentences.
6. `summarise_passages.py` — passage summaries.
7. `find_predictors.py` / `find_sentence_predictors.py` — train TF-IDF predictor
   models for mythicness & skepticism at passage and sentence level.
8. `analyse_noun_network.py` — proper-noun co-occurrence network + centrality.
9. `sentence_tagging_daily.sh` → `sentence_tag_batch.py` — batch sentence tagging
   (Greta ontology modes: `greta`, `greta-both-context`, `legacy`).
10. `create_website.py` + `build_graphic_book.py` — generate the static site into
    `pausanias_site/`, then `rsync` to `merah` (the web host, behind Cloudflare).

Supporting tools not in the daily run: `check_proper_noun_spellings.py` (spelling
policy review/apply), `add_proper_nouns_to_stopwords.py`, `sentence_lemmatizer.py`
/ `word_lemmatizer.py`, `import_manual_sentence_tags.py`, `phrase_translator.py`,
`generate_latex_book.py`.

## Stopwords (affects the predictor models)

Proper nouns can leak into TF-IDF models. Exclude them via DB tables:
- `manual_stopwords` — combined with the proper-noun list for the **mythicness** model.
- `manual_skepticism_stopwords` — applied only to passage/sentence **skepticism** models.
```
psql "$PAUSANIAS_DATABASE_URL" -c "INSERT INTO manual_stopwords(word) VALUES ('Athens') ON CONFLICT DO NOTHING;"
```

## Output / deployment

- Generated site: `pausanias_site/` → rsynced to
  `merah:/var/www/vhosts/pausanias.symmachus.org/htdocs/`.
- Finished graphic-book pages live outside the repo and sync via
  `sync_graphic_book_images.sh [push|pull]` (rsync to raksasa, optional S3).
- Graphic-book source/component image binaries are an S3-backed local cache
  managed by `sync_graphic_book_assets.sh [push|pull|verify]`; keep prompt text,
  page plans, render scripts, and `graphic_book/assets/manifest.jsonl` in Git,
  but do not track `graphic_book/assets/generated/**/*.png|jpg|jpeg|webp`.

## Code style

- snake_case; standard-library imports first, then third-party; docstrings on functions.
- Python 3.11+. Follow existing explicit-error-message patterns.
- Add tests under `tests/` for new features; exercise them with the `--stop` flag on limited data.

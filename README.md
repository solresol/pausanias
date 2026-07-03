# pausanias

Digital humanities tools for manipulating the text of Ἑλλάδος Περιήγησις

# Tooling

All the programs use Python. Lots of digital humanities folks run into
trouble with environments and dependencies, so I've made sure
everything works nicely with `uv`. Download `uv` from here:
https://github.com/astral-sh/uv (it's one command, so it's quick, and
it won't disrupt any other installation you might have).

The first time you run a `uv` command it will output something like this:

```
Using CPython 3.11.6 interpreter at: /Users/gregb/anaconda3/bin/python3.11
Creating virtual environment at: .venv
```



# Data Loading

`uv run pausanias_importer.py description_of_greece.txt`

This should respond with 

```
Successfully imported 3170 passages into PostgreSQL
```

# Daily

I didn't have enough token allocation to run the whole corpus in one go, so
I broke it up into smaller chunks. Schedule `cronscript.sh` (and alter the
`--stop` parameter smaller if you have less allocation than me, or increase
it if you don't mind spending money).


## Manual stop words

Some words that are really proper nouns might slip past the automated
extractor. To make sure they don't influence the TF‑IDF model, you can add
them to a `manual_stopwords` table in the database:

```bash
psql "$PAUSANIAS_DATABASE_URL" -c "INSERT INTO manual_stopwords(word) VALUES ('Athens') ON CONFLICT DO NOTHING;"
```

When `find_predictors.py` runs it combines these entries with the proper
noun list and uses the union as stop words for the mythicness model.

For skepticism-specific exclusions, use `manual_skepticism_stopwords`
instead. These entries are applied only to the passage- and sentence-level
skepticism models, so they will not affect mythicness:

```bash
psql "$PAUSANIAS_DATABASE_URL" -c "INSERT INTO manual_skepticism_stopwords(word) VALUES ('δοκεῖν') ON CONFLICT DO NOTHING;"
```

## Proper noun spelling checks

The live PostgreSQL database is on `raksasa`, so local checking usually needs an
SSH tunnel:

```bash
ssh -N -L 6543:/var/run/postgresql/.s.PGSQL.5432 raksasa
```

Then run the spelling checker against the tunnel:

```bash
uv run check_proper_noun_spellings.py \
  --database-url "host=127.0.0.1 port=6543 dbname=pausanias user=gregb"
```

The checker stores reviewed spelling policies in
`proper_noun_spelling_policies` and scan results in
`proper_noun_spelling_findings`. Use `--apply` to replace deprecated variants in
completed translation text, sentence text, and passage summaries.

To import the review report as policies, apply corrections, and keep the proper
noun registry in step with the selected spellings:

```bash
uv run check_proper_noun_spellings.py \
  --database-url "host=127.0.0.1 port=6543 dbname=pausanias user=gregb" \
  --import-review-tsv tmp/proper_noun_spelling_review.tsv \
  --apply \
  --sync-registry \
  --sync-derived-name-spellings
```

The review importer chooses the dominant completed-prose spelling for each
entity, with a small set of explicit overrides where a base name and compound
name would otherwise fight each other.

## MANTO import and place-survival modelling

MANTO is imported from the public Zenodo data release rather than scraped from
the browser interface. The raw ZIP stays out of Git under `tmp/manto-releases/`.

Check the latest public release:

```bash
uv run manto_release_check.py --json
```

Download and record the release locally:

```bash
uv run manto_release_check.py --download --record-known
```

Import the cached release into PostgreSQL:

```bash
uv run manto_importer.py
```

The importer stores raw CSV/JSON row summaries in `manto_raw_records`, then
builds best-effort `manto_entities`, typed `manto_entity_details`,
`manto_tie_details`, and `manto_edges`. It derives Pausanias place-survival
labels in `manto_place_status_labels` from MANTO's entity `Information` field
for places linked to Pausanias tie records.

For prediction, use the strict pre-Pausanias graph only:
`manto_edges.is_pre_pausanias = TRUE`. Edges from Pausanias, sources dated to
Pausanias or later, and unknown-date sources are excluded from the default
modelling graph to avoid leaking both Pausanias' own evidence and future
evidence.

Build MANTO network features for the labelled Pausanias places and train the
first explainable model:

```bash
uv run manto_place_network_features.py
uv run predict_place_survival.py
```

The archived sentence-level LLM `place-state` sweep is historical evidence, not
the active sweep. To recover archived Batch API outputs for review or candidate
generation, use:

```bash
uv run recover_place_state_outputs.py
```

The active LLM sweep is passage-level, because a single sentence often lacks
enough context and one passage may contain multiple place claims. Refresh
deterministic candidate hints, submit passage-level batches, and fetch completed
runs with:

```bash
uv run place_state_candidate_importer.py
uv run passage_place_state_batch.py --use-batch-api --candidate-first --token-budget 1000000
uv run passage_place_state_batch.py --fetch-batches
```

`passage_place_state_daily.sh` runs those steps with a one-million-token daily
planning budget and is called by `cronscript.sh`.

## UDPipe grammar annotations

Sentence-level grammar annotations are stored separately from the LLM
lemmatization tables. The UDPipe runner reads `greek_sentences`, stores full
CoNLL-U output in `sentence_udpipe_analyses`, and stores queryable token-level
lemma, UPOS, morphology, head, and dependency labels in
`sentence_udpipe_tokens`.

The default model is `ancient_greek-perseus-ud-2.5-191206`, downloaded into the
ignored `models/udpipe/` cache when missing:

```bash
uv run python sentence_udpipe.py --ssh-host raksasa
```

Useful smaller checks:

```bash
uv run python sentence_udpipe.py --ssh-host raksasa --stop-after 1 --dry-run \
  --output-json tmp/udpipe-dry-run.json

uv run python sentence_udpipe.py --ssh-host raksasa --schema-only
```

## Trankit OGA grammar annotations

For higher-accuracy Ancient Greek dependency parsing, use Celano's Trankit
Ancient Greek model. It reports AGDT-style morphosyntax and dependency labels,
not Universal Dependencies, so the output is kept in separate
`sentence_trankit_runs`, `sentence_trankit_analyses`, and
`sentence_trankit_tokens` tables.

The model cache lives outside git under `models/trankit-oga/`. The bundled
Trankit source currently needs an isolated Python 3.10 runtime and pinned ML
dependencies:

```bash
PYTHONPATH=models/trankit-oga/trankit-master \
uv run --no-project --python 3.10 \
  --with adapters==0.1.1 \
  --with transformers==4.35.2 \
  --with huggingface-hub==0.20.3 \
  --with langid==1.1.6 \
  --with sentencepiece \
  --with 'torch>=1.6.0,<=2.0.1' \
  --with 'numpy<2' \
  --with six \
  python sentence_trankit.py --ssh-host raksasa --parse-batch-size 16 --write-batch-size 64
```

Useful smaller checks:

```bash
uv run python sentence_trankit.py --ssh-host raksasa --schema-only

PYTHONPATH=models/trankit-oga/trankit-master \
uv run --no-project --python 3.10 \
  --with adapters==0.1.1 \
  --with transformers==4.35.2 \
  --with huggingface-hub==0.20.3 \
  --with langid==1.1.6 \
  --with sentencepiece \
  --with 'torch>=1.6.0,<=2.0.1' \
  --with 'numpy<2' \
  --with six \
  python sentence_trankit.py --ssh-host raksasa --stop-after 1 --dry-run \
    --output-json tmp/trankit-dry-run.json
```

This model does not supply lemmas in its CoNLL-U output; `lemma` is therefore
nullable in the Trankit token table. Keep using the separate lemmatization tables
for lemma-focused work.

## LLM grammar annotations

The LLM grammar runner asks `gpt-5.4-mini` for parser-style token annotations:
lemma, UPOS, detailed morphology, UD-style features, head token, and dependency
relation. Results are stored separately from deterministic parser output in
`sentence_llm_grammar_runs`, `sentence_llm_grammar_analyses`, and
`sentence_llm_grammar_tokens`.

Run a deterministic 20-sentence sample:

```bash
uv run python sentence_llm_grammar.py --ssh-host raksasa \
  --sample-size 20 \
  --sample-seed sentence-llm-grammar-20-v1 \
  --output-json tmp/llm-grammar-20.json
```

The script validates each response before storing it: token count, token forms,
UPOS tags, and dependency heads must align with the input token list.

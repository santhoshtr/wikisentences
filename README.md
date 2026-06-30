# Wikisentences

Extract sentences from all Wikipedia content in all languages and publish as dataset.

## Core technology

- [wikipedia-article-transform](https://github.com/santhoshtr/wikipedia-article-transform) (Rust/Python) — parses article HTML using tree-sitter-html and extracts plain text
- sentencex (Rust) — sentence segmentation

## Pipeline stages

1. Download enterprise HTML dumps from `https://dumps.wikimedia.org/other/enterprise_html/runs/20250320/` (replace language code as needed)
2. Parse the NDJSON (schema: [Wikimedia Enterprise data dictionary](https://enterprise.wikimedia.com/docs/data-dictionary/)) and save as `data/<lang>.html.parquet` — columns: `id, name, url, language, html`
3. Extract plain text from the `html` column via `wikipedia-article-transform` and save as `data/<lang>.text.parquet` — columns: `id, url, name, text`
4. Segment text into sentences using sentencex and save as `data/<lang>.sentences.parquet` — columns: `id, url, name, sentence, sentence_index`

Stages 1–2 are handled by `scripts/json_to_parquet.py`.
Stage 3 is handled by `scripts/html_to_text_parquet.py`.
Stage 4 is handled by `scripts/text_to_sentences_parquet.py`.

## Usage

```sh
# Stage 2: JSON dump → html parquet (streams, no extraction to disk)
uv run scripts/json_to_parquet.py dumps/enterprise_html/mlwiki-NS0-20250320-ENTERPRISE-HTML.json.tar.gz data/ml.html.parquet

# Stage 3: html parquet → text parquet (~8 min for ml, 88K articles)
uv run scripts/html_to_text_parquet.py data/ml.html.parquet data/ml.text.parquet

# Stage 4: text parquet → sentences parquet (~18s for ml, 2.25M sentences)
uv run scripts/text_to_sentences_parquet.py ml data/ml.text.parquet data/ml.sentences.parquet

# Or drive all stages via make
make data/ml.sentences.parquet
```

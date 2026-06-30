# /// script
# requires-python = ">=3.9"
# dependencies = [
#   "pyarrow>=15.0.0",
#   "tqdm>=4.0.0",
#   "wikipedia-article-transform>=0.4.0",
# ]
# ///

"""
Read an *.html.parquet file, extract plain text from each row's HTML using
wikipedia-article-transform, and write the results to a *.text.parquet file.

Usage:
    uv run scripts/html_to_text_parquet.py <input.html.parquet> <output.text.parquet>
"""

import os
import sys

import pyarrow as pa
import pyarrow.parquet as pq
from tqdm import tqdm
from wikipedia_article_transform import extract_plain

BATCH_SIZE = 500

OUTPUT_SCHEMA = pa.schema(
    [
        pa.field("id", pa.int64(), nullable=True),
        pa.field("url", pa.string(), nullable=True),
        pa.field("name", pa.string(), nullable=True),
        pa.field("text", pa.string(), nullable=True),
    ]
)


def run(input_parquet: str, output_parquet: str) -> None:
    table = pq.read_table(input_parquet, columns=["id", "url", "name", "html"])
    total = len(table)

    ids = table["id"].to_pylist()
    urls = table["url"].to_pylist()
    names = table["name"].to_pylist()
    htmls = table["html"].to_pylist()

    os.makedirs(os.path.dirname(os.path.abspath(output_parquet)), exist_ok=True)
    writer = pq.ParquetWriter(output_parquet, OUTPUT_SCHEMA)

    batch: list[dict] = []

    def flush_batch() -> None:
        if not batch:
            return
        writer.write_table(pa.Table.from_pylist(batch, schema=OUTPUT_SCHEMA))
        batch.clear()

    with tqdm(total=total, unit="articles") as bar:
        for id_, url, name, html in zip(ids, urls, names, htmls):
            text = extract_plain(html or "")
            batch.append(
                {"id": id_, "url": url or "", "name": name or "", "text": text}
            )
            if len(batch) >= BATCH_SIZE:
                flush_batch()
            bar.update(1)

    flush_batch()
    writer.close()
    print(f"Done. Wrote {total} rows to {output_parquet}")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print(
            "Usage: python html_to_text_parquet.py <input.html.parquet> <output.text.parquet>",
            file=sys.stderr,
        )
        sys.exit(1)
    run(sys.argv[1], sys.argv[2])

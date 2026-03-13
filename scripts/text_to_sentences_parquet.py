# /// script
# requires-python = ">=3.9"
# dependencies = [
#   "pyarrow>=15.0.0",
#   "sentencex>=1.0.0",
#   "tqdm>=4.0.0",
# ]
# ///

"""
Segment article text from a *.text.parquet file into sentences and write
a *.sentences.parquet file with one sentence per row.

Output schema: id (int64), url (string), name (string),
               sentence (string), sentence_index (int32)

Usage:
    uv run scripts/text_to_sentences_parquet.py <lang> <input.text.parquet> <output.sentences.parquet>
"""

import os
import sys

import pyarrow as pa
import pyarrow.parquet as pq
from sentencex import segment
from tqdm import tqdm

BATCH_SIZE = 5000

OUTPUT_SCHEMA = pa.schema(
    [
        pa.field("id", pa.int64(), nullable=True),
        pa.field("url", pa.string(), nullable=True),
        pa.field("name", pa.string(), nullable=True),
        pa.field("sentence", pa.string(), nullable=False),
        pa.field("sentence_index", pa.int32(), nullable=False),
    ]
)


def run(lang: str, input_parquet: str, output_parquet: str) -> None:
    table = pq.read_table(input_parquet, columns=["id", "url", "name", "text"])
    total_articles = len(table)

    os.makedirs(os.path.dirname(os.path.abspath(output_parquet)), exist_ok=True)
    writer = pq.ParquetWriter(output_parquet, OUTPUT_SCHEMA)

    batch: list[dict] = []
    total_sentences = 0

    def flush_batch() -> None:
        if not batch:
            return
        writer.write_table(pa.Table.from_pylist(batch, schema=OUTPUT_SCHEMA))
        batch.clear()

    with tqdm(total=total_articles, unit="articles") as bar:
        for row in table.to_pylist():
            text = row["text"] or ""
            count = 0
            try:
                sentences = list(segment(lang, text))
            except BaseException as e:
                print(
                    f"\nWarning: segmentation failed for id={row['id']} ({row['name']!r}): {e}",
                    file=sys.stderr,
                )
                bar.update(1)
                continue
            for i, sentence in enumerate(sentences):
                sentence = sentence.strip()
                if not sentence:
                    continue
                batch.append(
                    {
                        "id": row["id"],
                        "url": row["url"],
                        "name": row["name"],
                        "sentence": sentence,
                        "sentence_index": i,
                    }
                )
                if len(batch) >= BATCH_SIZE:
                    flush_batch()
                count += 1
            total_sentences += count
            bar.update(1)

    flush_batch()
    writer.close()
    print(
        f"Done. {total_articles} articles → {total_sentences} sentences → {output_parquet}"
    )


if __name__ == "__main__":
    if len(sys.argv) != 4:
        print(
            "Usage: python text_to_sentences_parquet.py <lang> <input.text.parquet> <output.sentences.parquet>",
            file=sys.stderr,
        )
        sys.exit(1)
    run(sys.argv[1], sys.argv[2], sys.argv[3])

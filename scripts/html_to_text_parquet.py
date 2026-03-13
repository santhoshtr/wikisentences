# /// script
# requires-python = ">=3.9"
# dependencies = [
#   "pyarrow>=15.0.0",
#   "tqdm>=4.0.0",
# ]
# ///

"""
Read an *.html.parquet file, pipe each row's HTML through the Rust
wiki-html-text-extractor binary via line-delimited JSON on stdin/stdout,
and write the results to a *.text.parquet file.

Usage:
    uv run scripts/html_to_text_parquet.py <input.html.parquet> <output.text.parquet> <extractor-binary>
"""

import json
import os
import subprocess
import sys
import threading
from queue import Queue

import pyarrow as pa
import pyarrow.parquet as pq
from tqdm import tqdm

BATCH_SIZE = 500
# Sentinel to signal the reader thread that writing is done
_DONE = object()

OUTPUT_SCHEMA = pa.schema(
    [
        pa.field("id", pa.int64(), nullable=True),
        pa.field("url", pa.string(), nullable=True),
        pa.field("name", pa.string(), nullable=True),
        pa.field("text", pa.string(), nullable=True),
    ]
)


def _writer_thread(proc_stdin, rows):
    """Feed all rows as line-delimited JSON to the Rust process stdin."""
    try:
        for row in rows:
            line = json.dumps(row, ensure_ascii=False)
            proc_stdin.write(line + "\n")
        proc_stdin.flush()
    finally:
        proc_stdin.close()


def run(input_parquet: str, output_parquet: str, extractor_bin: str) -> None:
    table = pq.read_table(input_parquet, columns=["id", "url", "name", "html"])
    total = len(table)

    os.makedirs(os.path.dirname(os.path.abspath(output_parquet)), exist_ok=True)
    writer = pq.ParquetWriter(output_parquet, OUTPUT_SCHEMA)

    proc = subprocess.Popen(
        [extractor_bin, "stdin"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=sys.stderr,
        text=True,
        # Default (full) buffering for stdin/stdout — avoids deadlock
    )

    rows = [
        {
            "id": ids,
            "url": urls or "",
            "name": names or "",
            "html": html or "",
        }
        for ids, urls, names, html in zip(
            table["id"].to_pylist(),
            table["url"].to_pylist(),
            table["name"].to_pylist(),
            table["html"].to_pylist(),
        )
    ]

    # Write to stdin in a background thread so the main thread can drain stdout
    t = threading.Thread(target=_writer_thread, args=(proc.stdin, rows), daemon=True)
    t.start()

    batch: list[dict] = []

    def flush_batch() -> None:
        if not batch:
            return
        out_table = pa.Table.from_pylist(batch, schema=OUTPUT_SCHEMA)
        writer.write_table(out_table)
        batch.clear()

    with tqdm(total=total, unit="articles") as bar:
        for line in proc.stdout:
            line = line.strip()
            if not line:
                continue
            try:
                result = json.loads(line)
            except json.JSONDecodeError as e:
                print(f"Warning: bad JSON from extractor: {e}", file=sys.stderr)
                continue

            batch.append(
                {
                    "id": result.get("id"),
                    "url": result.get("url"),
                    "name": result.get("name"),
                    "text": result.get("text"),
                }
            )
            if len(batch) >= BATCH_SIZE:
                flush_batch()
            bar.update(1)

    t.join()
    proc.wait()
    flush_batch()
    writer.close()

    if proc.returncode != 0:
        print(f"Extractor exited with code {proc.returncode}", file=sys.stderr)
        sys.exit(1)

    print(f"Done. Wrote {total} rows to {output_parquet}")


if __name__ == "__main__":
    if len(sys.argv) != 4:
        print(
            "Usage: python html_to_text_parquet.py <input.html.parquet> <output.text.parquet> <extractor-binary>",
            file=sys.stderr,
        )
        sys.exit(1)
    run(sys.argv[1], sys.argv[2], sys.argv[3])

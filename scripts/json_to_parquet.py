# /// script
# requires-python = ">=3.9"
# dependencies = [
#   "pyarrow>=15.0.0",
# ]
# ///

import json
import sys
import os
import tarfile
import pyarrow as pa
import pyarrow.parquet as pq


def process_tar_gz(tar_gz_path, output_parquet):
    """
    Stream a tar.gz file containing .ndjson files, extract specific fields,
    and write to a Parquet file.
    """
    # Define the schema for the output Parquet file with nullable fields
    schema = pa.schema(
        [
            pa.field("id", pa.int64(), nullable=True),
            pa.field("name", pa.string(), nullable=True),
            pa.field("url", pa.string(), nullable=True),
            pa.field("language", pa.string(), nullable=True),
            pa.field("html", pa.string(), nullable=True),
        ]
    )

    # Open the output Parquet writer
    os.makedirs(os.path.dirname(output_parquet), exist_ok=True)
    writer = pq.ParquetWriter(output_parquet, schema)

    batch_size = 1000  # Number of rows per batch
    batch = []

    # Helper function to write a batch and reset
    def write_batch():
        nonlocal batch, writer
        if batch:
            table = pa.Table.from_pylist(batch, schema=schema)
            writer.write_table(table)
            batch = []

    # Open the tar.gz file (or stdin if tar_gz_path is '-')
    if tar_gz_path == "-":
        # Read from stdin as a binary stream
        tar_stream = sys.stdin.buffer
    else:
        tar_stream = open(tar_gz_path, "rb")

    try:
        # Open the tar file from the stream
        with tarfile.open(fileobj=tar_stream, mode="r|gz") as tar:
            for member in tar:
                # We only care about regular files that end with .ndjson
                if member.isfile() and member.name.endswith(".ndjson"):
                    # Extract the file object
                    f = tar.extractfile(member)
                    if f is None:
                        continue
                    # Process each line in the .ndjson file
                    for line in f:
                        try:
                            record = json.loads(line.decode("utf-8").strip())
                            # Extract only the required fields
                            extracted = {
                                "id": record.get("identifier"),
                                "name": record.get("name"),
                                "url": record.get("url"),
                                "language": record.get("in_language", {}).get(
                                    "identifier"
                                ),
                                "html": record.get("article_body", {}).get("html"),
                            }
                            batch.append(extracted)
                            if len(batch) >= batch_size:
                                write_batch()
                        except (
                            json.JSONDecodeError,
                            UnicodeDecodeError,
                            KeyError,
                        ) as e:
                            # Skip malformed lines
                            print(
                                f"Warning: Skipping invalid line in {member.name}: {e}",
                                file=sys.stderr,
                            )
                            continue
                    f.close()
    finally:
        if tar_gz_path != "-":
            tar_stream.close()
        write_batch()  # Write any remaining records
        writer.close()


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python json_to_parquet.py <input_tar_gz_or_-> <output_parquet>")
        sys.exit(1)
    process_tar_gz(sys.argv[1], sys.argv[2])

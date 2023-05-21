## Usage


Clone the repo, create a virtual environment and install dependencies.

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .
```

Install fastttext

```bash
sudo apt install fasttext
```

Then run:

```bash
make
```

Note that downloading wikipedia dumps and processing for languages will take about 2 days and will use lot of diskspace. Use the fasttest machine you have. At the end the directory `data` will have `langcode.sentences.txt` files.

Once the sentences are prepared run `make ld.model.bin` to create fasttext model for language identification. This is also a long running process.



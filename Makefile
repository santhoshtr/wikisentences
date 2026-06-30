#!/usr/bin/make -f
SHELL:=/bin/bash
.ONESHELL: # Applies to every targets in the file!
DATA_DIR:=data

# Enterprise HTML dumps
ENTERPRISE_DUMP_URL_BASE := https://dumps.wikimedia.org/other/enterprise_html/runs/20250320
ENTERPRISE_DUMP_SUFFIX := -NS0-20250320-ENTERPRISE-HTML.json.tar.gz
enterprise_codes := $(shell sed 's/-/_/g' $(DATA_DIR)/wikipedia.list)
html_parquet := $(enterprise_codes:%=data/%.html.parquet)

text_parquet := $(enterprise_codes:%=data/%.text.parquet)
sentences_parquet := $(enterprise_codes:%=data/%.sentences.parquet)

all: $(dataset) datacleanup test $(sentences_parquet)


# Wikipedia list
$(DATA_DIR)/wikipedia.list: | $(DATA_DIR)
	@echo "Fetching Wikipedia list..."
	@mkdir -p $(DATA_DIR)
	@curl -fsSL https://noc.wikimedia.org/conf/dblists/closed.dblist > closed.dblist
	@curl -fsSL https://noc.wikimedia.org/conf/dblists/wikipedia.dblist \
		| grep -E 'wiki$$' \
		| grep -v '^#' \
		| grep -v -f closed.dblist > $@
	@sed -i '/^arbcom/d; /^test/d; /^sysop/d; /^wg_en/d; /^cebwiki/d; /^warwiki/d; /^be_x_old/d' $@
	@rm -f closed.dblist

# Download tar.gz dump (resume if partially downloaded)
dumps/enterprise_html/%-wiki$(ENTERPRISE_DUMP_SUFFIX):
	mkdir -p dumps/enterprise_html
	wget -c $(ENTERPRISE_DUMP_URL_BASE)/$*wiki$(ENTERPRISE_DUMP_SUFFIX) -O $@

# Convert to Parquet (idempotent) - streams the tar.gz directly, no extraction
data/%.html.parquet: dumps/enterprise_html/%-wiki$(ENTERPRISE_DUMP_SUFFIX)
	mkdir -p data
	uv run scripts/json_to_parquet.py $< $@

clean:
	@rm -rf data dumps

# Extract plain text from HTML parquet
data/%.text.parquet: data/%.html.parquet
	uv run scripts/html_to_text_parquet.py $< $@

# Segment text into sentences (language code extracted from filename)
data/%.sentences.parquet: data/%.text.parquet
	uv run scripts/text_to_sentences_parquet.py $* $< $@

#!/usr/bin/make -f
SHELL:=/bin/bash
.ONESHELL: # Applies to every targets in the file!

codes := $(shell cat wikis.txt)
dataset=$(codes:%=data/%.sentences.txt)

all: $(dataset)

dumps/%wiki-latest-pages-articles.xml:
	mkdir -p dumps
	cd dumps
	wget -c -N https://dumps.wikimedia.org/$*wiki/latest/$*wiki-latest-pages-articles.xml.bz2
	bunzip2 $*wiki-latest-pages-articles.xml.bz2
	cd ../

data/%: dumps/%wiki-latest-pages-articles.xml
	wikiextractor \
		--no-templates \
		--processes 4 \
		--bytes 10M \
		--output $@ \
		dumps/$*wiki-latest-pages-articles.xml

data/%.sentences.txt: data/%
	find data/$*  -name 'wiki_*' -type f -print0 | while read -d '' -r file; do \
		echo "Sentence segmenting $$file"; \
		awk NF "$$file" | sed '/^<doc/d; /^<\/doc/d' | python segmenter.py >> $@; \
	done;
	@rm -rf data/$*

clean:
	@rm -rf data dumps
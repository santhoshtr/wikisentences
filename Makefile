#!/usr/bin/make -f
SHELL:=/bin/bash
.ONESHELL: # Applies to every targets in the file!
# dumps uses _ instead of - in language codes
codes := $(shell sed 's/-/_/g' wikis.txt)
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

datacleanup:
	# General cleanup
	sed -i -E -f cleanup.sed ./data/*.sentences.txt
	# Remove English from non lating scripts
	./remove_english.sh

labels.txt: datacleanup
	./prepare_train_set.sh ./data/*.sentences.txt > $@
	@echo "Preparing train and testing splits"
	awk '{if(rand()<0.9) {print > "train.txt"} else {print > "valid.txt"}}' $@

ld.model.bin: labels.txt
	fasttext supervised \
		-input train.txt \
		-output ld.model \
		-epoch 25 \
		-lr 0.1 \
		-dim 16 \
		-minn 2 \
		-maxn 4 \
		-loss hs

ld.model.ftz: ld.model.bin
	fasttext quantize \
		-input train.txt \
		-output ld.model \
		-qnorm \
		-cutoff 50000 \
		-retrain


test: ld.model.bin ld.model.ftz
	# Test model
	fasttext test-label ld.model.bin valid.txt
	fasttext test-label ld.model.ftz valid.txt

clean:
	@rm -rf data dumps


#!/bin/bash
# Sample size - number of sentences per language
samplesize=100000 # One hundred thousands(1 lakh)
for file in "$@"; do
  num_lines=$(wc -l "$file" | awk '{print $1}')
  prefix=$(basename "$file" .sentences.txt)
  if [ $num_lines -le $samplesize ]; then
    cat "$file" | sed -e "s/\([.\!?,'/()]\)/ \1 /g" | tr "[:upper:]" "[:lower:]" | while read -r line; do
        echo -e "__label__${prefix}\t$line"
    done
  else
    shuf -n $samplesize "$file" | sed -e "s/\([.\!?,'/()]\)/ \1 /g" | tr "[:upper:]" "[:lower:]" | while read -r line; do
      echo -e "__label__${prefix}\t$line"
    done
  fi
done




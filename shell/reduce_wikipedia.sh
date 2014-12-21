#!/bin/bash
tr "/_.-" "    " < wordlists/raw/big/wikipedia_en_titles.txt | grep "^[^ ]" | grep -v "  " | LANG=C egrep "^[A-Za-z' ]+$" | tr a-z A-Z | sort | uniq > wordlists/wikipedia-en-titles.txt

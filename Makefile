PYTHON=python3
SEARCH_DIR=data/search
WORDLIST_DIR=data/wordlists
CORPUS_DIR=data/corpora

all: wordlists search

clean:
	rm $(WORDLIST_DIR)/*.txt
	rm -r $(SEARCH_DIR)

WORDLISTS = $(WORDLIST_DIR)/enable.txt $(WORDLIST_DIR)/twl06.txt \
	$(WORDLIST_DIR)/google-books.freq.txt \
	$(WORDLIST_DIR)/google-books-1grams.txt \
	$(WORDLIST_DIR)/google-books-1grams.freq.txt \
	$(WORDLIST_DIR)/google-books.txt \
	$(WORDLIST_DIR)/wikipedia-en-titles.txt \
	$(WORDLIST_DIR)/wordnet.txt \
	$(WORDLIST_DIR)/csw-apr07.txt \
	$(WORDLIST_DIR)/npl-allwords.txt

search: $(SEARCH_DIR)/_MAIN_1.toc

wordlists: $(WORDLISTS) $(WORDLIST_DIR)/combined.txt

$(WORDLIST_DIR)/google-books.freq.txt: $(WORDLIST_DIR)/raw/google-books-1grams.txt\
	$(WORDLIST_DIR)/raw/google-books-2grams.txt
	LC_ALL=C egrep -h "^[A-Z' ]+,[0-9]" $^ | sort -nrk 2 -t "," > $@

$(WORDLIST_DIR)/google-books.txt: $(WORDLIST_DIR)/google-books.freq.txt
	LC_ALL=C sort $< > $@

$(WORDLIST_DIR)/google-books-1grams.txt: $(WORDLIST_DIR)/raw/google-books-1grams.txt
	LC_ALL=C egrep -h "^[A-Z']+," $^ | sort > $@

$(WORDLIST_DIR)/google-books-1grams.freq.txt: $(WORDLIST_DIR)/google-books-1grams.txt
	sort -nrk 2 -t "," $< > $@

$(WORDLIST_DIR)/enable.txt: $(WORDLIST_DIR)/raw/enable.txt shell/freq1.sh
	tr a-z A-Z < $< | shell/freq1.sh > $@

$(WORDLIST_DIR)/csw-apr07.txt: $(WORDLIST_DIR)/raw/csw-apr07.txt shell/freq1.sh
	shell/freq1.sh < $< > $@

$(WORDLIST_DIR)/twl06.txt: $(WORDLIST_DIR)/raw/twl06.txt shell/freq1.sh
	tr a-z A-Z < $< | shell/freq1.sh > $@

$(WORDLIST_DIR)/wikipedia-en-titles.txt: $(WORDLIST_DIR)/raw/wikipedia-en-titles.txt
	egrep -hv " .* .* " $< | shell/freq1.sh > $@

$(WORDLIST_DIR)/wordnet.txt: $(WORDLIST_DIR)/raw/wordnet.txt
	LC_ALL=C egrep -h "^[A-Za-z0-9'/ -]+$$" $< | tr a-z A-Z | shell/freq1.sh > $@

$(WORDLIST_DIR)/npl-allwords.txt: $(WORDLIST_DIR)/raw/npl_allwords2.txt
	LC_ALL=C egrep -h "^[A-Za-z0-9' -]+$$" $< | tr a-z A-Z | shell/freq1.sh > $@

$(WORDLIST_DIR)/combined.txt: $(WORDLISTS) scripts/build_combined.py
	$(PYTHON) scripts/build_combined.py

$(SEARCH_DIR)/_MAIN_1.toc: scripts/build_search_index.py $(CORPUS_DIR)/crossword_clues.txt
	$(PYTHON) scripts/build_search_index.py

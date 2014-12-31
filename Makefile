PYTHON=python3

all: wordlists

clean:
	rm wordlists/*.txt

WORDLISTS = wordlists/enable.txt wordlists/twl06.txt \
	wordlists/google-books.freq.txt \
	wordlists/google-books-1grams.txt \
	wordlists/google-books-1grams.freq.txt \
	wordlists/google-books.txt \
	wordlists/wikipedia-en-titles.txt \
	wordlists/wordnet.txt \
	wordlists/npl-allwords.txt

wordlists: $(WORDLISTS) wordlists/combined.txt

wordlists/google-books.freq.txt: wordlists/raw/google-books-1grams.txt\
	wordlists/raw/google-books-2grams.txt
	LC_ALL=C egrep -h "^[A-Z' ]+,[0-9]" $^ | sort -nrk 2 -t "," > $@

wordlists/google-books.txt: wordlists/google-books.freq.txt
	LC_ALL=C sort $< > $@

wordlists/google-books-1grams.txt: wordlists/raw/google-books-1grams.txt
	LC_ALL=C egrep -h "^[A-Z']+," $^ | sort > $@

wordlists/google-books-1grams.freq.txt: wordlists/google-books-1grams.txt
	sort -nrk 2 -t "," $< > $@

wordlists/enable.txt: wordlists/raw/enable.txt shell/freq1.sh
	tr a-z A-Z < $< | shell/freq1.sh > $@

wordlists/twl06.txt: wordlists/raw/twl06.txt shell/freq1.sh
	tr a-z A-Z < $< | shell/freq1.sh > $@

wordlists/wikipedia-en-titles.txt: wordlists/raw/wikipedia-en-titles.txt
	egrep -hv " .* .* " $< | shell/freq1.sh > $@

wordlists/wordnet.txt: wordlists/raw/wordnet.txt
	LC_ALL=C egrep -h "^[A-Za-z0-9'/ -]+$$" $< | tr a-z A-Z | shell/freq1.sh > $@

wordlists/npl-allwords.txt: wordlists/raw/npl_allwords2.txt
	LC_ALL=C egrep -h "^[A-Za-z0-9' -]+$$" $< | tr a-z A-Z | shell/freq1.sh > $@

wordlists/combined.txt: $(WORDLISTS) scripts/build_combined.py
	$(PYTHON) scripts/build_combined.py


PYTHON=python3.3

all: wordlists

wordlists: wordlists/enable.txt wordlists/twl06.txt \
	wordlists/google-books.freq.txt \
	wordlists/google-books-1grams.txt \
	wordlists/google-books-1grams.freq.txt \
	wordlists/google-books.txt

env/bin/activate: py-requirements.txt
	test -d env || virtualenv --python=$(PYTHON) env
	. env/bin/activate ; pip install -U -r py-requirements.txt
	touch env/bin/activate

wordlists/google-books.freq.txt: wordlists/raw/google-books-1grams.txt\
	wordlists/raw/google-books-2grams.txt
	LC_ALL=C egrep -h "^[A-Z ]+," $^ | sort -nrk 2 -t "," > $@

wordlists/google-books.txt: wordlists/google-books.freq.txt
	LC_ALL=C sort $< > $@

wordlists/google-books-1grams.txt: wordlists/raw/google-books-1grams.txt
	LC_ALL=C egrep -h "^[A-Z]+," $^ | sort > $@

wordlists/google-books-1grams.freq.txt: wordlists/google-books-1grams.txt
	sort -nrk 2 -t "," $< > $@

wordlists/enable.txt: wordlists/raw/enable.txt shell/freq1.sh
	tr a-z A-Z < $< | shell/freq1.sh > $@

wordlists/twl06.txt: wordlists/raw/twl06.txt shell/freq1.sh
	tr a-z A-Z < $< | shell/freq1.sh > $@

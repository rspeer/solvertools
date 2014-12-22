PYTHON=python3.3

all: wordlists

clean:
	rm wordlists/*.txt

wordlists: wordlists/enable.txt wordlists/twl06.txt \
	wordlists/google-books.freq.txt \
	wordlists/google-books-1grams.txt \
	wordlists/google-books-1grams.freq.txt \
	wordlists/google-books.txt \
	wordlists/wikipedia-en-titles.txt \
	wordlists/npl-allwords.txt

env/bin/activate: py-requirements.txt
	test -d env || virtualenv --python=$(PYTHON) env
	. env/bin/activate ; pip install -U -r py-requirements.txt
	touch env/bin/activate

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

wordlists/npl-allwords.txt: wordlists/raw/npl_allwords2.txt
	LC_ALL=C egrep -h "^[A-Za-z0-9' -]+$$" $< | tr a-z A-Z | shell/freq1.sh > $@


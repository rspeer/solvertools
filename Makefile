all: wordlists/google-books.ascii.freq.txt wordlists/google-books.ascii.alph.txt wordlists/enable.txt

wordlists/google-books.ascii.freq.txt: wordlists/raw/google-books-1grams.txt
	LC_ALL=C egrep "^[A-Z]+\t" $< > $@

wordlists/google-books.ascii.alph.txt: wordlists/google-books.ascii.freq.txt
	LC_ALL=C sort $< > $@

wordlists/enable.txt: wordlists/raw/enable.txt
	tr a-z A-Z < $< | scripts/freq1.sh > $@

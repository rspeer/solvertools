all: wordlists/google-books.ascii.freq.txt wordlists/google-books.ascii.alph.txt wordlists/enable.txt \
	wordlists/twl06.txt

wordlists/google-books.ascii.freq.txt: wordlists/raw/google-books-1grams.txt
	LC_ALL=C egrep "^[A-Z]+\t" $< > $@

wordlists/google-books.ascii.alph.txt: wordlists/google-books.ascii.freq.txt
	LC_ALL=C sort $< > $@

wordlists/enable.txt: wordlists/raw/enable.txt
	tr a-z A-Z < $< | shell/freq1.sh > $@

wordlists/twl06.txt: wordlists/raw/twl06.txt
	tr a-z A-Z < $< | shell/freq1.sh > $@

doc: docs/SolverTools.html

docs/SolverTools.html: julia/SolverTools.jl jocco.jl
	julia jocco.jl julia/SolverTools.jl

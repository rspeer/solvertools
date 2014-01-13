PYTHON=python3.3

all: setup wordlists

setup: env/bin/activate .julia-setup.log .python-setup.log

.julia-setup.log: julia/setup.jl
	julia julia/setup.jl > .julia-setup.log

.python-setup.log: python/setup.py
	. env/bin/activate ; cd python ; python setup.py develop > ../.python-setup.log

wordlists: wordlists/enable.txt wordlists/twl06.txt \
	wordlists/google-books.freq.txt \
	wordlists/google-books-1grams.txt \
	wordlists/google-books.txt

env/bin/activate: py-requirements.txt
	test -d env || virtualenv --python=$(PYTHON) env
	. env/bin/activate ; pip install -U -r py-requirements.txt
	touch env/bin/activate

wordlists/google-books.freq.txt: wordlists/raw/google-books-1grams.txt\
	wordlists/raw/google-books-2grams.txt
	LC_ALL=C egrep -h "^[A-Z ]+	" $^ | sort -nrk 2 -t "	" > $@

wordlists/google-books.txt: wordlists/google-books.freq.txt
	LC_ALL=C sort $< > $@

wordlists/google-books-1grams.txt: wordlists/raw/google-books-1grams.txt
	LC_ALL=C egrep -h "^[A-Z]+	" $^ | sort > $@

wordlists/enable.txt: wordlists/raw/enable.txt
	tr a-z A-Z < $< | shell/freq1.sh > $@

wordlists/twl06.txt: wordlists/raw/twl06.txt
	tr a-z A-Z < $< | shell/freq1.sh > $@

doc: docs/SolverTools.html

docs/SolverTools.html: julia/SolverTools.jl jocco.jl
	julia julia/jocco.jl julia/SolverTools.jl

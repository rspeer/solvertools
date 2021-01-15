Prerequisites
=============
You need Python 3.6+, Make, and GNU tools such as 'grep' and 'sort'.

To set up Solvertools, run `setup.py develop` (not `install`) in your
appropriately-configured Python environment.

Getting an appropriately-configured Python environment
------------------------------------------------------

**These instructions are for Linux or WSL. I also sorta made it work on Windows -- see below.**

The best way to install Python packages is in a virtual environment,
which points `python` in your shell to a local copy. On many systems, you
could run:

    python3 -m venv env
    source env/bin/activate

But Ubuntu broke pyvenv, so use Ubuntu's virtualenv instead:

    sudo apt-get install python-virtualenv
    virtualenv --python=/usr/bin/python3 env
    source env/bin/activate

To install the code in this environment, run:

    python setup.py develop

...or, if you didn't set up a virtualenv, you might do this instead:

    sudo python3 setup.py develop

You'll need data, which you can download:

    wget http://tools.ireproof.org/static/solvertools-data-2021.zip
    unzip solvertools-data-2021.zip

Partial instructions for setting up on Windows
----------------------------------------------

There are a zillion different ways to set up Python on Windows, so I can't give
full detail about all the steps you might need to go through, but try this:

- Get an official version of Python for Windows from python.org
- When you install it, make sure to add Python to the PATH
- Clone this solvertools repository using git
- At your command prompt (cmd or powershell), go to the solvertools directory and run:

```
py -m pip install .
```

- Get the data from http://tools.ireproof.org/static/solvertools-data-2021.zip
- Unzip it in the solvertools directory, so that it populates the `solvertools/data` directory
- Test whether it worked:

```
py -m pip install pytest
py -m pytest
```


Quick start
===========

    >>> from solvertools.all import *
    >>> search('rg.of.el.qu.ry')[0]
    (14.9, 'RGB OF RELIQUARY')


Where to find stuff
===================
Everything relevant is imported into `solvertools.all`, but I haven't had time
to document all the individual operations. You'll have to look at the code
and/or the docstrings.

But here's an overview of what's in solvertools:

* `wordlist.py`: a model of words and their likelihood that lots of stuff
    uses; the "cromulence" measure

* `letters.py`: operations on letters and multisets of letters. Alphagrams,
    differences between alphagrams, consonantcies, phone-spell.

* `ciphers.py`: Caesar ciphers (including trying all possibilities), Vigenere
    ciphers.

* `search.py`: enables searching by clue, or delegating to the wordlist to
  search by just a pattern.

* `puzzle_structures.py`: solve certain structures of puzzles by brute force,
  particularly by trying indexing everything into everything
  (`index_all_the_things`) or trying all the possible diagonals.

* `anagram.py`: find interesting anagrams of sets of letters, even if there are
  too many of them. (Please be advised that anagrams of, say, 20 letters are
  for entertainment purposes only and should not be considered puzzle answers.)

There's more stuff in https://github.com/dgulotta/puzzle-tools .


Wordlists
=========
In solvertools, a wordlist is designed to store a set of words and their
relative frequencies, and to optimize various operations for finding words.

This is slightly different from the traditional sort of wordlist, which
merely makes a binary decision about whether something "is a word" or not.
In fact, in order to not miss potential answers, the main wordlist we use
has a long tail of dubious words.

The important thing is to rank words by their frequency, and to use that
frequency information appropriately. Our frequency information comes from
Google Books, and for any word that we didn't get from Google Books, we
fake it.

The data for wordlists are stored in various files that can be loaded
very quickly, such as SQLite databases and mmapped piles of bytes.

This module defines two wordlists as globals:

- WORDS, the large, combined wordlist. Its data comes from Google Books,
  WordNet, titles and redirects on Wikipedia, the NPL "allwords" list,
  and two Scrabble dictionaries, ENABLE2K and TWL06 (OWL2).

- SCRAB, a list of words that "have the Scrabble nature". Many wordlist
  features don't work on this list, because it is a binary decision.
  The frequency only indicates the number of Scrabble lists the word
  is found in, out of three: ENABLE2K, TWL06, and CSW2019.

      >>> 'qat' in SCRAB
      True

      >>> 'phonies' in SCRAB
      False

      >>> 'retweet' in SCRAB   # now that we have the 2019 list
      True

We'll use WORDS for the examples here, because it's the best suited for
them. It's also built into top-level functions such as search() and
cromulence().


Words, phrases, and slugs
=========================

When we refer to a 'word' here, it could actually be a phrase of multiple
words, separated by spaces.

As is conventional for crosswords and the Mystery Hunt, we don't consider
the spaces very important. All inputs will be converted to a form we call
a 'slug'. In solvertools, a slug is made only of the lowercase letters
a to z, with no spaces, digits, or punctuation.

To distinguish them from slugs, things that are supposed to be legible
text are written in capital letters.

    >>> from solvertools.all import slugify
    >>> slugify('ESCAPE FROM ZYZZLVARIA')
    'escapefromzyzzlvaria'
    >>> cromulence('escapefromzyzzlvaria')
    (25.3, 'ESCAPE FROM ZYZZL VARIA')


Cromulence
==========

"Cromulence" is how valid a sequence of letters is as a clue or a puzzle
answer. It's measured in dB, kinda. The zero point is the cutoff for whether
it considers it a real answer.

(We used to tune this point to various difficult-to-recognize puzzle answers,
but now it's just tuned to optimize the precision-recall tradeoff.)

Cromulence is rounded to one decimal place to avoid implying unreasonable
precision, and so that it's visually distinguishable from log probability in
Python output. The possible values seem to range from -45 to 35.

Positive cromulences correspond to real answers, with a precision of 96% and
a recall of 98%, in a test against distractors made of random letters selected
from an English letter distribution.

The `cromulence` function (a shorthand for `WORDS.cromulence`) won't fill in
blanks or regular expressions. Use `search` for that.

    >>> from solvertools.all import cromulence
    >>> cromulence('mobilesuitgundam')
    (21.6, 'MOBILE SUIT GUNDAM')
    >>> cromulence('mulugetawendimu')
    (18.7, 'MULUGETA WENDIMU')
    >>> cromulence('rgbofreliquary')
    (8.9, 'RGB OF RELIQUARY')
    >>> cromulence('atzerodtorvolokheg')
    (3.2, 'ATZERODT OR VOLOKH EG')
    >>> cromulence('turkmenhowayollary')
    (0.4, 'TURKMEN HOW A YOLLA RY')
    >>> cromulence('ottohidjanskey')
    (-1.7, "OTTO HID JAN'S KEY")
    >>> cromulence('ouipareesgay')
    (-6.0, 'OUI PA REES GAY')
    >>> cromulence('yoryu')
    (-7.6, 'YO RYU')


Searching by patterns and clues
===============================

`search()` finds words given various criteria, which can include a regex
pattern, a clue phrase, and/or a length.

The results are ordered by descending goodness, which is the log probability of
the text if there's no clue involved, or the score of the search result if
there was a clue.

    >>> search('.a.b.c..')[0][1]
    'BARBECUE'
    >>> search(clue='Lincoln assassin', length=15)[0][1]
    'JOHN WILKES BOOTH'
    >>> search(clue='US president', pattern='.a.f....')[0][1]
    'GARFIELD'

If the pattern contains spaces, we require the spacing of the text to match.

    >>> search('....e.......', clue='NASA vehicle')[0][1]
    'CARTERCOPTER'
    >>> search('....e .......', clue='NASA vehicle')[0][1]
    'SPACE SHUTTLE'

(This implementation is pretty rough; it just checks the spaces after trying
a bunch of words that match the pattern. If it doesn't find any, it gives up
and gives you the version that ignores spaces, just so that it isn't implying
there are no matches.)

Examples
========

Shifting and anagramming in a loop
----------------------------------
Suppose you've got a puzzle with the positions of letters of the alphabet
marked on a cycle of 26 dots, and you happen to know that these are going to
be anagrams minus a letter of reasonable words, but you'd have to solve a
different part of the puzzle to know which dot is A.

You can skip ahead in this puzzle by using Solvertools to try all possible
shifts, then anagram with one wildcard. Let's define a function that returns
the results, in reverse order by cromulence, along with the distance that
they're shifted through the alphabet:

    >>> from solvertools.all import *
    >>> def cyclogram(letters, additional=1):
    ...     results = []
    ...     for i in range(26):
    ...         cae = caesar_shift(letters, i)
    ...         ana = anagram_single(cae, wildcards=additional, count=10)
    ...         results.extend([(an + (i,)) for an in ana])
    ...     return sorted(results, reverse=True)
    ...
    >>> cyclogram('adegou')[:5]
    [(22.8, 'WHISKEY', 4),
     (20.5, 'CARIOUS', 14),
     (19.7, 'COURT IS', 14),
     (19.2, 'ROSCIUS', 14),
     (19.0, 'I COURSE', 14)]

Brute-force diagonalization
---------------------------

Here's the first recorded example of an answer on a diagonal in the Mystery
Hunt, the 1995 puzzle "Billiard Room". You're told to solve a logic puzzle
to order the 10 teams in the Central League of Underappreciated Employees,
then take the Nth letter from each team name. But with these 10 team names and
Solvertools, we don't have to solve the puzzle.

    >>> from solvertools.all import *
    >>> teams = [
    ...     'back-up singers',
    ...     'channel surfers',
    ...     'dermatologists',
    ...     'etymologists',
    ...     'receptionists',
    ...     'short order cooks',
    ...     'talk show hosts',
    ...     'taxi drivers',
    ...     'televangelists',
    ...     'undertakers'
    ... ]
    >>> brute_force_diagonalize(teams)[0]
    Tried 10000 permutations
    [...]
    Tried 3620000 permutations
    Log prob.   Cromulence  Text
    -12.9031    26      DELIVERIES
    -18.0365    22      STRIP POKER
    -18.1996    22      DE DISPOSER
    -18.3727    22      TEAR STAINS
    -18.7234    22      BE RESERVES
    -19.0139    21      ENLISTS OUR
    -19.2645    21      BE DESERVES
    -19.4999    21      SAY EARLIER
    -20.5336    20      BE RESOLVES
    -20.5965    20      TALENT OVER
    -20.9823    20      TEAM STRONG
    -21.0412    20      CHRIST SOIL
    -21.4347    19      RARE SERIES
    -21.4892    19      THY EARLIER
    -21.8216    19      RAY EARLIER
    -21.9774    19      CALM STRONG
    -22.2095    19      BEAR STAGES
    -22.2998    19      TERRORS OUR
    -22.3016    19      TELESERIES
    -22.3016    19      BADEN TOWER
    (-12.903120689538845, 'DELIVERIES')

DELIVERIES is actually the right answer.


Index All the Things
--------------------
Sometimes a puzzle ends with you having a big spreadsheet of data, and there's
nothing left to do but to try sorting by everything and indexing everything into
everything else.

Fortunately, the `index_all_the_things()` function can automate this.

It takes in a table, expressed as a list of lists, and tries everything. The
`indexing_demo()` function will demonstrate it getting the correct answer on
the table of data from "Soylent Partners".

The table must have a header row, giving a name to each column.

The table can have a smallish number of missing entries, and some of its entries
can be uncertain. Uncertain entries should be given as regular expressions between
slashes. If all you know is that the entry starts with T, write it as `/T.*/`.

Here's an example of loading data from the puzzle "Soylent Partners", with some
entries left incomplete. (You can see the data in
`data/test/soylent_incomplete.csv`, or the completed version in
`data/test/soylent_partners.csv`.)

It will show the current best result as it searches, then both print and return
the `count` best answers.

    >>> puz = read_csv_file(data_path('test/soylent_incomplete.csv'))
    >>> index_all_the_things(puz, count=3)
        -52.24  ACTOR CM TABLS YOU  Don't sort, take the first letters of 'colorname'
        -40.75  LC MARC NOBUO SATO  Don't sort, index by 'inspector' into 'colorname'
        -38.59  SHOULD NABUCCO NA   Sort by 'colorname', index by 'inspector' into 'colorname'
        -38.14  BEMOANS THE AUCOC   Sort by 'cluea', index by 'inspector' into 'colorname'
        -35.05  SUCH A BISON SUCH A Sort by 'clueb', index by 'inspector' into 'colorname'
        -25.79  RAINBOW CACTUS OF   Sort by 'columnorder', index by 'inspector' into 'colorname'

    Log prob.   Cromulence  Text    Info
    -25.7857    22.4    RAINBOW CACTUS OF   Sort by 'columnorder', index by 'inspector' into 'colorname'
    -26.2560    22.2    RAINBOW CACTUS TO   Sort by 'columnorder', index by 'inspector' into 'colorname'
    -26.3918    22.1    RAINBOW CACTUS IN   Sort by 'columnorder', index by 'inspector' into 'colorname'
[(-25.785671522045277, 'RAINBOW CACTUS OF', "Sort by 'columnorder', index by 'inspector' into 'colorname'"),
 (-26.2559966671154, 'RAINBOW CACTUS TO', "Sort by 'columnorder', index by 'inspector' into 'colorname'"),
 (-26.39179329162168, 'RAINBOW CACTUS IN', "Sort by 'columnorder', index by 'inspector' into 'colorname'")]

The actual answer is `RAINBOW CACTUSES`, which it gets exactly if it's given
`soylent_partners.csv` instead.

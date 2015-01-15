Prerequisites
=============
You need Python 3.3+, Make, and GNU tools such as 'grep' and 'sort'.

To install the code, run:

    python3 setup.py develop

Then, to set up the wordlists, run:

    make

...and wait for maybe an hour. (Getting a USB drive of the built data from
someone is also an option.)

One person (Paul) has possibly made this work on Windows, but you need a
terminal that supports UTF-8, because I'm not going to hunt down all the things
that can go wrong without it. Paul recommends msys2.


Quick start
===========

    >>> from solvertools.all import *
    >>> search('rg.of.el.qu.ry')[0]
    (-33.868139189898926, 'RGB OF RELIQUARY')


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
  is found in, out of three: ENABLE2K, TWL06, and Collins April 2007
  (a successor to SOWPODS, although not the most up-to-date one).

    >>> 'qat' in SCRAB
    True
    >>> 'phonies' in SCRAB
    False

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
    (25.3, 'ESCAPE FROM ZYZZLVARIA')


Cromulence
==========

"Cromulence" is how valid a sequence of letters is as a clue or a puzzle
answer. It's measured in dB, kinda, with the reference point of 0 dB being the
awkward meta-answer "OUI, PAREE'S GAY".

Cromulence is rounded to one decimal place to avoid implying unreasonable
precision, and so that it's visually distinguishable from log probability in
Python output. The possible values seem to range from -45 to 35.

Positive cromulences correspond to real answers, with a precision of 99% and
a recall of 86%, in a test against distractors made of random letters selected
from an English letter distribution.

The `cromulence` function (a shorthand for `WORDS.cromulence`) won't fill in
blanks or regular expressions. Use `search` for that.

    >>> from solvertools.all import cromulence
    >>> cromulence('mulugetawendimu')
    (25.1, 'MULUGETA WENDIMU')

    >>> cromulence('rgbofreliquary')
    (14.9, 'RGB OF RELIQUARY')

    >>> cromulence('atzerodtorvolokheg')
    (8.8, 'ATZERODT OR VOLOKH EG')

    >>> cromulence('turkmenhowayollary')   # wrong spacing
    (6.7, 'TURKMEN HOW AYO LLARY')

    >>> cromulence('ottohidjanskey')
    (3.9, 'OTTO HID JANS KEY')

    >>> cromulence('ouipareesgay')
    (-0.0, "OUI PAREE 'S GAY")

    >>> cromulence('yoryu')                # wrong spacing
    (-6.2, 'YOR YU')

In case you're wondering, the least-cromulent Mystery Hunt clues and answers
that this metric finds are:

    -6.2  YORYU
    -2.5  N
    -1.6  E
    -0.7  HUERFANA
    0.0   OUI PAREE'S GAY
    0.0   OCEAN E HQ
    0.4   UV
    1.0   IO
    1.2   BABE WYNERY
    1.2   HIFIS
    1.8   ACQUIL
    2.3   ALT F FOUR
    3.9   OTTO HID JAN'S KEY
    5.1   V NECK
    5.0   PREW
    5.4   DIN
    6.3   NEA
    6.7   KLAK RING
    6.7   QUEUER
    6.8   WEBISMS


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
    >>> search(clue='US president', pattern='.a....e.')[0][1]
    'VAN BUREN'


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


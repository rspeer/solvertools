Prerequisites
=============
You need Python 3.3+, Make, and GNU tools such as 'grep' and 'sort'.

In a Python 3.3+ environment, run:

    python setup.py develop

To set up the wordlists, run:

    make

...and wait for maybe half an hour.


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

We'll use WORDS for the examples here, because it's the best suited for
them.


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

As an example, the slug of "ESCAPE FROM ZYZZLVARIA" is "escapefromzyzzlvaria".


Cromulence
==========

"Cromulence" is how valid a sequence of letters is as a clue or a puzzle
answer. It's measured in dB, kinda, with the reference point of 0 dB being the
awkward meta-answer "OUI, PAREE'S GAY".

Cromulence is rounded to an integer to avoid implying unreasonable
precision, and to avoid confusion with log probability. The possible
values seem to range from -42 to 32.

Positive cromulences correspond to real answers, with a precision of 99% and
a recall of 86%, in a test against distractors made of random letters selected
from an English letter distribution.

    >>> WORDS.cromulence('mulugetawendimu')
    (24, 'MULUGETA WENDIMU')

    >>> WORDS.cromulence('rgbofreliquary')
    (15, 'RGB OF RELIQUARY')

    >>> WORDS.cromulence('atzerodtorvolokheg')
    (9, 'ATZERODT OR VOLOKH EG')

    >>> WORDS.cromulence('turkmenhowayollary')   # wrong spacing
    (7, 'TURKMEN HOW AYO LLARY')

    >>> WORDS.cromulence('ottohidjanskey')
    (4, 'OTTO HID JANS KEY')

    >>> WORDS.cromulence('ouipareesgay')
    (0, "OUI PAREE 'S GAY")

    >>> WORDS.cromulence('yoryu')                # wrong spacing
    (-6, 'YOR YU')

In case you're wondering, the least-cromulent Mystery Hunt clues and answers
that this metric finds are:

    -6  YORYU
    -3  N
    -2  E
    -1  HUERFANA
    0   OUI PAREE'S GAY
    0   OCEAN E HQ
    0   UV
    1   BABE WYNERY
    1   HIFIS
    1   IO
    2   ALT F FOUR
    2   ACQUIL
    4   OTTO HID JAN'S KEY
    5   V NECK
    5   PREW
    5   DIN
    6   NEA
    7   KLAK RING
    7   WEBISMS
    7   NEATIFY
    7   QUEUER
    7   PG WORD
    7   GOOIER
    7   VI


Examples
========

Brute-force diagonalization
---------------------------

Here's the first recorded example of an answer on a diagonal in the Mystery
Hunt, the 1995 puzzle "Billiard Room". You're told to solve a logic puzzle
to order the 10 teams in the Central League of Underappreciated Employees,
then take the Nth letter from each team name. But with these 10 team names and
Solvertools, we don't have to solve the puzzle.

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
    >>> brute_force_diagonalize(teams, quiet=True)
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


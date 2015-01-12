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
    -2  N
    -2  E
    -1  HUERFANA
    0   OUI PAREE'S GAY
    0   OCEAN E HQ
    0   UV
    0   HIFIS
    1   BABE WYNERY
    1   IO
    2   ALT F FOUR
    2   ACQUIL
    4   OTTO HID JAN'S KEY
    5   PREW
    5   DIN


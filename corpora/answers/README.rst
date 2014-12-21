.. _answers:

`data/corpora/answers` -- The MH 2004-2008 answer corpus
========================================================

The files in this directory contain the answer phrases from Mystery
Hunts 2004 through 2008. They comprise 597 answers, of which 56 are
meta-puzzle answers. This is far too small to serve as a corpus, but
may still be useful for getting an idea of what kinds of strings might
be reasonable answers.

Each file contains one line per answer. The order of the lines may or
may not be meaningful. Each line is of the format ``(STRING, TYPE)`` where
STRING is the answer as a string enclosed in double quotes, for
example::

        ("CONVERSATIONALIST", Puzzle)
        ("BOYES", Puzzle)
        ("RGB OF RELIQUARY", Meta)

The answer strings are almost all uppercase letters and spaces, but
there are a few hyphens, periods, apostrophes, and lowercase letters.
No answer string contains a line break or a double quote. ``TYPE`` is
one of {``Puzzle``, ``Meta``, ``Ante``}. Puzzle denotes a regular,
non-meta puzzle. Meta denotes a meta-puzzle, meta-meta-puzzle, or any
puzzle which uses the *answers* of other puzzles as inputs. Less
conventional combinations may be marked as Puzzle, or may be omitted.
Ante is only used for 2006 (SPIES) and denotes the "ante" (or "agent")
puzzle of each round. These do not use other answers as inputs and
could have been marked as Puzzle.

Examples of puzzles not found in the data are the puzzles from 2005
with physical objects as answers. (Approximate strings could have been
listed, but this seemed essentially useless for any sort of answer
string analysis.) There may be minor coverage or quality issues
throughout the data.

Alex Schwendner, 2008

.. vim: tw=70

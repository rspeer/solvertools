"""
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

"""
from solvertools.util import db_path, data_path, wordlist_path, corpus_path
from solvertools.normalize import slugify, unspaced_lower
from solvertools.regextools import is_exact, regex_len, regex_slice
from solvertools.letters import (
    alphagram, alphabytes_to_alphagram, anahash, consonantcy, alphabytes, random_letters
)
import sqlite3
import re
import os
import mmap
from collections import defaultdict, Counter
from pprint import pprint
from math import log, exp
from itertools import islice
import logging
logger = logging.getLogger(__name__)


# The NULL_HYPOTHESIS_ENTROPY is the log-probability per letter of something
# that is just barely an answer, for which we use the entropy of the meta
# answer "OUI, PAREE'S GAY". (Our probability metric considers that a worse
# answer than "TURKMENHOWAYOLLARY" or "ATZERODT OR VOLOKH EG".)
NULL_HYPOTHESIS_ENTROPY = -4.192795083133463
DECIBEL_SCALE = 20 / log(10)


class Wordlist:
    schema = [
        """
        CREATE TABLE words (
            slug TEXT,
            freq INT,
            text TEXT
        )
        """,
        "CREATE UNIQUE INDEX words_slug ON words (slug)",
        "CREATE INDEX words_freq ON words (freq)"
    ]
    wordplay_schema = [
        "CREATE TABLE wordplay (slug TEXT, alphagram TEXT, anahash TEXT, consonantcy TEXT)",
        "CREATE UNIQUE INDEX wordplay_slug on words (slug)",
        "CREATE INDEX wordplay_alphagram on wordplay (alphagram)",
        "CREATE INDEX wordplay_anahash on wordplay (anahash)",
        "CREATE INDEX wordplay_consonantcy on wordplay (consonantcy)",
    ]
    max_indexed_length = 25

    def __init__(self, name):
        """
        Load a wordlist, given its name.
        """
        self.name = name
        self.db = wordlist_db_connection(name + '.wl.db')
        self._word_cache = {}
        self._grep_maps = {}
        self._alpha_maps = {}
        self.logtotal = None

    def __contains__(self, word):
        """
        `word in wordlist` is a quick, idiomatic way to tell if the given word
        (or phrase) appears in the wordlist.

        The word can be entered in natural form, possibly with capital letters
        and spaces. It will be converted to a lowercase, unspaced 'slug' here.
        """
        slug = slugify(word)
        return self.lookup_slug(slug) is not None

    def lookup_slug(self, slug):
        """
        Given an alphabetic 'slug', find its corresponding row of the
        database. If there is such a row, return its unscaled frequency and
        its text (including spaces). If not, return None.
        """
        if slug in self._word_cache:
            return self._word_cache[slug]
        c = self.db.cursor()
        c.execute("SELECT freq, text FROM words WHERE slug=?", (slug,))
        result = c.fetchone()
        self._word_cache[slug] = result
        return result

    def segment_logprob(self, slug):
        """
        If this slug appears directly in the word list, return its log
        probability and its text. Otherwise, return None.
        """
        if self.logtotal is None:
            totalfreq, _ = self.lookup_slug('')
            self.logtotal = log(totalfreq)
        found = self.lookup_slug(slug)
        if found is None:
            return None
        freq, text = found
        logprob = log(freq) - self.logtotal
        return logprob, text

    def text_logprob(self, text):
        """
        Get the log probability of this text, along with its most likely
        spacing, gluing it together with multiple "segments" if necessary.
        """
        slug = slugify(text)
        n = len(slug)
        best_partial_results = ['']
        best_logprobs = [0.]
        for right_edge in range(1, n + 1):
            found = self.segment_logprob(slug[:right_edge])
            if found:
                rprob, rtext = found
                best_partial_results.append(rtext)
                best_logprobs.append(rprob)
            else:
                best_logprobs.append(-1000.)
                best_partial_results.append(slug[:right_edge])
            for left_edge in range(1, right_edge):
                lprob = best_logprobs[left_edge]
                found2 = self.segment_logprob(slug[left_edge:right_edge])
                if found2:
                    rprob, rtext = found2
                    if lprob + rprob > best_logprobs[right_edge]:
                        best_logprobs[right_edge] = lprob + rprob - log(10)
                        ltext = best_partial_results[left_edge]
                        best_partial_results[right_edge] = ltext + ' ' + rtext
        return best_logprobs[-1], best_partial_results[-1]

    def cromulence(self, text):
        """
        Estimate how likely this text is to be an answer. The "cromulence"
        scale is defined at the top of this module.
        """
        slug = slugify(text)
        if len(slug) == 0:
            return (0, '')
        logprob, found_text = self.text_logprob(slug)
        entropy = logprob / (len(slug) + 1)
        cromulence = round((entropy - NULL_HYPOTHESIS_ENTROPY) * DECIBEL_SCALE)
        return cromulence, found_text

    def logprob_to_cromulence(self, logprob, length):
        """
        Convert a log probability to the 'cromulence' scale, which only
        requires knowing the length of the text.
        """
        entropy = logprob / (length + 1)
        cromulence = round((entropy - NULL_HYPOTHESIS_ENTROPY) * DECIBEL_SCALE)
        return cromulence

    def grep(self, pattern, length=None):
        """
        """
        pattern = unspaced_lower(pattern)
        if is_exact(pattern):
            if pattern in self:
                yield self.segment_logprob(pattern)
            return
        if length:
            minlen = maxlen = length
        else:
            minlen, maxlen = regex_len(pattern)
        if minlen < 1:
            minlen = 1
        if maxlen > self.max_indexed_length:
            maxlen = self.max_indexed_length

        for cur_length in range(minlen, maxlen + 1):
            if cur_length not in self._grep_maps:
                mm = self._open_mmap(
                    wordlist_path_from_name(
                        'greppable/%s.%d' % (self.name, cur_length)
                    )
                )
                self._grep_maps[cur_length] = mm
            else:
                mm = self._grep_maps[cur_length]
            pbytes = pattern.encode('ascii')
            pattern1 = b'^' + pbytes + b','
            pattern2 = b'\n' + pbytes + b','
            match = re.match(pattern1, mm)
            if match:
                found = mm[match.start():match.end() - 1].decode('ascii')
                yield self.segment_logprob(found)
            for match in re.finditer(pattern2, mm):
                found = mm[match.start() + 1:match.end() - 1].decode('ascii')
                yield self.segment_logprob(found)

    def grep_one(self, pattern, length=None):
        for result in self.grep(pattern, length):
            return result

    def search(self, pattern, count=10):
        pattern = unspaced_lower(pattern)
        if is_exact(pattern):
            return [self.text_logprob(pattern)]
        minlen, maxlen = regex_len(pattern)
        if minlen != maxlen:
            # If there are variable-length matches, the dynamic programming
            # strategy won't work, so fall back on grepping for complete
            # matches in the wordlist.
            items = list(self.grep(pattern))
            items.sort(reverse=True)
            return items[:count]

        best_partial_results = [[]]
        for right_edge in range(1, maxlen + 1):
            segment = regex_slice(pattern, 0, right_edge)
            results_this_step = list(islice(self.grep(segment), count))

            for left_edge in range(1, right_edge):
                if best_partial_results[left_edge]:
                    segment = regex_slice(pattern, left_edge, right_edge)
                    found = list(islice(self.grep(segment), count))
                    for lprob, ltext in best_partial_results[left_edge]:
                        for rprob, rtext in found:
                            results_this_step.append((
                                lprob + rprob - log(2),
                                ltext + ' ' + rtext
                            ))
            results_this_step.sort(reverse=True)
            best_partial_results.append(results_this_step[:count])
        return best_partial_results[-1]

    def _iter_query(self, query, params=()):
        c = self.db.cursor()
        c.execute(query, params)
        while True:
            got = c.fetchmany()
            if not got:
                return
            for row in got:
                yield row

    def _iter_singletons(self, query, params=()):
        c = self.db.cursor()
        c.execute(query, params)
        while True:
            got = c.fetchmany()
            if not got:
                return
            for row in got:
                yield row[0]

    def iter_all_by_freq(self):
        """
        Read the database and iterate through it in descending order
        by frequency.
        """
        return self._iter_query(
            "SELECT slug, freq, text FROM words ORDER BY freq DESC"
        )

    def iter_all_by_cromulence(self):
        """
        Read the database and iterate through it in descending order
        by cromulence.
        """
        return self._iter_query(
            "SELECT slug, freq, text FROM words ORDER BY freq/(length(slug) + 1) DESC"
        )

    def find_sub_alphagrams(self, alpha, wildcard=False):
        if len(alpha) + wildcard < 2:
            return
        abytes = alphabytes(alpha)
        max_length = min(len(alpha) + wildcard - 2, self.max_indexed_length)
        if max_length < 2:
            max_length = 2
        if max_length not in self._alpha_maps:
            mm = self._open_mmap(
                wordlist_path_from_name(
                    'alphabytes/%s.%d' % (self.name, max_length)
                )
            )
            self._alpha_maps[max_length] = mm
        else:
            mm = self._alpha_maps[max_length]
        if wildcard:
            pattern = b'\n[' + abytes + b']*.[' + abytes + b']*\n'
        else:
            pattern = b'\n[' + abytes + b']+\n'
        for match in re.finditer(pattern, mm):
            found = mm[match.start() + 1:match.end() - 1]
            yield found

    def find_by_alphagram(self, alphagram):
        return self._iter_query(
            "SELECT w.* from wordplay wp, words w "
            "WHERE wp.slug=w.slug and wp.alphagram=? "
            "ORDER BY freq DESC",
            (alphagram,)
        )

    def find_by_alphagram_raw(self, alphagram):
        return self._iter_singletons(
            "SELECT w.slug from wordplay wp, words w "
            "WHERE wp.slug=w.slug and wp.alphagram=? "
            "ORDER BY freq DESC",
            (alphagram,)
        )

    def find_by_anahash_raw(self, anahash):
        return self._iter_singletons(
            "SELECT w.slug from wordplay wp, words w "
            "WHERE wp.slug=w.slug and wp.anahash=? "
            "ORDER BY freq DESC",
            (anahash,)
        )

    def find_by_consonantcy(self, consonants):
        return self._iter_query(
            "SELECT w.* from wordplay wp, words w "
            "WHERE wp.slug=w.slug and wp.consonantcy=? "
            "ORDER BY freq DESC",
            (consonants,)
        )

    def __getitem__(self, pattern):
        return self.grep_one(pattern)

    def __repr__(self):
        return "Wordlist(%r)" % self.name

    def _open_mmap(self, path):
        openfile = open(path, 'r+b')
        mm = mmap.mmap(openfile.fileno(), 0, access=mmap.ACCESS_READ)
        return mm

    # Below this are building steps that should only need to be run once.
    def build_db(self):
        """
        Build a SQLite database from a flat wordlist file.
        """
        self.db.execute("DROP TABLE IF EXISTS words")
        for statement in self.schema:
            self.db.execute(statement)

        total = 0
        with self.db:
            for i, slug, freq, text in read_wordlist(self.name):
                self.db.execute(
                    "INSERT INTO words (slug, freq, text) "
                    "VALUES (?, ?, ?)",
                    (slug, freq, text)
                )
                total += freq
                if i % 10000 == 0:
                    print("\t%s,%s" % (text, freq))

            # Use the empty string to record the total
            print("Total: %d" % total)
            self.db.execute(
                "INSERT INTO words (slug, freq, text) VALUES ('', ?, '')",
                (total,)
            )

    def build_wordplay(self):
        self.db.execute("DROP TABLE IF EXISTS wordplay")
        for statement in self.wordplay_schema:
            self.db.execute(statement)

        with self.db:
            for i, slug, freq, text in read_wordlist(self.name):
                alpha = alphagram(slug)
                ana = anahash(slug)
                cons = consonantcy(slug)
                self.db.execute(
                    "INSERT INTO wordplay (slug, alphagram, anahash, consonantcy) "
                    "VALUES (?, ?, ?, ?)",
                    (slug, alpha, ana, cons)
                )
                if i % 10000 == 0:
                    print("\t%s" % (text))

    def write_greppable_lists(self):
        """
        Separate the words by length and write them into separate files.
        """
        os.makedirs(wordlist_path('greppable'), exist_ok=True)
        length_files = {
            length: open(
                wordlist_path_from_name(
                    'greppable/%s.%d' % (self.name, length)
                ), 'w', encoding='ascii'
            )
            for length in range(1, self.max_indexed_length + 1)
        }
        i = 0
        for slug, freq, text in self.iter_all_by_cromulence():
            length = len(slug)
            if 1 <= length <= self.max_indexed_length:
                out = length_files[length]
                print("%s,%d" % (slug, freq), file=out)
            if i % 10000 == 0:
                print("\t%s,%d" % (slug, freq))
            i += 1
        for file in length_files.values():
            file.close()

    def write_alphabytes(self):
        os.makedirs(wordlist_path('alphabytes'), exist_ok=True)
        length_files = {
            length: open(
                wordlist_path_from_name(
                    'alphabytes/%s.%d' % (self.name, length)
                ), 'wb'
            )
            for length in range(2, self.max_indexed_length + 1)
        }
        i = 0
        used = set()
        for slug, freq, text in self.iter_all_by_freq():
            if len(slug) >= 2:
                maxlen = self.max_indexed_length
                abytes = alphabytes(slug)
                if abytes not in used:
                    for length in range(len(slug), maxlen + 1):
                        out = length_files[length]
                        out.write(b'\n')
                        out.write(abytes)
                        used.add(abytes)
        for file in length_files.values():
            file.write(b'\n')
            file.close()

    def test_cromulence(self):
        """
        More trivia about cromulence:

        The most interesting cromulent fake answers, made of random letters, that
        came out in several runs of testing were:

            17  ALCUNI
            15  CLANKS
            12  LEVERDSEE
            9   DTANDISCODE
            9   ITOO
            9   DRCELL
            9   LEERECHO
            7   EBOLASOSIT
            7   RAGEMYLADSOK

        Those would be good inputs for a game of Metapuzzle Spaghetti.
        """
        real_answers = []
        for year in ['2004', '2005', '2006', '2007', '2008', '2011', '2012']:
            with open(corpus_path('answers/mystery%s.txt' % year)) as file:
                for line in file:
                    line = line.strip()
                    if line:
                        answer, _typ = line.rsplit(',', 1)
                        real_answers.append(answer)
        fake_answers = [
            random_letters(len(real)) for real in real_answers
        ]
        results = []
        for ans in real_answers:
            cromulence, spaced = self.cromulence(ans)
            logprob, _ = self.text_logprob(ans)
            if cromulence >= 1:
                results.append((cromulence, logprob, spaced, 'true positive'))
            else:
                results.append((cromulence, logprob, spaced, 'false negative'))
        for ans in fake_answers:
            cromulence, spaced = self.cromulence(ans)
            logprob, _ = self.text_logprob(ans)
            if cromulence >= 1:
                results.append((cromulence, logprob, spaced, 'false positive'))
            else:
                results.append((cromulence, logprob, spaced, 'true negative'))

        results.sort(reverse=True)
        counts = Counter([item[-1] for item in results])
        precision = counts['true positive'] / (counts['true positive'] + counts['false positive'])
        recall = counts['true positive'] / (counts['true positive'] + counts['false negative'])
        f_score = 2/(1/precision + 1/recall)
        for cromulence, logprob, spaced, category in results:
            print("%d\t%2.2f\t%s\t%s" % (cromulence, logprob, category, spaced))
        print("Precision: %2.2f%%" % (precision * 100))
        print("Recall: %2.2f%%" % (recall * 100))
        return f_score

    def show_best_results(self, results):
        results.sort(reverse=True)
        print("Log prob.\tCromulence\tText")
        for logprob, text in results[:20]:
            cromulence, spaced = self.cromulence(text)
            print("%4.4f\t%d\t\t%s" % (logprob, cromulence, spaced))
        return results[0]


def wordlist_path_from_name(name):
    """
    Get the path to the plain-text form of a wordlist.
    """
    return wordlist_path(name + '.txt')


def wordlist_db_connection(filename):
    """
    Get a SQLite DB connection for a wordlist. (The DB must previously
    have been built.)
    """
    os.makedirs(db_path(''), exist_ok=True)
    return sqlite3.connect(db_path(filename))


def read_wordlist(name):
    """
    Read a wordlist from a comma-separated plain-text file, and iterate
    its entries in order.
    """
    filepath = wordlist_path_from_name(name)
    with open(filepath, encoding='utf-8') as wordfile:
        for i, line in enumerate(wordfile):
            if ',' not in line:
                continue
            line = line.rstrip()
            text, freq = line.split(',', 1)
            freq = int(freq)
            slug = slugify(text)
            if slug:
                yield (i, slug, freq, text)


def combine_wordlists(weighted_lists, out_name):
    """
    This function is used in building the combined wordlist called WORDS.
    It reads several wordlists from their plain-text form, and adds together
    the frequencies of the words they contain, applying a multiplicative
    weight to each.
    """
    freqs = defaultdict(float)
    texts = {}
    print("Combining %s" % weighted_lists)
    for name, weight in weighted_lists:
        for i, slug, freq, text in read_wordlist(name):
            # Replace an existing text if this spelling of it has a solid
            # majority of the frequency so far. Avoids weirdness such as
            # spelling "THE" as "T'HE".
            if slug not in texts or (freq * weight) > freqs[slug]:
                texts[slug] = text
            freqs[slug] += freq * weight
            if i % 10000 == 0:
                print("\t%s,%s" % (text, freq))

    alphabetized = sorted(list(texts))
    out_filename = wordlist_path_from_name(out_name)
    with open(out_filename, 'w', encoding='utf-8') as out:
        print("Writing %r" % out)
        for i, slug in enumerate(alphabetized):
            line = "%s,%s" % (texts[slug], int(freqs[slug]))
            print(line, file=out)
            if i % 10000 == 0:
                print("\t%s,%s" % (texts[slug], int(freqs[slug])))


def build_extras(name):
    """
    Load a wordlist with a particular name, and create additional files that
    enable more operations on the wordlist -- a file that can be mmapped and
    grepped quickly, a file of 'alphabytes' that can be mmapped and grepped to
    find anagrams, and a database of 'wordplay' properties of words.
    """
    dbw = Wordlist(name)
    dbw.build_db()
    dbw.write_greppable_lists()
    dbw.write_alphabytes()
    dbw.build_wordplay()


WORDS = Wordlist('combined')
SCRAB = Wordlist('scrab')
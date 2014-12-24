"""
"Cromulence" is how valid a sequence of letters is as a clue or a puzzle
answer. It's measured in dB, with the reference point of 0 dB being the
awkward meta-answer "OUI, PAREE'S GAY".

Cromulence is rounded to an integer to avoid implying unreasonable
precision, and to avoid confusion with log probability. The possible
values seem to range from -33 to 28.

>>> words.cromulence('mulugetawendimu')
(22, 'MULUGETA WENDIMU')

>>> words.cromulence('rgbofreliquary')
(13, 'RGB OF RELIQUARY')

>>> words.cromulence('atzerodtorvolokheg')
(8, 'ATZERODT OR VOLOKH EG')

>>> words.cromulence('turkmenhowayollary')   # wrong spacing
(5, 'TURKMEN HOW A YOLLA RY')

>>> words.cromulence('ottohidjanskey')
(3, 'OTTO HID JANS KEY')

>>> words.cromulence('ouipareesgay')
(0, "OUI PAREE 'S GAY")

>>> words.cromulence('yoryu')                # wrong spacing
(-7, 'YOR YU')
"""
from solvertools.util import db_path, data_path, wordlist_path
from solvertools.normalize import alpha_slug, unspaced_lower
from solvertools.regextools import is_exact, regex_len, regex_slice
from solvertools.letters import alphagram, anahash, consonantcy
import sqlite3
import re
import os
import mmap
from collections import defaultdict
from math import log, exp
from itertools import islice
import logging
logger = logging.getLogger(__name__)


# The NULL_HYPOTHESIS_ENTROPY is the log-probability per letter of something
# that is just barely an answer, for which we use the entropy of the meta
# answer "OUI, PAREE'S GAY". (Our probability metric considers that a worse
# answer than "TURKMENHOWAYOLLARY" or "ATZERODT OR VOLOKH EG".)
NULL_HYPOTHESIS_ENTROPY = -3.8203213525570447
DECIBELS_PER_NEPER = 20 / log(10)


def wordlist_path_from_name(name):
    return wordlist_path(name + '.txt')


def wordlist_db_connection(filename):
    os.makedirs(db_path(''), exist_ok=True)
    return sqlite3.connect(db_path(filename))


def read_wordlist(name):
    filepath = wordlist_path_from_name(name)
    with open(filepath, encoding='utf-8') as wordfile:
        for i, line in enumerate(wordfile):
            if ',' not in line:
                continue
            line = line.rstrip()
            text, freq = line.split(',', 1)
            freq = int(freq)
            slug = alpha_slug(text)
            if slug:
                yield (i, slug, freq, text)


def combine_wordlists(weighted_lists, out_name):
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


class DBWordlist:
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
        self.name = name
        self.db = wordlist_db_connection(name + '.wl.db')
        self._word_cache = {}
        self._grep_maps = {}
        self.logtotal = None

    def __contains__(self, word):
        slug = alpha_slug(word)
        return self.lookup_slug(slug) is not None

    def lookup_slug(self, slug):
        if slug in self._word_cache:
            return self._word_cache[slug]
        c = self.db.cursor()
        c.execute("SELECT freq, text FROM words WHERE slug=?", (slug,))
        result = c.fetchone()
        self._word_cache[slug] = result
        return result

    def segment_logprob(self, slug):
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
        slug = alpha_slug(text)
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
                        best_logprobs[right_edge] = lprob + rprob - log(2)
                        ltext = best_partial_results[left_edge]
                        best_partial_results[right_edge] = ltext + ' ' + rtext
        return best_logprobs[-1], best_partial_results[-1]

    def cromulence(self, text):
        slug = alpha_slug(text)
        if len(slug) == 0:
            return (0, '')
        logprob, found_text = self.text_logprob(slug)
        entropy = logprob / (len(slug) + 1)
        cromulence = round((entropy - NULL_HYPOTHESIS_ENTROPY) * DECIBELS_PER_NEPER)
        return cromulence, found_text

    def grep(self, pattern, length=None):
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
            return list(self.grep(pattern))

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

    def iter_all_by_freq(self):
        """
        Read the database and iterate through it in descending order
        by frequency.
        """
        return self._iter_query(
            "SELECT slug, freq, text FROM words ORDER BY freq DESC"
        )

    def find_by_alphagram(self, alphagram):
        return self._iter_query(
            "SELECT w.* from wordplay wp, words w "
            "WHERE wp.slug=w.slug and wp.alphagram=?",
            (alphagram,)
        )

    def find_by_anahash(self, anahash):
        return self._iter_query(
            "SELECT w.* from wordplay wp, words w "
            "WHERE wp.slug=w.slug and wp.anahash=?",
            (anahash,)
        )

    def find_by_consonantcy(self, consonants):
        return self._iter_query(
            "SELECT w.* from wordplay wp, words w "
            "WHERE wp.slug=w.slug and wp.consonantcy=?",
            (consonants,)
        )

    def __getitem__(self, pattern):
        return self.grep_one(pattern)

    def __repr__(self):
        return "DBWordlist(%r)" % self.name

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
        for slug, freq, text in self.iter_all_by_freq():
            length = len(slug)
            if 1 <= length <= self.max_indexed_length:
                out = length_files[length]
                print("%s,%d" % (slug, freq), file=out)
            if i % 10000 == 0:
                print("\t%s,%d" % (slug, freq))
            i += 1
        for file in length_files.values():
            file.close()


# TODO: make these actual commands that can be run from the Makefile when
# appropriate
def build_combined_list():
    combine_wordlists([
        ('google-books', 1),
        ('enable', 250),
        ('twl06', 250),
        ('wikipedia-en-titles', 800),
    ], 'combined')


def build_extras(name):
    dbw = DBWordlist(name)
    dbw.build_db()
    #dbw.write_greppable_lists()
    dbw.build_wordplay()


words = DBWordlist('combined')
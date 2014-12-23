"""
"Cromulence" is how valid a sequence of letters is as a clue or a puzzle
answer. It's measured in dB, with the reference point of 0 dB being the
awkward meta-answer "OUI, PAREE'S GAY".

>>> words.cromulence('mulugetawendimu')
(20.81283388396978, 'MULUGETA WENDIMU')

>>> words.cromulence('rgbofreliquary')
(12.801189823550718, 'RGB OF RELIQUARY')

>>> words.cromulence('atzerodtorvolokheg')
(7.424762425298007, 'ATZERODT OR VOLOKH EG')

>>> words.cromulence('turkmenhowayollary')   # wrong spacing
(5.297392577036264, 'TURKMEN HOW A YOLLA RY')

>>> words.cromulence('ottohidjanskey')
(3.277474561428554, 'OTTO HID JANS KEY')

>>> words.cromulence('ouipareesgay')
(0.0, "OUI PAREE 'S GAY")

>>> words.cromulence('yoryu')   # wrong spacing
(-7.496185741874485, 'YOR YU')
"""
from solvertools.util import db_path, data_path, wordlist_path
import re
import logging
import os
import sqlite3
from collections import defaultdict
from math import log, exp
logger = logging.getLogger(__name__)


# The NULL_HYPOTHESIS_ENTROPY is the log-probability per letter of something
# that is just barely an answer, for which we use the entropy of the meta
# answer "OUI, PAREE'S GAY". (Our probability metric considers that a worse
# answer than "TURKMENHOWAYOLLARY" or "ATZERODT OR VOLOKH EG".)
#
# Puzzle answers with 
NULL_HYPOTHESIS_ENTROPY = -3.6603643108893644
DECIBELS_PER_NEPER = 20 / log(10)
NONALPHA_RE = re.compile(r'[^a-z]')


def wordlist_path_from_name(name):
    return wordlist_path(name + '.txt')


def wordlist_db_connection(filename):
    os.makedirs(db_path(''), exist_ok=True)
    return sqlite3.connect(db_path(filename))


def alpha_slug(text):
    """
    Return a text as a sequence of letters. No spaces, digits, hyphens,
    or apostrophes.
    """
    return NONALPHA_RE.sub('', text.lower())


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
    max_indexed_length = 25

    def __init__(self, name):
        self.name = name
        self.db = wordlist_db_connection(name + '.wl.db')
        self.word_cache = {}
        self.logtotal = None

    def __contains__(self, word):
        slug = alpha_slug(word)
        return self.lookup_slug(slug) is not None

    def lookup_slug(self, slug):
        if slug in self.word_cache:
            return self.word_cache[slug]
        c = self.db.cursor()
        c.execute("SELECT freq, text FROM words WHERE slug=?", (slug,))
        result = c.fetchone()
        if result is None:
            result = (1e-40, slug)
        self.word_cache[slug] = result
        return result

    def segment_logprob(self, slug):
        if self.logtotal is None:
            totalfreq, _ = self.lookup_slug('')
            self.logtotal = log(totalfreq)
        freq, text = self.lookup_slug(slug)
        logprob = log(freq) - self.logtotal
        return logprob, text

    def text_logprob(self, text):
        slug = alpha_slug(text)
        n = len(slug)
        best_partial_results = ['']
        best_logprobs = [0.]
        for right_edge in range(1, n + 1):
            rprob, rtext = self.segment_logprob(slug[:right_edge])
            best_partial_results.append(rtext)
            best_logprobs.append(rprob)
            for left_edge in range(1, right_edge):
                lprob = best_logprobs[left_edge]
                rprob, rtext = self.segment_logprob(slug[left_edge:right_edge])
                if lprob + rprob > best_logprobs[right_edge]:
                    best_logprobs[right_edge] = lprob + rprob
                    ltext = best_partial_results[left_edge]
                    best_partial_results[right_edge] = ltext + ' ' + rtext
        return best_logprobs[-1], best_partial_results[-1]

    def cromulence(self, text):
        slug = alpha_slug(text)
        if len(slug) == 0:
            return (0., '')
        logprob, found_text = self.text_logprob(slug)
        entropy = logprob / (len(slug) + 1)
        cromulence = (entropy - NULL_HYPOTHESIS_ENTROPY) * DECIBELS_PER_NEPER
        return cromulence, found_text

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
                    print(text, freq)

            # Use the empty string to record the total
            print("Total: %d" % total)
            self.db.execute(
                "INSERT INTO words (slug, freq, text) VALUES ('', ?, '')",
                (total,)
            )

    def iter_all_by_freq(self):
        """
        Read the database and iterate through it in descending order
        by frequency.
        """
        c = self.db.cursor()
        c.execute(
            "SELECT slug, freq, text FROM words ORDER BY freq DESC"
        )
        while True:
            got = c.fetchmany()
            if not got:
                return
            for row in got:
                yield row

    def write_greppable_lists(self):
        """
        Separate the words by length and write them into separate files.
        """
        os.makedirs(wordlist_path('greppable'), exist_ok=True)
        length_files = {
            length: open(
                wordlist_path_from_name(
                    'greppable/%s.%d' % (self.name, length)
                ), 'w', encoding='utf-8'
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
def build_all():
    combine_wordlists([
        ('google-books', 1),
        ('enable', 250),
        ('twl06', 250),
        ('wikipedia-en-titles', 800),
    ], 'combined')

def build_more():
    DBWordlist('combined').build_db()
    #DBWordlist('combined').write_greppable_lists()


words = DBWordlist('combined')

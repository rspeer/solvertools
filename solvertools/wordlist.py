from solvertools.util import db_path, data_path, wordlist_path
import re
import logging
import os
import sqlite3
from collections import defaultdict
logger = logging.getLogger(__name__)


NONALPHA_RE = re.compile(r'[^A-Z]')


def wordlist_path_from_name(name):
    return wordlist_path(name + '.txt')


def wordlist_db_connection(filename):
    os.makedirs(db_path(''), exist_ok=True)
    return sqlite3.connect(db_path(filename))


def alpha_cram(text):
    """
    Return a text as a sequence of letters. No spaces, digits, hyphens,
    or apostrophes.
    """
    return NONALPHA_RE.sub('', text.upper())


def read_wordlist(name):
    filepath = wordlist_path_from_name(name)
    with open(filepath, encoding='utf-8') as wordfile:
        for i, line in enumerate(wordfile):
            if ',' not in line:
                continue
            line = line.rstrip()
            text, freq = line.split(',', 1)
            freq = int(freq)
            slug = alpha_cram(text)
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

    def build_db(self):
        self.db.execute("DROP TABLE IF EXISTS words")
        for statement in self.schema:
            self.db.execute(statement)

        with self.db:
            for i, slug, freq, text in read_wordlist(self.name):
                self.db.execute(
                    "INSERT INTO words (slug, freq, text) "
                    "VALUES (?, ?, ?)",
                    (slug, freq, text)
                )
                if i % 10000 == 0:
                    print(text, freq)

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
        os.makedirs(wordlist_path('greppable'), exist_ok=True)
        length_files = {
            length: open(
                wordlist_path_from_name('greppable/%s.%d' % (self.name, length)),
                'w', encoding='utf-8'
            )
            for length in range(1, self.max_indexed_length + 1)
        }
        i = 0
        for slug, freq, text in self.iter_all_by_freq():
            length = len(slug)
            if 1 <= length <= self.max_indexed_length:
                out = length_files[length]
                print("%s,%d,%s" % (slug, freq, text.lower()), file=out)
            if i % 10000 == 0:
                print(slug, freq, text.lower())
            i += 1
        for file in length_files.values():
            file.close()

def build_all():
    combine_wordlists([
        ('google-books', 1),
        ('enable', 250),
        ('twl06', 250),
        ('wikipedia-en-titles', 800),
    ], 'combined')
    DBWordlist('combined').build_db()

def build_more():
    DBWordlist('combined').write_greppable_lists()
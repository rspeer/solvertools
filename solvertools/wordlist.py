from solvertools.util import get_db, get_wordlist
import re
import logging
import os
import sqlite3
from collections import defaultdict
logger = logging.getLogger(__name__)


NONALPHA_RE = re.compile(r'[^A-Z]')


def wordlist_db_connection(filename):
    os.makedirs(get_db(''), exist_ok=True)
    return sqlite3.connect(get_db(filename))


def alpha_cram(text):
    """
    Return a text as a sequence of letters. No spaces, digits, hyphens,
    or apostrophes.
    """
    return NONALPHA_RE.sub('', text.upper())


class DBWordlist:
    schema = [
        """
        CREATE TABLE words (
        slug TEXT,
        freq REAL,
        text TEXT
        )
        """,
        "CREATE UNIQUE INDEX words_slug ON words (slug)",
        "CREATE INDEX words_freq ON words (freq)"
    ]

    def __init__(self, name):
        self.name = name
        self.db = wordlist_db_connection(name + '.wl.db')

    @staticmethod
    def build_dicts(wordlists):
        freqs = defaultdict(float)
        texts = {}
        for filename, weight in wordlists:
            filepath = get_wordlist(filename)
            with open(filepath, encoding='utf-8') as wordfile:
                for i, line in enumerate(wordfile):
                    line = line.rstrip()
                    if ',' not in line:
                        continue
                    text, freq = line.split(',', 1)
                    freq = int(freq) * weight
                    slug = alpha_cram(text)
                    if slug:
                        freqs[slug] += freq
                        if slug not in texts:
                            texts[slug] = text
        return freqs, texts


    def build(self, wordlists):
        freqs, texts = DBWordlist.build_dicts(wordlists)
        alphabetized = sorted(list(texts))

        self.db.execute("DROP TABLE IF EXISTS words")
        for statement in self.schema:
            self.db.execute(statement)

        with self.db:
            for i, slug in enumerate(alphabetized):
                text = texts[slug]
                freq = freqs[slug]
                self.db.execute(
                    "INSERT INTO words (slug, freq, text) "
                    "VALUES (?, ?, ?)",
                    (slug, freq, text)
                )
                if i % 1000 == 0:
                    print(text, freq)

def build_all():
    DBWordlist('scrabble').build([
        ('enable.txt', 0.5), ('twl06.txt', 0.5)
    ])
    DBWordlist('cromulent').build([
        ('google-books.txt', 1),
        ('enable.txt', 250),
        ('twl06.txt', 250),
        ('wikipedia-en-titles.txt', 800),
    ])


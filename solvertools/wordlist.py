from solvertools.util import get_db, get_wordlist
import re
import logging
import os
import sqlite3
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

    def build(self, wordlists):
        self.db.execute("DROP TABLE IF EXISTS words")
        for statement in self.schema:
            self.db.execute(statement)

        with self.db:
            # Keep track of entries we already have. Put the empty string here
            # to make sure we don't add it.
            used_slugs = set('')
            for filename, weight in wordlists:
                filepath = get_wordlist(filename)
                with open(filepath, encoding='utf-8') as wordfile:
                    for i, line in enumerate(wordfile):
                        word, freq = line.rstrip().split(',', 1)
                        freq = int(freq) * weight
                        slug = alpha_cram(word)
                        if slug not in used_slugs:
                            used_slugs.add(slug)
                            self.db.execute(
                                "INSERT INTO words (slug, freq, text) "
                                "VALUES (?, ?, ?)",
                                (slug, freq, word)
                            )
                        if i % 1000 == 0:
                            print(word, freq)

def build_all():
    DBWordlist('scrabble').build([
        ('enable.txt', 1), ('twl06.txt', 1)
    ])
    DBWordlist('cromulent').build([
        ('google-books.txt', 1),
        ('enable.txt', 500),
        ('wikipedia-en-titles.txt', 800),
    ])


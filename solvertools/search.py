from solvertools.wordlist import WORDS
from solvertools.normalize import slugify, sanitize
from solvertools.util import data_path, db_path
from wordfreq import tokenize
from operator import itemgetter
from collections import defaultdict
from .conceptnet_numberbatch import load_numberbatch, get_vector, similar_to_term
import re
import sqlite3

NUMBERBATCH = None
DB = None


def query_expand(word):
    global NUMBERBATCH
    if NUMBERBATCH is None:
        NUMBERBATCH = load_numberbatch()

    similar = similar_to_term(NUMBERBATCH, word, limit=25)
    sim_words = [word2.replace('"','') for word2, sim in similar.items() if sim >= 0.2]
    parts = [word] + [word2 for word2 in sim_words if word2 != word]
    query = ' OR '.join('"%s"' % word2 for word2 in parts)
    return '(%s)' % query


def db_search(query, limit=10000):
    global DB
    if DB is None:
        DB = sqlite3.connect(db_path("search.db"), check_same_thread=False)

    cur = DB.cursor()
    results = defaultdict(float)
    for (keyword, negscore) in cur.execute("SELECT keyword, bm25(clues) AS score FROM clues WHERE text MATCH ? LIMIT ?", (query, limit)):
        assert negscore < 0
        results[keyword] -= negscore
    return results


def db_rank(clue):
    scores = defaultdict(float)
    for match, score in db_search(clue).items():
        scores[slugify(match)] += score * 1000
        parts = tokenize(match, 'en')
        for part in parts:
            scores[slugify(part)] += score * 1000 / len(parts)

    for word in tokenize(clue, 'en'):
        logprob_result = WORDS.segment_logprob(slugify(word))
        if logprob_result is not None:
            logprob, _ = logprob_result
        else:
            logprob = -1000.
        rare_boost = min(25., -logprob)
        for match, score in db_search(word).items():
            scores[slugify(match)] += rare_boost * score * 10
            parts = tokenize(match, 'en')
            for part in parts:
                scores[slugify(part)] += rare_boost * score * 10 / len(parts)

        query = query_expand(word)
        for match, score in db_search(query).items():
            scores[slugify(match)] += rare_boost * score
            parts = tokenize(match, 'en')
            for part in parts:
                scores[slugify(part)] += rare_boost * score / len(parts)

    return scores


def search(pattern=None, clue=None, length=None, count=20):
    """
    Find words and phrases that match various criteria: a regex pattern,
    a clue phrase, and/or a length.

    >>> search('.a.b.c..')[0][1]
    'BARBECUE'
    >>> search('.a....e.', clue='US President')[0][1]
    'VAN BUREN'
    >>> search(clue='lincoln assassin', length=15)[0][1]
    'JOHN WILKES BOOTH'
    """
    if clue is None:
        if pattern is None:
            return []
        else:
            return WORDS.search(pattern, count=count, use_cromulence=True)

    if pattern is not None:
        pattern = pattern.lstrip('^').rstrip('$').lower()
        pattern = re.compile('^' + pattern + '$')

    raw_matches = sorted(db_rank(clue).items(), key=itemgetter(1), reverse=True)
    matches = {}
    for slug, score in raw_matches:
        if length is None or length == len(slug):
            if pattern is None or pattern.match(slug):
                crom, text = WORDS.cromulence(slug)
                matches[text] = score
        if len(matches) >= count:
            break
    return sorted([(score, text) for (text, score) in matches.items()], reverse=True)

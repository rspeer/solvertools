from solvertools.wordlist import WORDS
from solvertools.letters import alphagram, alphabytes, alphabytes_to_alphagram, alpha_diff, anahash
from solvertools.normalize import alpha_slug
import itertools
import numpy as np


def anagram_single(text, wordlist=WORDS):
    return list(_anagram_single(alphagram(alpha_slug(text)), wordlist))


def _anagram_single(alpha, wordlist=WORDS, depth=10):
    for slug, freq, text in itertools.islice(wordlist.find_by_alphagram(alpha), depth):
        yield slug


def subsequences(seq, depth=None):
    if depth is None:
        depth = len(seq) - 1
    for seq_len in range(len(seq) - depth, len(seq)):
        for combo in itertools.combinations(seq, seq_len):
            yield ''.join(combo)


def _anagram_double(alpha, wordlist=WORDS, single_depth=1):
    yield from _anagram_single(alpha, wordlist)
    for sub in wordlist.find_sub_alphagrams(alpha):
        alpha1 = alphabytes_to_alphagram(sub)
        alpha2 = alpha_diff(alpha, alpha1)
        for slug2 in _anagram_single(alpha2, wordlist, single_depth):
            for slug1 in _anagram_single(alpha1, wordlist, single_depth):
                yield slug1 + slug2


def anagram_double(text, wordlist=WORDS, depth=100, single_depth=1):
    results = []
    used = set()
    for slug in _anagram_double(alphagram(alpha_slug(text)), wordlist, single_depth):
        logprob, text = wordlist.text_logprob(slug)
        textblob = ''.join(sorted(text.split(' ')))
        if textblob not in used:
            print("%4.4f\t%s" % (logprob, text))
            results.append((logprob, text))
            if len(results) >= depth:
                break
            used.add(textblob)
    results.sort()
    return results

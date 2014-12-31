from solvertools.wordlist import WORDS
from solvertools.letters import alphagram, alphabytes, alphabytes_to_alphagram, alpha_diff, anahash
from solvertools.normalize import alpha_slug
import itertools
import numpy as np


def eval_anagrams(gen, wordlist, count):
    results = []
    used = set()
    for slug in gen:
        logprob, text = wordlist.text_logprob(slug)
        textblob = ''.join(sorted(text.split(' ')))
        if textblob not in used:
            print("%4.4f\t%s" % (logprob, text))
            results.append((logprob, text))
            if len(results) >= count * 2:
                break
            used.add(textblob)
    results.sort()
    return results[-count:]


def anagram_single(text, wordlist=WORDS, count=10):
    return eval_anagrams(
        _anagram_single(alphagram(alpha_slug(text)), wordlist),
        wordlist, count
    )


def _anagram_single(alpha, wordlist=WORDS, count=100):
    for slug, freq, text in itertools.islice(wordlist.find_by_alphagram(alpha), count):
        yield slug


def anagram_double(text, wordlist=WORDS, count=100, depth=1):
    return eval_anagrams(
        _anagram_double(alphagram(alpha_slug(text)), wordlist, depth),
        wordlist, count
    )


def _anagram_double(alpha, wordlist=WORDS, depth=1):
    yield from _anagram_single(alpha, wordlist)
    for sub in wordlist.find_sub_alphagrams(alpha):
        alpha1 = alphabytes_to_alphagram(sub)
        try:
            alpha2 = alpha_diff(alpha, alpha1)
        except ValueError:
            continue
        for slug2 in _anagram_single(alpha2, wordlist, depth):
            for slug1 in _anagram_single(alpha1, wordlist, depth):
                yield slug1 + slug2


def anagram_triple(text, wordlist=WORDS, count=100, depth=3):
    return eval_anagrams(
        _anagram_triple(alphagram(alpha_slug(text)), wordlist, count, depth),
        wordlist, count
    )


def _anagram_triple(alpha, wordlist=WORDS, max_results=100, depth=3):
    yield from itertools.islice(_anagram_double(alpha, wordlist, depth), max_results // 2)
    for ahash in subsequences(anahash(alpha), 3):
        for slug1, freq1, text1 in wordlist.find_by_anahash(ahash):
            alpha1 = alphagram(slug1)
            try:
                alpha2 = alpha_diff(alpha, alpha1)
                inner_func = _anagram_double
                inner_depth = depth
                if len(alpha2) >= 25:
                    inner_func = _anagram_triple
                    inner_depth = 1
                for slug2 in itertools.islice(inner_func(alpha2, wordlist, inner_depth), inner_depth):
                    yield slug1 + slug2
            except ValueError:
                pass


def subsequences(seq, depth=None):
    if depth is None:
        depth = len(seq) - 1
    for seq_len in reversed(range(len(seq) - depth, len(seq) + 1)):
        for combo in itertools.combinations(seq, seq_len):
            yield ''.join(combo)



from solvertools.wordlist import WORDS
from solvertools.letters import alphagram, alphabytes, alphabytes_to_alphagram, alpha_diff, anahash
from solvertools.normalize import alpha_slug
import itertools
import numpy as np


letters_to_try = 'etaoinshrdlucympbgfvxwkjzq'


def eval_anagrams(gen, wordlist, count):
    results = []
    used = set()
    for slug in gen:
        logprob, text = wordlist.text_logprob(slug)
        textblob = ''.join(sorted(text.split(' ')))
        if textblob not in used:
            print("%4.4f\t%s" % (logprob, text))
            cromulence = wordlist.logprob_to_cromulence(logprob, len(slug))
            results.append((cromulence, logprob, text))
            if len(results) >= count * 2:
                break
            used.add(textblob)
    results.sort()
    return results[-count:]


def anagram_single(text, wildcards=0, wordlist=WORDS, count=10):
    return eval_anagrams(
        _anagram_single(alphagram(alpha_slug(text)), wildcards, wordlist, count),
        wordlist, count
    )


def _anagram_single(alpha, wildcards=0, wordlist=WORDS, count=100):
    if wildcards == 0:
        for slug, freq, text in itertools.islice(wordlist.find_by_alphagram(alpha), count):
            yield slug
    else:
        for seq in itertools.combinations(letters_to_try, wildcards):
            newalpha = alphagram(alpha + ''.join(seq))
            for slug, freq, text in itertools.islice(wordlist.find_by_alphagram(newalpha), count):
                yield slug            


def anagram_double(text, wildcards=0, wordlist=WORDS, max_results=100, depth=1):
    return eval_anagrams(
        _anagram_double(alphagram(alpha_slug(text)), wildcards, wordlist, depth),
        wordlist, max_results
    )


def _anagram_double(alpha, wildcards=0, wordlist=WORDS, depth=1):
    yield from _anagram_single(alpha, wildcards, wordlist)
    for sub in wordlist.find_sub_alphagrams(alpha, wildcard=(wildcards > 0)):
        alpha1 = alphabytes_to_alphagram(sub)
        alpha2, wildused = alpha_diff(alpha, alpha1)
        wildcards_remaining = wildcards - wildused
        if wildcards_remaining >= 0:
            for slug2 in _anagram_single(alpha2, wildcards_remaining, wordlist, depth):
                for slug1 in _anagram_single(alpha1, 0, wordlist, depth):
                    yield slug1 + slug2


def anagram_triple(text, wildcards=0, wordlist=WORDS, max_results=100, depth=3):
    return eval_anagrams(
        _anagram_triple(alphagram(alpha_slug(text)), wildcards, wordlist, max_results, depth),
        wordlist, max_results
    )


def _anagram_triple(alpha, wildcards=0, wordlist=WORDS, max_results=100, depth=3):
    yield from itertools.islice(_anagram_double(alpha, wildcards, wordlist, 1), max_results // 2)
    for ahash in subsequences(anahash(alpha), 3):
        for slug1, freq1, text1 in wordlist.find_by_anahash(ahash):
            alpha1 = alphagram(slug1)
            alpha2, wildused = alpha_diff(alpha, alpha1)
            wildcards_remaining = wildcards - wildused
            if wildcards_remaining >= 0:
                inner_func = _anagram_double
                inner_depth = min(depth, max_results)
                inner_max = inner_depth
                if len(alpha2) >= 25:
                    inner_func = _anagram_triple
                    inner_depth = 1
                print(alpha2, inner_max)
                gen = itertools.islice(
                    inner_func(alpha2, wildcards_remaining, wordlist, inner_depth),
                    inner_max
                )
                for slug2 in gen:
                    yield slug1 + slug2


def subsequences(seq, depth=None):
    if depth is None:
        depth = len(seq) - 1
    for seq_len in reversed(range(len(seq) - depth, len(seq) + 1)):
        for combo in itertools.combinations(seq, seq_len):
            yield ''.join(combo)



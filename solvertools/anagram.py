from solvertools.wordlist import WORDS
from solvertools.letters import (
    alphagram, alphabytes, alphabytes_to_alphagram, anagram_diff, anahash,
    anagram_cost
)
from solvertools.normalize import alpha_slug
import itertools
import numpy as np


letters_to_try = 'etaoinshrdlucympbgfvxwkjzq'


def interleave(iteriter):
    seen_iters = []
    for newiter in iteriter:
        seen_iters.append(newiter)
        for i in reversed(range(len(seen_iters))):
            try:
                yield next(seen_iters[i])
            except StopIteration:
                del seen_iters[i]
    while seen_iters:
        for i in reversed(range(len(seen_iters))):
            try:
                yield next(seen_iters[i])
            except StopIteration:
                del seen_iters[i]        


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
            if len(results) >= count * 5:
                break
            used.add(textblob)
    results.sort()
    return [(cromulence, text) for (cromulence, logprob, text) in results[-count:]]


def anagram_single(text, wildcards=0, wordlist=WORDS, count=10):
    return eval_anagrams(
        _anagram_single(alphagram(alpha_slug(text)), wildcards, wordlist),
        wordlist, count
    )


def _anagram_single(alpha, wildcards, wordlist):
    if len(alpha) == 0:
        # don't make anything out of *just* wildcards
        return
    if len(alpha) == 1 and wildcards == 0:
        # short circuit
        yield alpha
        return
    if wildcards == 0:
        yield from wordlist.find_by_alphagram_raw(alpha)
    else:
        for seq in itertools.combinations(letters_to_try, wildcards):
            newalpha = alphagram(alpha + ''.join(seq))
            yield from wordlist.find_by_alphagram_raw(newalpha)


def anagram_double(text, wildcards=0, wordlist=WORDS, max_results=100):
    return eval_anagrams(
        _anagram_double(alphagram(alpha_slug(text)), wildcards, wordlist),
        wordlist, max_results
    )


def _anagram_double(alpha, wildcards, wordlist):
    return interleave([
        _anagram_single(alpha, wildcards, wordlist),
        interleave(_anagram_double_2(alpha, wildcards, wordlist))
    ])

def adjusted_anagram_cost(item):
    """
    Sorts the sub-anagrams we should try by their likeliness to yield
    """
    used, letters, wildcards, index = item
    if wildcards >= 0:
        return anagram_cost(letters) / (wildcards + 1) * (index + 100)
    else:
        raise ValueError


def _anagram_double_2(alpha, wildcards, wordlist):
    if len(alpha) >= 25:
        return
    sub_anas = [
        (sub, adiff, wildcards - wildcards_used, index)
        for index, sub in enumerate(wordlist.find_sub_alphagrams(alpha, wildcard=(wildcards > 0)))
        for adiff, wildcards_used in [anagram_diff(alpha, alphabytes_to_alphagram(sub))]
        if wildcards >= wildcards_used
    ]

    sub_anas.sort(key=adjusted_anagram_cost)
    for abytes, alpha2, wildcards_remaining, index in sub_anas:
        alpha1 = alphabytes_to_alphagram(abytes)
        for slug1 in _anagram_single(alpha1, 0, wordlist):
            yield _anagram_double_piece(slug1, alpha2, wildcards_remaining, wordlist)


def _anagram_double_piece(slug1, alpha2, wildcards_remaining, wordlist):
    for slug2 in _anagram_single(alpha2, wildcards_remaining, wordlist):
        yield slug1 + slug2


def anagrams(text, wildcards=0, wordlist=WORDS, max_results=100):
    return eval_anagrams(
        _anagram_recursive(alphagram(alpha_slug(text)), wildcards, wordlist),
        wordlist, max_results
    )


def _anagram_recursive(alpha, wildcards, wordlist):
    if len(alpha) <= 10:
        return _anagram_double(alpha, wildcards, wordlist)
    else:
        return _anagram_recursive_2(alpha, wildcards, wordlist)


def _anagram_recursive_2(alpha, wildcards, wordlist):
    return interleave([
        _anagram_double(alpha, wildcards, wordlist),
        interleave(_anagram_recursive_pieces(alpha, wildcards, wordlist))
    ])


def _anagram_recursive_pieces(alpha, wildcards, wordlist):
    for ahash in subsequences(anahash(alpha), 4):
        yield interleave(_anagram_recursive_piece_1(alpha, wildcards, wordlist, ahash))


def _anagram_recursive_piece_1(alpha, wildcards, wordlist, ahash):
    sub_anas = [
        (sub, adiff, wildcards - wildcards_used, index)
        for index, sub in enumerate(wordlist.find_by_anahash_raw(ahash))
        for adiff, wildcards_used in [anagram_diff(alpha, alphagram(sub))]
        if wildcards >= wildcards_used
    ]
    sub_anas.sort(key=adjusted_anagram_cost)

    for slug1, alpha2, wildcards_remaining, index in sub_anas:
        alpha1 = alphagram(slug1)
        yield _anagram_recursive_piece_2(slug1, alpha2, wildcards_remaining, wordlist)


def _anagram_recursive_piece_2(slug1, alpha, wildcards, wordlist):
    for slug2 in _anagram_recursive(alpha, wildcards, wordlist):
        yield slug1 + slug2


def subsequences(seq, depth=None):
    if depth is None:
        depth = len(seq) - 1
    min_len = max(len(seq) - depth, 1)
    for seq_len in reversed(range(min_len, len(seq) + 1)):
        for combo in itertools.combinations(seq, seq_len):
            yield ''.join(combo)


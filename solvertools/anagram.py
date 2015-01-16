"""
This anagrammer is pretty cool.

It can probably still be improved, possibly by actually using priority
queues with a search strategy instead of all these iterator shenanigans.
"""
from solvertools.wordlist import WORDS
from solvertools.letters import (
    alphagram, alphabytes, alphabytes_to_alphagram, anagram_diff, anahash,
    anagram_cost
)
from solvertools.normalize import slugify
import itertools
import time


letters_to_try = 'etaoinshrdlucympbgfvxwkjzq'


def interleave(iteriter):
    """
    Okay, suppose you've got an unbounded iterator of unbounded iterators,
    and you want to make an iterator that will get to *all* the items in all
    the iterators eventually.

    If you're familiar with how to prove that the rational numbers are
    countable, you'll be familiar with how to do this. We basically make a
    grid of iterators and walk down the reversed diagonals, skipping over
    iterators that have actually ended.

    Even though iterators of anagrams are actually finite, this works as a
    way of searching through them breadth-first, instead of getting stuck
    depth-first on bad anagrams.
    """
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


def eval_anagrams(gen, wordlist, count, quiet=False, time_limit=None):
    """
    The final step in anagramming. Given a generator of anagrams, `gen`,
    extract their readable text with spaces, get a reasonable number of
    results that aren't just shuffling the words of other results, and
    sort them by their cromulence (see wordlist.py).

    The results are printed as they are encountered, and at the end, the top
    `count` are returned from best to worst.
    """
    start_time = time.monotonic()
    results = []
    used = set()
    best_logprob = -1000
    for slug in gen:
        logprob, text = wordlist.text_logprob(slug)
        textblob = ''.join(sorted(text.split(' ')))
        if textblob not in used:
            if not quiet:
                if logprob > best_logprob:
                    best_logprob = logprob
                    print("%4.4f\t%s" % (logprob, text))
            cromulence = wordlist.logprob_to_cromulence(logprob, len(slug))
            results.append((cromulence, logprob, text))
            if len(results) >= count * 5:
                break
            if time_limit and (time.monotonic() - start_time > time_limit):
                break
            used.add(textblob)
    results.sort(reverse=True)
    return [(cromulence, text) for (cromulence, logprob, text) in results[:count]]


def anagram_single(text, wildcards=0, wordlist=WORDS, count=10, quiet=True):
    """
    Search for anagrams that appear directly in the wordlist.
    """
    return eval_anagrams(
        _anagram_single(alphagram(slugify(text)), wildcards, wordlist),
        wordlist, count, quiet=quiet
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


def adjusted_anagram_cost(item):
    """
    Sorts the sub-anagrams we should try by their likeliness to yield good
    anagrams.
    """
    used, letters, wildcards, index = item
    if wildcards >= 0:
        return anagram_cost(letters) / (wildcards + 1) * (index + 1)
    else:
        raise ValueError


def anagram_double(text, wildcards=0, wordlist=WORDS, count=100, quiet=False):
    """
    Search for anagrams that can be made of two words or phrases from the
    wordlist.
    """
    return eval_anagrams(
        _anagram_double(alphagram(slugify(text)), wildcards, wordlist),
        wordlist, count, quiet=quiet
    )


def _anagram_double(alpha, wildcards, wordlist):
    return interleave(_anagram_double_2(alpha, wildcards, wordlist))


def _anagram_double_2(alpha, wildcards, wordlist):
    yield _anagram_single(alpha, wildcards, wordlist)
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


def anagrams(text, wildcards=0, wordlist=WORDS, count=100, quiet=False, time_limit=None):
    """
    Search for anagrams that are made of an arbitrary number of pieces from the
    wordlist.
    """
    return eval_anagrams(
        _anagram_recursive(alphagram(slugify(text)), wildcards, wordlist),
        wordlist, count, quiet=quiet, time_limit=time_limit
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


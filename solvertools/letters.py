import numpy as np
from solvertools.normalize import slugify
import re
import random
ASCII_a = 97


# An estimate of the frequencies of letters in English, as a length-26
# vector of proportions
letter_freqs = np.array([
    0.08331452,  0.01920814,  0.04155464,  0.03997236,  0.11332581,
    0.01456622,  0.02694035,  0.02517641,  0.08116646,  0.00305369,
    0.00930784,  0.05399477,  0.02984008,  0.06982714,  0.06273243,
    0.0287359 ,  0.00204801,  0.07181286,  0.07714659,  0.06561591,
    0.03393991,  0.01232891,  0.01022719,  0.0037979 ,  0.01733258,
    0.00303336
])


def letters_to_vec(letters):
    """
    Convert an iterator of lowercase letters, such as a 'slug' form, into
    a length-26 vector indicating how often those letters occur.
    """
    vec = np.zeros(26)
    for letter in letters:
        index = ord(letter) - ASCII_a
        vec[index] += 1
    return vec


def to_proportion(vec):
    """
    Convert a vector that counts occurrences to a vector of proportions
    (whose sum is 1).
    """
    return vec / vec.sum()


def alphagram(slug):
    """
    Given text in 'slug' form, return its alphagram, which is the string of
    its letters sorted in alphabetical order.
    """
    return ''.join(sorted(slug))


def alphabytes(slug):
    """
    This representation is used internally to Solvertools. It's like an
    alphagram, but represents up to 7 occurrences of a letter as unique bytes
    that can be searched for in a specially-prepared word list.

    This allows simple regexes to match "a word with at most two e's and at
    most three t's", a search which would be very complex and inefficient in
    the usual string representation.
    """
    alpha = alphagram(slug)
    current_letter = None
    rank = 0
    bytenums = []
    for letter in alpha:
        if letter == current_letter:
            rank += 1
        else:
            rank = 0
        if rank < 6:
            num = ord(letter) - 96 + (rank + 2) * 32
        else:
            num = ord(letter) - 96
        bytenums.append(num)
        current_letter = letter
    return bytes(bytenums)


def alphabytes_to_alphagram(abytes):
    """
    Convert the specialized 'alphabytes' form described above to an ordinary,
    printable alphagram.
    """
    letters = [chr(96 + byte % 32) for byte in abytes]
    return ''.join(letters)


def anagram_diff(a1, a2):
    """
    Find the difference between two multisets of letters, in a way specialized
    for anagramming.

    Returns a pair containing:

    - the alphagram of letters that remain
    - the number of letters in a2 that are not found in a1, which is the number
      of "wildcards" to consume
    """
    adiff = ''
    wildcards_used = 0
    for letter in set(a2) - set(a1):
        diff = a2.count(letter) - a1.count(letter)
        wildcards_used += diff
    for letter in sorted(set(a1)):
        diff = (a1.count(letter) - a2.count(letter))
        if diff < 0:
            wildcards_used -= diff
        else:
            adiff += letter * diff
    return adiff, wildcards_used


def diff_both(a1, a2):
    """
    Compare two multisets of letters, returning:

    - The alphagram of letters in a1 but not in a2
    - The alphagram of letters in a2 but not in a1
    """
    diff1 = ''
    diff2 = ''
    for letter in set(a2) - set(a1):
        diff = a2.count(letter) - a1.count(letter)
        diff2 += letter * diff
    for letter in sorted(set(a1)):
        diff = (a1.count(letter) - a2.count(letter))
        if diff < 0:
            diff2 += letter * diff
        else:
            diff1 += letter * diff
    return diff1, diff2


def diff_exact(full, part):
    """
    Find the difference between two multisets of letters, returning the
    alphagram of letters that are in `full` but not in `part`. If any letters
    are in `part` but not in `full`, raises an error.
    """
    diff1, diff2 = diff_both(full, part)
    if diff2:
        raise ValueError("Letters were left over: %s" % diff2)
    return diff1


def anahash(slug):
    if slug == '':
        return ''
    vec = to_proportion(letters_to_vec(slug))
    anomaly = vec - letter_freqs
    codes = np.flatnonzero(anomaly > 0) + ASCII_a
    return bytes(list(codes)).decode('ascii')


def anagram_cost(letters):
    """
    Return a value that's probably larger for sets of letters that are
    harder to anagram.

    I came up with this formula in the original version of anagram.js. Much
    like most of anagram.js, I can't entirely explain why it is the way it
    is.

    The 'discrepancy' of a set of letters is a vector indicating how far
    it is from the average proportions of a set of letters. These values
    are raised to the fourth power and summed to form one factor of this
    cost formula. The other factor is the number of letters.
    """
    if letters == '':
        return 0
    n_letters = len(letters)
    vec = to_proportion(letters_to_vec(letters))
    discrepancy = (1 - vec / letter_freqs)
    return np.sqrt((discrepancy ** 2).sum()) * n_letters


VOWELS_RE = re.compile('[aeiouy]')
def consonantcy(slug):
    """
    Given a word in 'slug' form, return just the consonants. 'y' is always
    considered a vowel and 'w' is always considered a consonant, regardless
    of context.
    """
    return VOWELS_RE.sub('', slug)


PHONESPELL_MAP = dict(zip(
    'abcdefghijklmnopqrstuvwxyz',
    '22233344455566677778889999'
))
UN_PHONESPELL_MAP = {
    '2': '[abc]',
    '3': '[def]',
    '4': '[ghi]',
    '5': '[jkl]',
    '6': '[mno]',
    '7': '[pqrs]',
    '8': '[tuv]',
    '9': '[wxyz]'
}


def phonespell(text):
    "Convert letters to the digits 2-9 on a phone keypad."
    return ''.join(PHONESPELL_MAP[ch] for ch in slugify(text))


def un_phonespell(digits):
    """
    Convert digits 2-9 to a regular expression of letters, matching what
    they spell on a phone keypad.
    """
    if isinstance(digits, int):
        digits = str(digits)
    pattern = ''.join(UN_PHONESPELL_MAP[digit] for digit in digits)
    return pattern


def random_letters(num):
    """
    Get `num` random letters that are distributed like English. Useful for
    testing against a null hypothesis.
    """
    letters = []
    for i in range(num):
        rand = random.random()
        choice = '#'
        for j in range(26):
            if rand < letter_freqs[j]:
                choice = chr(j + ord('a'))
                break
            else:
                rand -= letter_freqs[j]
        letters.append(choice)
    return ''.join(letters)


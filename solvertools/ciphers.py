import string
from solvertools.wordlist import WORDS
ASCII_a = 97


def shift_letter(char, offset):
    if char not in string.ascii_letters:
        return char
    idx = ord(char.lower()) - ASCII_a
    new_idx = (idx + offset) % 26
    new_char = chr(ASCII_a + new_idx)
    if char.isupper():
        return new_char.upper()
    else:
        return new_char


def caesar_shift(text, offset):
    """
    Performs a Caesar shift by the given offset.

    If the offset is a letter, it will look it up in the alphabet to convert
    it to a shift. (For example, a shift of 'C' means that 'A' goes to 'C',
    which is the same as a shift of 2.)
        
        >>> print(caesar_shift('caesar', 13))
        pnrfne
        >>> print(caesar_shift('CAESAR', 'C'))
        RPTHPG

    """
    if isinstance(offset, str):
        offset = ord(offset.lower()) - ASCII_a

    shifted = [shift_letter(ch, offset) for ch in text]
    return ''.join(shifted)


def caesar_unshift(text, offset):
    """
    Performs a Caesar shift backwards by the given offset.
    
    If the offset is a letter, it will look it up in the alphabet to convert
    it to a shift. (For example, a shift of 'C' means that 'C' goes to 'A',
    which is the same as a backward shift of 2.)

        >>> print caesar_unshift('DBFTBS TIJGU', 1)
        CAESAR SHIFT
    """
    if isinstance(offset, str):
        offset = ord(offset.lower()) - ASCII_a
    return caesar_shift(text, -offset)


def best_caesar_shift(text, wordlist=WORDS, count=5):
    possibilities = [caesar_shift(text, n) for n in range(26)]
    results = []
    for poss in possibilities:
        results.extend([found + (n,) for found in wordlist.search(poss)])
    return wordlist.show_best_results(results, count=count)

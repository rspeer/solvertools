import numpy as np
from solvertools.normalize import alpha_slug
import re


letter_freqs = np.array([
    0.08331452,  0.01920814,  0.04155464,  0.03997236,  0.11332581,
    0.01456622,  0.02694035,  0.02517641,  0.08116646,  0.00305369,
    0.00930784,  0.05399477,  0.02984008,  0.06982714,  0.06273243,
    0.0287359 ,  0.00204801,  0.07181286,  0.07714659,  0.06561591,
    0.03393991,  0.01232891,  0.01022719,  0.0037979 ,  0.01733258,
    0.00303336
])


def to_proportion(vec):
    return vec / vec.sum()


def letters_to_vec(letters):
    vec = np.zeros(26)
    for letter in letters:
        index = ord(letter) - ord('a')
        vec[index] += 1
    return vec


def alphagram(slug):
    return ''.join(sorted(slug))


def anahash(slug):
    if slug == '':
        return ''
    vec = to_proportion(letters_to_vec(slug))
    anomaly = vec - letter_freqs
    codes = np.flatnonzero(anomaly > 0) + ord('a')
    return bytes(list(codes)).decode('ascii')


VOWELS_RE = re.compile('[aeiouy]')
def consonantcy(slug):
    return VOWELS_RE.sub('', slug)

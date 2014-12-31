# -*- coding: utf-8 -*-
"""
This module contains useful utilities, especially for working with external
files.
"""

import os
import sys
import pickle
import unicodedata


def asciify(text):
    """
    A wonderful function to remove accents from characters, and
    discard other non-ASCII characters. Outputs a string of only ASCII
    characters.

    >>> print(asciify('ædœomycodermis'))
    aedoeomycodermis

    >>> print(asciify('Zürich'))
    Zurich

    >>> print(asciify('-نہیں'))
    -
    """
    # Deal with annoying British vowel ligatures
    text = text.replace('Æ', 'AE').replace('Œ', 'OE')\
               .replace('æ', 'ae').replace('œ', 'oe')
    return unicodedata.normalize('NFKD', text).encode('ASCII', 'ignore').decode('ASCII')


def _build_path(parts):
    "Make a path out of the given path fragments."
    return os.path.sep.join(p for p in parts if p)


def module_path():
    """Figures out the full path of the directory containing this file.
    
    `PACKAGE_DIR` becomes the parent of that directory, which is the root
    of the solvertools package."""
    return os.path.dirname(__file__)


PACKAGE_DIR = os.path.dirname(module_path())


def data_path(path):
    "Get a complete path for a file in the data directory."
    return _build_path([PACKAGE_DIR, 'data', path])


def wordlist_path(path):
    "Get a complete path for a file in the wordlists directory."
    return _build_path([PACKAGE_DIR, 'wordlists', path])


def corpus_path(path):
    "Get a complete path for a file in the corpora directory."
    return _build_path([PACKAGE_DIR, 'corpora', path])


def db_path(path):
    "Get a path for a SQLite database in the data/db directory."
    return _build_path([PACKAGE_DIR, 'data', 'db', path])


# Simple functions for working with pickles.
# For more awesome pickling, see the pickledir below and lib/persist.py.

def pickle_path(path):
    "Get a complete path for a file in the data/pickle directory."
    return _build_path([PACKAGE_DIR, 'data', 'pickle', path])


def load_pickle(path):
    "Load a pickled object, given its file path (instead of an open file)."
    with open(get_picklefile(path)) as infile:
        return pickle.load(infile)


def save_pickle(obj, path):
    "Save a pickled object, given the object and the file path to save to."
    # There's no intuitive order for these arguments, so switch them if
    # necessary.
    if isinstance(obj, str) and not isinstance(path, str):
        obj, path = path, obj
    with open(get_picklefile(path), 'wb') as outfile:
        pickle.dump(obj, outfile)


def file_exists(path):
    "Test whether a given file exists. You must specify the full path."
    return os.access(path, os.F_OK)


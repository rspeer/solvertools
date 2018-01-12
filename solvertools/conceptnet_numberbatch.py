import re
import pandas as pd
import numpy as np
from .normalize import alphanumeric
from solvertools.util import data_path


DOUBLE_DIGIT_RE = re.compile(r'[0-9][0-9]')
DIGIT_RE = re.compile(r'[0-9]')


def replace_numbers(s):
    """
    Replace digits with # in any term where a sequence of two digits appears.

    This operation is applied to text that passes through word2vec, so we
    should match it.
    """
    if DOUBLE_DIGIT_RE.search(s):
        return DIGIT_RE.sub('#', s)
    else:
        return s


def load_labels_and_npy(label_file, npy_file):
    labels = [line.rstrip('\n') for line in open(label_file, encoding='utf-8')]
    npy = np.load(npy_file)
    return pd.DataFrame(npy, index=labels)


def load_numberbatch():
    return load_labels_and_npy(data_path('vectors/english.labels.txt'), data_path('vectors/english.npy'))


def get_vector(frame, label):
    """
    Returns the row of a vector-space DataFrame `frame` corresponding
    to the text `label`.
    """
    label = alphanumeric(label)
    try:
        return frame.loc[label]
    except KeyError:
        # Return a vector of all NaNs
        return pd.Series(index=frame.columns)


def normalize_vec(vec):
    """
    L2-normalize a single vector, as a 1-D ndarray or a Series.
    """
    if isinstance(vec, pd.Series):
        vals = vec.values
    else:
        vals = vec
    vec = vec.astype('f')
    norm = vals.dot(vals) ** .5
    return vec / (norm + 1e-6)


def cosine_similarity(vec1, vec2):
    """
    Get the cosine similarity between two vectors -- the cosine of the angle
    between them, ranging from -1 for anti-parallel vectors to 1 for parallel
    vectors.
    """
    return normalize_vec(vec1).dot(normalize_vec(vec2))


def similar_to_term(frame, term, limit=50):
    vec = get_vector(frame, term)
    most_similar = similar_to_vec(frame, vec, limit)
    if len(most_similar):
        max_val = most_similar.iloc[0]
        most_similar /= max_val
    return most_similar ** 3


def similar_to_vec(frame, vec, limit=50):
    sqnorm = vec.dot(vec)
    if sqnorm == 0.:
        return pd.Series(data=[], index=[], dtype='f')
    similarity = frame.dot(vec.astype('f'))
    return similarity.dropna().nlargest(limit)


def weighted_average(frame, weight_series):
    if isinstance(weight_series, list):
        weight_dict = dict(weight_series)
        weight_series = pd.Series(weight_dict)
    vec = np.zeros(frame.shape[1], dtype='f')

    for label in weight_series.index:
        if label in frame.index:
            val = weight_series.loc[label]
            vec += val * frame.loc[label].values

    return pd.Series(data=vec, index=frame.columns, dtype='f')

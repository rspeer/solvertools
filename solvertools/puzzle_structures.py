from solvertools.wordlist import WORDS
from solvertools.letters import slugify
from solvertools.regextools import regex_index, regex_len
from itertools import permutations


def diagonalize(items):
    """
    Take the diagonal of a list of words. If the diagonal runs off the end
    of a word, raise an IndexError.
    """
    # TODO: work with regexes
    return [items[i][i] for i in range(len(items))]


def brute_force_diagonalize(answers, wordlist=WORDS):
    results = []
    answers = [slugify(word) for word in answers]
    for i, permutation in enumerate(permutations(answers)):
        if i % 1000 == 0:
            print(i)
        try:
            diag = diagonalize(permutation)
        except IndexError:
            continue
        found = wordlist.search(diag, count=1)
        if found:
            logprob, text = found[0]
            results.append((logprob, text))
    return wordlist.show_best_results(results)

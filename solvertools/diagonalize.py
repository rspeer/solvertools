from solvertools.wordlist import WORDS, show_best_results
from solvertools.letters import slugify
from itertools import permutations


def brute_force_diagonalize(answers, wordlist=WORDS):
    results = []
    answers = [slugify(word) for word in answers]
    for i, permutation in enumerate(permutations(answers)):
        if i % 1000 == 0:
            print(i)
        try:
            diag = ''.join(permutation[i][i] for i in range(len(answers)))
        except IndexError:
            continue
        found = wordlist.search(diag, count=1)
        if found:
            logprob, text = found[0]
            results.append((logprob, text))
    return wordlist.show_best_results(results)

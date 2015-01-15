from solvertools.wordlist import WORDS
from solvertools.letters import slugify
from solvertools.regextools import regex_index, regex_len
from itertools import permutations
import csv


class RegexClue:
    """
    A wrapper for answers that are indicated to be regular expressions.
    Such answers are indicated in spreadsheet input by surrounding them with
    slashes.
    """
    def __init__(self, expr):
        self.expr = expr
        self.compiled = re.compile('^' + expr + '$')

    def match(self, text):
        return self.compiled.match(text)

    def resolve(self):
        """
        Get the most likely word that fits this pattern.
        """
        if self.expr == '.+':
            # a shortcut for a common case
            return 'THE'
        found = WORDS.search(self.expr, count=1)
        return found[0][1]

    def __getitem__(self, index):
        return regex_index(self.expr, index)

    def __len__(self):
        return regex_len(self.expr)

    def __str__(self):
        return "/%s/" % self.expr

    def __repr__(self):
        return "RegexClue(%s)" % self.expr


def parse_csv_cell(cell):
    """
    Handle some special syntax. A cell can contain a regex surrounded with
    slashes, in which case it will be interpreted as a regex. Or it can be
    the empty string, in which case it will match any word.
    """
    cell = cell.strip()
    if cell == '':
        return RegexClue('/.+/')
    elif cell.startswith('/') and cell.endswith('/'):
        reg = cell[1:-1]
        return RegexClue(reg)
    else:
        return cell


def parse_csv_row(row):
    return [parse_csv_cell(cell) for cell in row]


def read_csv_string(string):
    reader = csv.reader(string.split('\n'))
    return [parse_csv_row(row) for row in reader]


def read_csv_file(filename):
    with open(filename, encoding='utf-8') as file:
        reader = csv.reader(file)
        return [parse_csv_row(row) for row in reader]


def diagonalize(items):
    """
    Take the diagonal of a list of words. If the diagonal runs off the end
    of a word, raise an IndexError.
    """
    # TODO: work with regexes
    return ''.join([items[i][i] for i in range(len(items))])


def brute_force_diagonalize(answers, wordlist=WORDS, quiet=False):
    """
    Find the most cromulent diagonalization for a set of answers, trying all
    possible orders. See README.md for a cool example of this with 10 answers.

    As a somewhat artificial example, let's suppose we have these seven
    answers from the 2000 metas, but don't remember their order:

        >>> metas = ['benjamins', 'billgates', 'donors', 'luxor', 'mansion', 'miserly', 'realty']
        >>> brute_force_diagonalize(metas)
        Log prob.   Cromulence  Text
        -19.4590    15      MENOROT
        -19.7687    15      BE NOISY
        -19.8360    15      DELLROY
        -20.2949    14      RUN EAST
        -21.2783    13      MIX LAST
        -21.2995    13      MAX LAST
        -21.4100    13      LES LIST
        -21.4436    13      RUN SALT
        -21.4765    13      LAS LAST
        -21.5002    13      BOX STAY
        -22.2196    12      MALORY I
        -22.3016    12      MENOGYN
        -22.3404    12      BUS LIST
        -22.3529    12      LINE TO I
        -22.6054    12      LIN LAST
        -22.9099    12      DEAL ROY
        -22.9215    12      ME NOT AN
        -23.1715    11      RUNS RAY
        -23.2078    11      MUS LAST
        -23.3446    11      BE SO IST
        (-19.458979797825307, 'MENOROT')

    Okay, it actually thinks the best answer is "MENOROT", the plural of
    "menorah". But BE NOISY is in second place. And if that doesn't work,
    you can try to solve the hunt with other strategies such as RUN EAST.
    """
    results = []
    seen = set()
    answers = [slugify(word) for word in answers]
    for i, permutation in enumerate(permutations(answers)):
        if not quiet and i > 0 and i % 10000 == 0:
            print("Tried %d permutations" % i)
        try:
            diag = diagonalize(permutation)
        except IndexError:
            continue
        found = wordlist.search(diag, count=1)
        if found:
            logprob, text = found[0]
            slug = slugify(text)
            if slug not in seen:
                results.append((logprob, text))
                seen.add(slug)
    return wordlist.show_best_results(results)


def resolve(item):
    if isinstance(item, str):
        return item
    else:
        return item.resolve()


def _index_everything_into_everything(grid):
    titles = grid[0]
    ncols = len(titles)
    nrows = len(grid) - 1

    for sort_col in [None] + list(range(ncols)):
        if sort_col is None:
            ordered = grid[1:]
        else:
            sort_keys = [(row, resolve(grid[sort_col][row])) for row in range(1, nrows + 1)]
            sort_keys.sort(key=lambda x: x[1])
            ordered = [grid[row] for row, key in sort_keys]

        for indexed_col in range(ncols):
            items = [grid_row[indexed_col] for grid_row in ordered]
            yield diagonalize(items)


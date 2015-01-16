from solvertools.util import data_path
from solvertools.wordlist import WORDS
from solvertools.normalize import slugify, alphanumeric
from solvertools.regextools import regex_index, regex_len
from itertools import permutations
from natsort import natsorted
import csv
import re

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

    def __eq__(self, other):
        if type(self) != type(other):
            return False
        return self.expr == other.expr

    def __ne__(self, other):
        return not (self == other)

    def __str__(self):
        if self.expr == '.+':
            return "ANY"
        else:
            return "/%s/" % self.expr

    def __repr__(self):
        if self.expr == '.+':
            return "ANY"
        else:
            return "RegexClue(%r)" % self.expr


ANY = RegexClue('.+')


def parse_csv_cell(cell):
    """
    Handle some special syntax. A cell can contain a regex surrounded with
    slashes, in which case it will be interpreted as a regex. Or it can be
    the empty string, in which case it will match any word.
    """
    cell = cell.strip()
    if cell == '':
        return ANY
    elif cell.startswith('/') and cell.endswith('/'):
        reg = cell[1:-1]
        return RegexClue(reg)
    else:
        return alphanumeric(cell)


def parse_csv_row(row):
    return [parse_csv_cell(cell) for cell in row]


def read_csv_string(string):
    reader = csv.reader(string.split('\n'))
    return [parse_csv_row(row) for row in reader if row]


def read_csv_file(filename):
    with open(filename, encoding='utf-8') as file:
        reader = csv.reader(file, dialect='excel')
        return [parse_csv_row(row) for row in reader]


def diagonalize(items):
    """
    Take the diagonal of a list of words. If the diagonal runs off the end
    of a word, raise an IndexError.
    """
    return ''.join([items[i][i] for i in range(len(items))])


def acrostic(items):
    """
    Take the acrostic of a list of words -- the first letter of each word.
    """
    return ''.join([item[0] for item in items])


def brute_force_diagonalize(answers, wordlist=WORDS, quiet=False):
    """
    Find the most cromulent diagonalization for a set of answers, trying all
    possible orders. See README.md for a cool example of this with 10 answers.

    As a somewhat artificial example, let's suppose we have these seven
    answers from the 2000 metas, but don't remember their order:

        >>> metas = ['benjamins', 'billgates', 'donors', 'luxor', 'mansion', 'miserly', 'realty']
        >>> brute_force_diagonalize(metas)[0]   # doctest: +NORMALIZE_WHITESPACE
        Log prob.   Cromulence  Text    Info
        -19.4797    15.3    MENOROT 
        -19.8101    14.9    BE NOISY    
        -19.9530    14.8    DELLROY 
        -20.3282    14.4    RUN EAST    
        -21.3154    13.3    MIX LAST    
        -21.3333    13.3    MAX LAST    
        -21.4507    13.2    LES LIST    
        -21.4619    13.1    RUN SALT    
        -21.5178    13.1    LAS LAST    
        -21.5394    13.1    BOX STAY    
        -21.6241    13.0    MENOGYN 
        -22.2569    12.3    MALORY I    
        -22.3489    12.2    BUS LIST    
        -22.4141    12.1    LINE TO I   
        -22.6454    11.9    LIN LAST    
        -22.9501    11.5    DEAL ROY    
        -22.9835    11.5    ME NOT AN   
        -23.2088    11.2    RUNS RAY    
        -23.2311    11.2    MUS LAST    
        -23.3860    11.1    BE SO IST   
        (-19.479680042263826, 'MENOROT', None)

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
                results.append((logprob, text, None))
                seen.add(slug)
    return wordlist.show_best_results(results)


def resolve(item):
    """
    Get a non-ambiguous string for each item. If it's uncertain, pick a word,
    even if it's just THE. This lets us at least try a sort order, although
    uncertain answers may be out of place.
    """
    if isinstance(item, RegexClue):
        return item.resolve()
    else:
        return item


def _index_by(indexee, index):
    if isinstance(index, RegexClue):
        if index == ANY:
            return '.'
        else:
            raise IndexError
    else:
        num = int(index)
        return indexee[num - 1]


def _try_indexing(grid, titles):
    ncols = len(titles)
    nrows = len(grid)

    for sort_col in [None] + list(range(ncols)):
        if sort_col is None:
            ordered = grid
            sort_title = None
        else:
            sort_keys = [(row, resolve(grid[row][sort_col])) for row in range(nrows)]
            sorted_keys = natsorted(sort_keys, key=lambda x: x[1])
            ordered = [grid[row] for row, key in sorted_keys]
            sort_title = titles[sort_col]

        for indexed_col in range(ncols):
            column = [grid_row[indexed_col] for grid_row in ordered]
            try:
                info = (sort_title, titles[indexed_col], '1ST')
                yield acrostic(column), info
                info = (sort_title, titles[indexed_col], 'DIAG')
                yield diagonalize(column), info
            except IndexError:
                pass

            for indexing_col in range(ncols):
                if indexing_col == indexed_col:
                    continue
                indices = [grid_row[indexing_col] for grid_row in ordered]
                try:
                    letters = [_index_by(cell, index_cell)
                               for (cell, index_cell) in zip(column, indices)]
                    index_result = ''.join(letters)
                    info = (sort_title, titles[indexed_col], titles[indexing_col])
                    yield index_result, info
                except (IndexError, ValueError):
                    pass


def readable_indexing(info):
    sortby, indexed, indexer = info
    if sortby is None:
        sort_part = "Don't sort"
    else:
        sort_part = "Sort by %r" % sortby

    if indexer == '1ST':
        index_part = "take the first letters of"
    elif indexer == 'DIAG':
        index_part = "take the diagonal of"
    else:
        index_part = "index by %r into" % indexer

    return "%s, %s %r" % (sort_part, index_part, indexed)


DIGITS_RE = re.compile(r'[0-9]')


def index_all_the_things(grid, count=20):
    """
    Try every combination of sorting by one column and indexing another column,
    possibly by the numeric values in a third column.
    """
    titles = grid[0]
    ncols = len(titles)
    data = []
    for row in grid[1:]:
        if len(row) < ncols:
            row = row + [ANY] * (ncols - len(row))
        data.append(row)
    best_logprob = -1000
    results = []
    seen = set()
    for pattern, info in _try_indexing(data, titles):
        if DIGITS_RE.search(pattern):
            continue
        found = WORDS.search(pattern, count=5)
        for logprob, text in found:
            if text not in seen:
                seen.add(text)
                description = readable_indexing(info)
                results.append((logprob, text, description))
                if logprob > best_logprob:
                    print("\t%2.2f\t%s\t%s" % (logprob, text, description))
                    best_logprob = logprob
    print()
    return WORDS.show_best_results(results, count)


def indexing_demo():
    filename = data_path('test/soylent_partners.csv')
    grid = read_csv_file(filename)
    index_all_the_things(grid)


from solvertools.wordlist import combine_wordlists, build_extras


def build_scrabblish_list():
    """
    Build a list of words that have the "Scrabble nature", which is to say that
    they'd be officially acceptable in a word game according to some tournament
    rules.

    This wordlist combines the wordlists whose data is publicly available. As
    a result, it's only updated to 2007, and it's not authoritative.
    """
    combine_wordlists([
        ('enable', 1),
        ('twl06', 1),
        ('csw-apr07', 1)
    ], 'scrab')


if __name__ == '__main__':
    build_scrabblish_list()
    build_extras('scrab')

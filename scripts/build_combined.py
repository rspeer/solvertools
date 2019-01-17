from solvertools.wordlist import combine_wordlists, build_extras


def build_combined_list():
    combine_wordlists([
        ('google-books', 1),
        ('enable', 10000),
        ('twl06', 10000),
        ('csw-apr07', 10000),
        ('wikipedia-en-links', 10000),
#        ('wikipedia-en-titles', 1),
        ('wordfreq', 50000),
        ('wordnet', 100000),
        ('npl-allwords', 100)
    ], 'combined')


if __name__ == '__main__':
    build_combined_list()
    build_extras('combined')

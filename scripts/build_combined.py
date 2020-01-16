from solvertools.wordlist import combine_wordlists, build_extras


def build_combined_list():
    combine_wordlists([
        ('google-books', 1),
        ('enable', 100),
        ('twl06', 100),
        ('csw-apr07', 1000),
        ('wikipedia-en-links', 1000),
#        ('wikipedia-en-titles', 1),
        ('wordfreq', 10000),
        ('wordnet', 10000),
        ('npl-allwords', 10)
    ], 'combined')


if __name__ == '__main__':
    build_combined_list()
    build_extras('combined')

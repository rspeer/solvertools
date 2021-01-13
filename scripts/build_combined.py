from solvertools.wordlist import combine_wordlists, build_extras


def build_combined_list():
    combine_wordlists([
        ('google-books-1grams', 1),
        ('google-books-phrases', 1),
        ('enable', 1000),
        ('twl06', 1000),
        ('csw2019', 10000),
        ('wikipedia-en-links', 10000),
#        ('wikipedia-en-titles', 1),
        ('wordfreq', 100000),
        ('wordnet', 100000),
        ('npl-allwords', 1000)
    ], 'combined')


if __name__ == '__main__':
    build_combined_list()
    build_extras('combined')

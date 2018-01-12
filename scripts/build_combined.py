from solvertools.wordlist import combine_wordlists, build_extras


def build_combined_list():
    combine_wordlists([
        ('google-books', 1),
        ('enable', 10),
        ('twl06', 10),
        ('csw-apr07', 10),
        ('wikipedia-en-links', 100),
        ('wikipedia-en-titles', 1),
        ('wordfreq', 1),
        ('wordnet', 1000),
        ('npl-allwords', 1),
        ('wordfreq', 50)
    ], 'combined')


if __name__ == '__main__':
    build_combined_list()
    build_extras('combined')

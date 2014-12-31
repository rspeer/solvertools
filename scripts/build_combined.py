from solvertools.wordlist import combine_wordlists, build_extras


def build_combined_list():
    combine_wordlists([
        ('google-books', 1),
        ('enable', 25),
        ('twl06', 25),
        ('wikipedia-en-titles', 100),
        ('wordnet', 1000),
        ('npl-allwords', 10)
    ], 'combined')


if __name__ == '__main__':
    build_combined_list()
    build_extras('combined')

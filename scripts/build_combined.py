from solvertools.wordlist import combine_wordlists


def build_combined_list():
    combine_wordlists([
        ('google-books', 1),
        ('enable', 250),
        ('twl06', 250),
        ('wikipedia-en-titles', 800),
        ('wordnet', 10000),
        ('npl-allwords', 100)
    ], 'combined')


if __name__ == '__main__':
    build_combined_list()

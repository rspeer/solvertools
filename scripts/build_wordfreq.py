import string
import wordfreq


VALID_LETTERS = string.ascii_uppercase + "'"

for word in wordfreq.top_n_list('en', 1000000, 'large'):
    word = word.upper()
    if all(ch in VALID_LETTERS for ch in word):
        freq = int(wordfreq.word_frequency(word, 'en', 'large') * 1e9)
        print("{},{}".format(word, freq))

"""
Some NLP code designed to answer the question: "How much does this text look
like reasonable English?"
"""

from solvertools.lib.probability import FreqDist, LidstoneProbDist, \
                                        LaplaceProbDist, MLEProbDist
from solvertools.lib.tokenize import tokenize
from solvertools.model.numbers import number_logprob, is_numeric
from solvertools.model.answer_reader import answer_reader
from solvertools.util import load_pickle, save_pickle, get_picklefile, \
                             file_exists
from solvertools.regex import is_regex, regex_pieces, regex_sequence
from solvertools import wordlist
import random, string, logging
import numpy as np
logger = logging.getLogger(__name__)

# Loaded language models go here. (TODO: more elegant code for this?)
CACHE = {}


def scan_ngrams(seq, n=2):
    """
    Given a sequence, extract all n-grams of a given length from it.
    """
    for i in xrange(len(seq)-n+1):
        fragment = seq[i:i+n]
        yield fragment

class LanguageModel(object):
    """
    A base class of language models. Right now there's only one subclass,
    but this allows for the possibility of others.
    """
    pass

# TODO: make these configurable
MINIMUM_LOGPROB = -1000000.0
SPLIT_LOGPROB = -10.0

class WordListModel(LanguageModel):
    """
    A language model that extrapolates from a list of words in that language.

    Given appropriate wordlists, this could easily be extended to other
    languages besides English.
    """
    version = 4
    def __init__(self, name, wordlist):
        pickle_name = '%s.model.%s.pickle' % (name, self.version)
        if file_exists(get_picklefile(pickle_name)):
            self._load_from_pickle(pickle_name)
        else:
            self.wordlist = wordlist
            letter_freq = FreqDist()        # letter unigram frequencies
            bigram_freq = FreqDist()        # letter bigram frequencies
            word_freq = FreqDist()          # word frequencies

            if not wordlist.words: wordlist.load()
            for word, freq in wordlist.iteritems():
                # store the word frequency in the frequency distribution
                word_freq.inc(word, freq)
                for letter in ' '+word:
                    letter_freq.inc(letter)
                for ngram in scan_ngrams(' '+word+' ', 2):
                    # record the n-gram frequencies of letters
                    bigram_freq.inc(ngram, freq)
            
            self.letter_dist = MLEProbDist(letter_freq)
            self.bigram_dist = LidstoneProbDist(bigram_freq, 1000)
            self.word_dist = LaplaceProbDist(word_freq)
            
            self._save_pickle(pickle_name)
        
    def _load_from_pickle(self, filename):
        logger.info('Loading %s' % filename)
        (self.wordlist, self.letter_dist, self.bigram_dist,
        self.word_dist) = load_pickle(filename)

    def _save_pickle(self, filename):
        logger.info('Saving %s' % filename)
        stuff = (self.wordlist, self.letter_dist, self.bigram_dist,
        self.word_dist)
        save_pickle(stuff, filename)
    
    def letters_logprob(self, word):
        """
        Get the relative probability of this word according to the letter
        bigrams in it.
        """
        word = self.wordlist.convert(word)
        logprob = self.letter_dist.logprob(' ')
        if not word: return logprob
        for bigram in scan_ngrams(' '+word+' ', 2):
            # multiply p by the probability of the bigram given its first
            # character
            if bigram[0] in self.letter_dist.freqdist():
                logprob += self.bigram_dist.logprob(bigram)
                logprob -= self.letter_dist.logprob(bigram[0])
        return logprob

    def word_logprob(self, word):
        """
        Get the relative probability of this word given its appearance in
        a wordlist.
        """
        if is_regex(word):
            word, freq = self.wordlist.best_match(word)
            if word is None:
                return MINIMUM_LOGPROB

        if is_numeric(word):
            return number_logprob(int(word))
        else:
            if word in self.wordlist:
                return self.word_dist.logprob(self.wordlist.convert(word))
            elif word not in self.wordlist:
                return MINIMUM_LOGPROB

    def word_match_logprob(self, word):
        """
        Get the relative probability of this word, or non-deterministic regex,
        given its appearance in a wordlist. Returns the matched word and its
        log probability as a tuple.
        """
        if is_regex(word):
            word, freq = self.wordlist.best_match(word)
            word = unicode(word)
            if not word:
                return (u'#', MINIMUM_LOGPROB)

        if is_numeric(word):
            return (word, number_logprob(int(word)))
        else:
            if word in self.wordlist:
                return (word, self.word_dist.logprob(self.wordlist.convert(word)))
            elif word not in self.wordlist:
                return (u'#', MINIMUM_LOGPROB)

    def split_words(self, text):
        """
        Find the best English text to match the given string by inserting
        spaces and filling blanks.

            >>> en = get_model('en')
            >>> en.split_words('RGBOFRELIQUARY')[0]
            u'RGB OF RELIQUARY'
            >>> split_words('/.U..E..F...../')[0]
            u'NUCLEAR FUSION'
        """
        pieces = regex_pieces(text)
        textlen = len(pieces)
        best_matches = [u'#'] * (textlen + 1)

        # start with very negative log probabilities
        best_logprobs = np.ones((textlen + 1,)) * -10000

        best_matches[0] = u''
        best_logprobs[0] = 0.0
        for right in xrange(1, textlen+1):
            for left in xrange(right):
                left_text = best_matches[left]
                left_logprob = best_logprobs[left]
                right_text = regex_sequence(pieces[left:right])
                right_match, right_logprob = self.word_match_logprob(right_text)
                if left_text != u'':
                    combined_text = left_text + u' ' + right_match
                    combined_logprob = (left_logprob + right_logprob
                                        + SPLIT_LOGPROB)
                else:
                    combined_logprob = right_logprob
                    combined_text = right_match

                if combined_logprob > best_logprobs[right]:
                    best_logprobs[right] = combined_logprob
                    best_matches[right] = combined_text
                    assert combined_text != u''
        return best_matches[-1], best_logprobs[-1]

    def text_logprob(self, text):
        """
        Get the relative probability of a text, inserting spaces when
        necessary.
        """
        text = text.replace('-', ' ')
        words = [word for word in tokenize(text).split() if
        self.wordlist.convert(word)]
        logprob = 0.0
        for word in words:
            logprob += self.split_words(word)[1]
        return logprob

    def text_goodness(self, text):
        """
        Get the overall "goodness" of a text, which adjusts its log probability
        for its length.
        """
        return self.text_logprob(text) / len(text)

def unigram_sampler(model):
    """
    Extract random letters from a unigram distribution.

    This is used for generating negative examples for the answer recognizer.
    """
    p = random.random()
    for let in string.uppercase:
        if let == ' ':
            continue
        p -= model.letter_dist.prob(let)
        if p < 0:
            return let
    return unigram_sampler(model)

def unigram_replace(char, model):
    """
    Given a phrase, replace its alphabetic characters with random letters,
    yielding nonsense that looks like the phrase.
    """
    if char == ' ': return char
    else: return unigram_sampler(model)

def text_goodness(text):
    """
    As we're almost always expecting English text, this function makes sure
    the English model is loaded and evaluates the goodness of text.
    """
    english = get_english_model()
    return english.text_goodness(text)

def split_words(text):
    """
    As we're almost always expecting English text, this function makes sure
    the English model is loaded and finds the most likely multi-word split
    and its goodness value.
            
        >>> split_words('RGBOFRELIQUARY')[0]
        u'RGB OF RELIQUARY'
        >>> split_words('/.U..E..F...../')[0]
        u'NUCLEAR FUSION'
    """
    english = get_english_model()
    return english.split_words(text)

LANGUAGE_DEFS = {
    # add definitions here of the form:
    # key: (language_name, wordlist)
    'en': ('english', wordlist.COMBINED_WORDY),
    'english': ('english', wordlist.COMBINED_WORDY),
    'la': ('latin', wordlist.LATIN),
    'latin': ('latin', wordlist.LATIN),
    'chaos': ('chaotic', wordlist.CHAOTIC),
    'chaotic': ('chaotic', wordlist.CHAOTIC),
    'chaotian': ('chaotic', wordlist.CHAOTIC),
}

def get_model(lcode):
    lcode = lcode.lower()
    if lcode not in LANGUAGE_DEFS:
        raise KeyError(
          "There's no model defined for the language '%s' in language_model.py."
          "\nThe defined models are: %s" % (LANGUAGE_DEFS.keys(),)
        )
    language_name, lang_wordlist = LANGUAGE_DEFS[lcode]
    if language_name not in CACHE:
        CACHE[language_name] = WordListModel(language_name, lang_wordlist)
    return CACHE[language_name]

def get_english_model():
    """
    Load the cached English language model.
    """
    return get_model('en')

def demo(omit_spaces=True):
    """
    Demonstrate this module's ability to distinguish real Mystery Hunt answers
    from gibberish.
    """
    the_model = get_english_model()
    results = []
    for year in range(2004, 2009):
        for answer in answer_reader(year):
            if omit_spaces:
                answer = answer.replace(' ', '').replace('-', '')\
                  .replace('.', '').replace(',', '').replace("'", '')
            results.append((the_model.text_goodness(answer), answer, True))
            fakeanswer = ''.join(unigram_replace(x, the_model) for x in answer)
            results.append((the_model.text_goodness(fakeanswer),
                            fakeanswer, False))
    usefulness = 0.0
    for score, result, good in sorted(results):
        if good:
            usefulness += score
        else:
            usefulness -= score
        print "%s\t%5.5f %s" % (good, score, result)
    print usefulness

if __name__ == '__main__':
    demo()

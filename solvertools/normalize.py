from unidecode import unidecode
import re


NONALPHA_RE = re.compile(r'[^a-z]')
NONALPHANUM_RE = re.compile(r'[^a-z0-9]')
DIGIT_RE = re.compile(r'[0-9]')
PUNCTUATION_RE = re.compile(r"[^A-Za-z0-9' ]")
PARENTHESIS_RE = re.compile(r'[_ ]\(.*\)')
SPACES_RE = re.compile(r'  +')

def slugify(text):
    """
    Return a text as a sequence of letters. No spaces, digits, hyphens,
    or apostrophes. This kind of reduced form of text is sometimes called a
    "slug", and that's the term we use for it throughout solvertools.
    """
    return NONALPHA_RE.sub('', text.lower())


def alphanumeric(text):
    return NONALPHANUM_RE.sub('', text.lower())


def sanitize(text):
    """
    Return a text as a sequence of letters, digits, apostrophes, and spaces.
    """
    return SPACES_RE.sub(' ', PUNCTUATION_RE.sub(' ', text))


def unspaced_lower(text):
    """
    Remove spaces and apostrophes from text. This is a gentler form of
    `slugify` that preserves regex operators, for example.
    """
    return text.replace(' ', '').replace("'", '').lower()


# We don't want to translate every number, just the ones that have single words.
NUMERALS = {
    '0': 'zero', '1': 'one', '2': 'two', '3': 'three', '4': 'four', '5': 'five', '6': 'six',
    '7': 'seven', '8': 'eight', '9': 'nine', '10': 'ten', '11': 'eleven', '12': 'twelve',
    '13': 'thirteen', '14': 'fourteen', '15': 'fifteen', '16': 'sixteen', '17': 'seventeen',
    '18': 'eighteen', '19': 'nineteen', '20': 'twenty', '30': 'thirty', '40': 'forty',
    '50': 'fifty', '60': 'sixty', '70': 'seventy', '80': 'eighty', '90': 'ninety',
    '1st': 'first', '2nd': 'second', '3rd': 'third', '4th': 'fourth', '5th': 'fifth',
    '6th': 'sixth', '7th': 'seventh', '8th': 'eighth', '9th': 'ninth', '10th': 'tenth',
    '11th': 'eleventh', '12th': 'twelfth', '13th': 'thirteenth', '14th': 'fourteenth',
    '15th': 'fifteenth', '16th': 'sixteenth', '17th': 'seventeenth', '18th': 'eighteenth',
    '19th': 'nineteenth', '20th': 'twentieth'
}


def transform_simple_numbers(word):
    if word in NUMERALS:
        return NUMERALS[word]
    else:
        if DIGIT_RE.search(word):
            return '###'
        else:
            return word


def fix_entities(text):
    return text.replace('&amp;', '&').replace('&lt;', '<').replace('&gt;', '>').replace('&quot;', '"')


def normalize_wp_link(text):
    text = text.split('#')[0]
    text = PARENTHESIS_RE.sub('', text)
    text = unidecode(text)
    text = fix_entities(text)
    text = text.replace("\\'", "'").replace('-', ' ').replace('_', ' ').replace('&', ' AND ').replace('/', ' ').replace('List of ', '').replace('History of ', '')
    text = PUNCTUATION_RE.sub('', text)
    words = [transform_simple_numbers(word).upper() for word in text.split()]
    return SPACES_RE.sub(' ', ' '.join(words)).strip()


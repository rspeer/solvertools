import re
NONALPHA_RE = re.compile(r'[^a-z]')


def alpha_slug(text):
    """
    Return a text as a sequence of letters. No spaces, digits, hyphens,
    or apostrophes.
    """
    return NONALPHA_RE.sub('', text.lower())


def unspaced_lower(text):
    """
    Remove spaces and apostrophes from text. This is a gentler form of
    `alpha_slug` that preserves regex operators, for example.
    """
    return text.replace(' ', '').replace("'", '').lower()

import re
NONALPHA_RE = re.compile(r'[^a-z]')


def slugify(text):
    """
    Return a text as a sequence of letters. No spaces, digits, hyphens,
    or apostrophes. This kind of reduced form of text is sometimes called a
    "slug", and that's the term we use for it throughout solvertools.
    """
    return NONALPHA_RE.sub('', text.lower())


def unspaced_lower(text):
    """
    Remove spaces and apostrophes from text. This is a gentler form of
    `slugify` that preserves regex operators, for example.
    """
    return text.replace(' ', '').replace("'", '').lower()

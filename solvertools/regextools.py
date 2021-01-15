"""
Wacky tools for slicing and dicing regexes.
"""
from sre_parse import parse, CATEGORIES, SPECIAL_CHARS, SubPattern
from sre_constants import MAXREPEAT   # this is a quantity, not an enum
from sre_constants import (
    MAX_REPEAT, LITERAL, IN, CATEGORY, ANY, SUBPATTERN, BRANCH,
    AT_BEGINNING, AT_END, NOT_LITERAL, NEGATE
)
import re


REVERSE_CATEGORIES = {}
for key, value in CATEGORIES.items():
    REVERSE_CATEGORIES[str(value)] = key

REGEX_RE = re.compile(r"[\[\]+.(){}|]")


def regex_sequence(strings):
    """
    Combine regexes or plain strings together in a sequence. This operation
    undoes :func:`regex_pieces`.

        >>> regex_sequence(['foo|bar', 'baz'])
        '(foo|bar)baz'
        >>> regex_sequence(['a', 'b'])
        'ab'
    """
    pattern = []
    for s in strings:
        parsed = parse(s)
        pattern.extend(_wrap_branches(parsed))
    return unparse(pattern)


def is_exact(string):
    """
    Indicates whether this is a plain string, with no special regex
    characters, so it will always match exactly.

        >>> is_exact('foo')
        True
        >>> is_exact('')
        True
        >>> is_exact('a|b')
        False
        >>> is_exact('(foo)')
        False
        >>> is_exact('ba[rz]')
        False
    """
    return not REGEX_RE.search(string)


def _wrap_branches(struct):
    result = []
    for op, data in struct:
        if op == BRANCH:
            result.append( (SUBPATTERN, (1, [(op, data)])) )
        else:
            result.append( (op, data) )
    return result


def regex_len(regex):
    """
    Returns a tuple of the minimum and maximum possible length string that a
    regex will match. Returns MAXREPEAT if a match can be very or infinitely
    long.

        >>> regex_len('test')
        (4, 4)
        >>> regex_len('t.st')
        (4, 4)
        >>> regex_len('.*')
        (0, MAXREPEAT)
        >>> regex_len('fo?o')
        (2, 3)
        >>> regex_len('mo{2,7}')
        (3, 8)
        >>> regex_len('(foo)+')
        (3, MAXREPEAT)
        >>> regex_len('s?e?q?u?e?n?c?e?')
        (0, 8)
    """
    return _regex_len_pattern(parse(regex))


def regex_pieces(regex):
    """
    Separates a regex into independent pieces.

        >>> regex_pieces('[abc]de+')
        ['[abc]', 'd', 'e+']
    """
    result = []
    for piece in parse(regex):
        result.append(unparse([piece]))
    return result


def _regex_len_pattern(pattern):
    "Returns the minimum and maximum length of a parsed regex pattern."
    assert isinstance(pattern, (list, SubPattern)), type(pattern)
    lo = hi = 0
    for op, data in pattern:
        if op in (LITERAL, IN, CATEGORY, ANY):
            sub_lo = sub_hi = 1
        elif op == SUBPATTERN:
            sub_lo, sub_hi = _regex_len_pattern(data[-1])
        elif op == BRANCH:
            sub_lo, sub_hi = _regex_len_branch(data[-1])
        elif op == MAX_REPEAT:
            sub_lo, sub_hi = _regex_len_repeat(data)
        elif op == AT_BEGINNING:
            sub_lo = sub_hi = 0
        elif op == AT_END:
            sub_lo = sub_hi = 0
        elif op == NOT_LITERAL:
            sub_lo = sub_hi = 1
        elif op == NEGATE:
            sub_lo = sub_hi = 0
        else:
            raise ValueError(
                "I don't know what to do with this regex operation: %s %s, %s"
                % (op, type(op), data)
            )
        lo += sub_lo
        hi += sub_hi
    return lo, min(MAXREPEAT, hi)


def _regex_len_branch(branches):
    """
    Returns the minimum and maximum length of a regex branch.

    This does not take into account the fact that some lengths in between may
    be impossible.
    """
    lo = MAXREPEAT
    hi = 0
    for branch in branches:
        sub_lo, sub_hi = _regex_len_pattern(branch)
        lo = min(lo, sub_lo)
        hi = max(hi, sub_hi)
    return lo, hi


def _regex_len_repeat(data):
    """
    Return the minimum and maximum length of a repeating expression.
    """
    min_repeat, max_repeat, pattern = data
    lo, hi = _regex_len_pattern(pattern)
    return min_repeat * lo, min(MAXREPEAT, max_repeat * hi)


def round_trip(regex):
    """
    Send a regex through the parser and unparser, possibly simplifying it.
    """
    return unparse(parse(regex))


def regex_index(regex, index):
    """
    Index into a regex, returning a smaller regex of the things that match
    in that position.
        
        >>> regex_index('test', 0)
        't'
        >>> regex_index('t?est', 0)
        '[te]'
        >>> regex_index('fa(la){2,}', 2)
        'l'
        >>> regex_index('fa(la){2,}', 6)
        'l'
        >>> regex_index('.*', 99)
        '.'
    """
    choices = _regex_index_pattern(parse(regex), index)
    if len(choices) == 0:
        raise IndexError
    elif len(choices) == 1:
        return unparse(choices[0])
    else:
        return round_trip(unparse((BRANCH, (None, choices))))


def _regex_index(struct, index):
    if isinstance(struct, (list, SubPattern)):
        return _regex_index_pattern(struct, index)
    else:
        opcode, data = struct
        if opcode in (LITERAL, IN, CATEGORY, ANY, NOT_LITERAL):
            if index == 0:
                return [[struct]]
            else:
                return []
        elif opcode == SUBPATTERN:
            return _regex_index_pattern(data[-1], index)
        elif opcode == BRANCH:
            return _regex_index_branch(data[-1], index)
        elif opcode == MAX_REPEAT:
            return _regex_index_repeat(data, index)
        elif opcode == NEGATE:
            print(struct)
            raise NotImplementedError
        else:
            raise ValueError("I don't know what to do with this regex: "
                             + str(struct))


def regex_slice(expr, start, end):
    """
    Get a slice of a regex by calling regex_index on each index.

    Note that this can return expressions that are overly general: for example,
    it can mix characters from both branches of a regex. Being more specific
    than that would take more work.

        >>> regex_slice('test', 0, 1)
        't'
        >>> regex_slice('t?est', 0, 2)
        '[te][es]'
        >>> regex_slice('mo+', 3, 8)
        'ooooo'

    """
    if start < 0 or end < 0:
        raise NotImplementedError("Can't take negative slices of a regex yet")
    result = ''
    for index in range(start, end):
        choices = _regex_index_pattern(parse(expr), index)
        if len(choices) == 0:
            return None
        elif len(choices) == 1:
            regex = unparse(choices[0])
            result += regex
        else:
            regex = round_trip(unparse((BRANCH, (None, choices))))
            if '|' in regex:
                result += '(%s)' % (regex,)
            else:
                result += regex
    return result


def _regex_index_branch(branches, index):
    choices = []
    for branch in branches:
        choices.extend(_regex_index_pattern(branch, index))
    return choices


def _regex_index_repeat(data, index):
    min_repeat, max_repeat, pattern = data
    lo, hi = _regex_len_pattern(pattern)
    lo = max(lo, 1)  # we don't care about things that take up 0 characters
    max_relevant_repeat = min(index // lo + 1, max_repeat)
    newpattern = list(pattern) * max_relevant_repeat
    return _regex_index_pattern(newpattern, index)


def _regex_index_pattern(pattern, index):
    if isinstance(index, slice):
        # we might come up with a clever way to do this
        raise NotImplementedError

    if index < 0:
        # This is an easier case that's still not done yet
        raise NotImplementedError

    lo_counter = hi_counter = 0
    choices = []
    for sub in pattern:
        lo, hi = _regex_len_pattern([sub])
        next_lo = lo_counter + lo
        next_hi = hi_counter + hi
        if index < lo_counter:
            break
        elif lo_counter <= index < next_hi:
            for offset in range(lo_counter, hi_counter+1):
                sub_index = index - offset
                if sub_index >= 0:
                    choices.extend(_regex_index(sub, sub_index))
        lo_counter, hi_counter = next_lo, next_hi
    
    # if any of the choices is 'any', it overrules everything else.
    for choice in choices:
        # make sure our choices are single characters
        assert len(choice) == 1
        op, data = choice[0]
        if op == 'any':
            return [choice]
    return choices


def unparse(struct):
    if isinstance(struct, list):
        return ''.join(unparse(x) for x in struct)        
    if isinstance(struct, SubPattern):
        return ''.join(unparse(x) for x in struct)
    elif isinstance(struct, tuple):
        opcode, data = struct
        func_name = '_unparse_%s' % str(opcode).lower()
        if str(struct) in REVERSE_CATEGORIES:
            return REVERSE_CATEGORIES[str(struct)]
        elif func_name in globals():
            unparser = globals()[func_name]
            return unparser(data)
        else:
            raise ValueError("I don't know what to do with this regex: "
                             + str(struct))
    else:
        raise TypeError("%s doesn't belong in a regex structure" % struct)


def _unparse_literal(data):
    char = chr(data)
    if char in SPECIAL_CHARS:
        return '\\' + char
    else:
        return char


def _unparse_any(data):
    return '.'


def _unparse_range(data):
    start, end = data
    return chr(start) + '-' + chr(end)


def _unparse_in(data):
    return '[' + unparse(data) + ']'


def _unparse_category(data):
    return REVERSE_CATEGORIES[data]


def _unparse_subpattern(data):
    return '(' + unparse(data[-1]) + ')'


def _unparse_branch(data):
    return '|'.join(unparse(branch) for branch in data[-1])


def _unparse_max_repeat(data):
    lo, hi, value = data
    if lo == 0 and hi == MAXREPEAT:
        symbol = '*'
    elif lo == 0 and hi == 1:
        symbol = '?'
    elif lo == 1 and hi == MAXREPEAT:
        symbol = '+'
    else:
        symbol = '{%d,%d}' % (lo, hi)
    return unparse(value) + symbol


def _unparse_at(data):
    if data == AT_BEGINNING:
        return '^'
    elif data == AT_END:
        return '$'
    else:
        raise ValueError


def _unparse_at_beginning(data):
    return '^'


def _unparse_at_end(data):
    return '$'


def _unparse_not_literal(data):
    return '[^{}]'.format(chr(data))


def _unparse_negate(data):
    return '^'
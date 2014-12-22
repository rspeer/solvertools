from math import log, pow


def is_numeric(word):
    try:
        int(word)
        return True
    except ValueError:
        return False


def lg(n):
    return log(n) / log(2)


def number_logprob(n):
    """
    A kind of arbitrary power-law distribution for how common a number should
    be. Obeys Benford's Law and all that. But keep in mind that I completely
    made it up. --Rob
    """
    if n < 0: return -2+number_logprob(-n)
    expdist = -lg(32+n)*2
    if n >= 10: expdist -= 1
    if n > 26: expdist -= 1
    if 1066 <= n < 1900: expdist += 2   # historical dates
    if 1900 <= n < 1981: expdist += 4   # most of the 20th century
    if 1981 <= n <= 2100: expdist += 6  # the Mystery Hunt era
    return expdist


# When you sum over this distribution, you get about a 1/50 chance that an
# arbitrary word is a number.
def demo():
    print(number_logprob(0))
    print(number_logprob(3))
    print(number_logprob(42))
    print(number_logprob(983))
    print(number_logprob(1983))
    print(1/sum(pow(2, number_logprob(n)) for n in range(-100000, 100000)))

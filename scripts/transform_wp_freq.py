import sys
import re
from solvertools.normalize import normalize_wp_link
assert sys.getdefaultencoding() == 'utf-8'


LINE_RE = re.compile("^ *([0-9]+) (.*)$")


def transform():
    for line in sys.stdin:
        line = line.rstrip()
        match = LINE_RE.match(line)
        if match:
            freq = int(match.group(1))
            if freq == 1:
                break
            name = normalize_wp_link(match.group(2)).strip()

            if name and '###' not in name:
                print('%s,%d' % (name, freq))


transform()

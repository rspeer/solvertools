#!/usr/bin/env python3
import sys
import re
from solvertools.normalize import normalize_wp_link

DATE_RE = re.compile(r'(January|February|March|April|May|June|July|August|September|October|November|December) [0-9]+')


def output_article(title, targets):
    if not DATE_RE.match(title):
        normed = normalize_wp_link(title)
        desc = ', '.join([title] + targets)
        normed_pieces = normed.split(' ')
        if len(normed_pieces) < 4:
            if '###' not in normed:
                print(f'{normed}\t{desc}')


def run():
    targets = []
    current = None
    skipping = False
    seen_titles = set()
    for line in sys.stdin:
        line = line.rstrip()
        if '\t' in line:
            title, text = line.split('\t', 1)
            if current != title:
                if current is not None and current not in seen_titles:
                    output_article(current, targets)
                    output_article(current, targets[:10])
                    seen_titles.add(current)
                current = title
                targets.clear()
                skipping = False
            
            if 'United States Census' in text:
                skipping = True
            if not skipping:
                targets.append(text)
            if 'poverty line' in text:
                skipping = False

    if current is not None and current not in seen_titles:
        output_article(current, targets)
        output_article(current, targets[:10])


if __name__ == '__main__':
    run()

#!/usr/bin/env python3
import sys
from solvertools.normalize import normalize_wp_link


def output_article(title, targets):
    normed = normalize_wp_link(title)
    desc = ', '.join([title] + targets)
    normed_pieces = normed.split(' ')
    if len(normed_pieces) == 2:
        titles = normed_pieces + [normed]
    else:
        titles = [normed]
    if len(normed_pieces) < 4:
        for title in titles:
            if '###' not in title:
                print(f'{title}\t{desc}')


def run():
    targets = []
    current = None
    skipping = False
    for line in sys.stdin:
        line = line.rstrip()
        if '\t' in line:
            title, text = line.split('\t', 1)
            if current != title:
                if current is not None:
                    output_article(current, targets)
                current = title
                targets.clear()
                skipping = False
            
            if 'United States Census' in text:
                skipping = True
            if not skipping:
                targets.append(text)
            if 'poverty line' in text:
                skipping = False

    output_article(current, targets)


if __name__ == '__main__':
    run()

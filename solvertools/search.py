from solvertools.wordlist import WORDS
from solvertools.normalize import slugify, sanitize
from solvertools.util import data_path
from whoosh.index import open_dir
from whoosh import qparser
import re

INDEX = None
QUERY_PARSER = None


def search(pattern=None, clue=None, length=None, count=20):
    global INDEX, QUERY_PARSER
    if clue is None:
        return WORDS.search(pattern)

    if pattern is not None:
        pattern = pattern.lstrip('^').rstrip('$').lower()
        pattern = re.compile('^' + pattern + '$')

    if INDEX is None:
        INDEX = open_dir(data_path('search'))
        QUERY_PARSER = qparser.SimpleParser(
            "definition", schema=INDEX.schema,
            group=qparser.OrGroup.factory(0.9)
        )
        QUERY_PARSER.add_plugin(qparser.GroupPlugin())
        QUERY_PARSER.add_plugin(qparser.BoostPlugin())

    matches = []
    with INDEX.searcher() as searcher:
        results = searcher.search(QUERY_PARSER.parse(clue), limit=20)
        # half-assed query expansion
        clue_parts = [sanitize(result['text']) for result in results]
        expanded_clue = ", ".join(clue_parts)
        new_clue = '%s, (%s)^0.01' % (clue, expanded_clue)
        print(new_clue)
        results = searcher.search(QUERY_PARSER.parse(new_clue), limit=None)
        seen = set()
        for i, result in enumerate(results):
            text = result['text']
            slug = slugify(text)
            if slug not in seen:
                if length is None or length == len(slug):
                    if pattern is None or pattern.match(slug):
                        seen.add(slug)
                        #crom, text = WORDS.cromulence(slug)
                        score = results.score(i)
                        matches.append((score, text))
                        if len(matches) >= count:
                            break
        return matches

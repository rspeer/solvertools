from solvertools.normalize import slugify
from solvertools.util import data_path
from whoosh.index import open_dir
from whoosh import qparser
import re

INDEX = None
QUERY_PARSER = None


def search(query, pattern=None, length=None, num=20):
    global INDEX, QUERY_PARSER
    if pattern is not None:
        pattern = pattern.lstrip('^').rstrip('$').lower()
        pattern = re.compile('^' + pattern + '$')

    if INDEX is None:
        INDEX = open_dir(data_path('search'))
        QUERY_PARSER = qparser.SimpleParser(
            "definition", schema=INDEX.schema,
            group=qparser.OrGroup.factory(0.9)
        )

    matches = []
    with INDEX.searcher() as searcher:
        results = searcher.search(QUERY_PARSER.parse(query), limit=None)
        seen = set()
        for result in results:
            text = result['text']
            slug = slugify(text)
            if slug not in seen:
                if length is None or length == len(slug):
                    if pattern is None or pattern.match(slug):
                        seen.add(slug)
                        matches.append((text, result['definition']))
                        if len(matches) >= num:
                            break
        return matches

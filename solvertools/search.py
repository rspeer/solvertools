from solvertools.normalize import alpha_slug
from solvertools.util import data_path
from whoosh.index import open_dir
from whoosh import qparser

INDEX = None
QUERY_PARSER = None


def search(q):
    global INDEX, QUERY_PARSER
    if INDEX is None:
        INDEX = open_dir(data_path('search'))
        QUERY_PARSER = qparser.MultifieldParser(
            ["text", "definition"], schema=INDEX.schema,
            group=qparser.OrGroup.factory(0.9)
        )

    with INDEX.searcher() as searcher:
        results = searcher.search(QUERY_PARSER.parse(q))
        return [(result['text'], result['definition']) for result in results[:10]]
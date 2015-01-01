from solvertools.normalize import alpha_slug
from solvertools.util import data_path
from whoosh.fields import Schema, ID, TEXT, KEYWORD, NUMERIC
from whoosh.analysis import StemmingAnalyzer
from whoosh.index import create_in
from nltk.corpus import wordnet
import nltk
import os
get_synset = wordnet._synset_from_pos_and_offset


schema = Schema(
    slug=ID,
    text=TEXT(stored=True, analyzer=StemmingAnalyzer()),
    definition=TEXT(stored=True, analyzer=StemmingAnalyzer()),
    length=NUMERIC
)


def get_adjacent(synset):
    return [
        name
        for pointer_tuples in synset._pointers.values()
        for pos, offset in pointer_tuples
        for name in get_synset(pos, offset).lemma_names()
    ]


def init_search_index():
    nltk.download('wordnet')
    os.makedirs(data_path('search'), exist_ok=True)
    ix = create_in(data_path('search'), schema)
    writer = ix.writer(procs=4)

    synsets = wordnet.all_synsets()
    for syn in synsets:
        lemmas = [lem.replace('_', ' ') for lem in syn.lemma_names()]
        slugs = [alpha_slug(lemma) for lemma in lemmas]
        related = [lem.replace('_', ' ') for lem in get_adjacent(syn)]
        related2 = lemmas + related
        links = ', '.join(related2).upper()
        defn_parts = [syn.definition()]
        for example in syn.examples():
            defn_parts.append('"%s"' % example)
        defn_parts.append(links)
        defn = '; '.join(defn_parts)
        print(lemmas, defn)
        for name in lemmas:
            this_slug = alpha_slug(name)

            writer.add_document(
                slug=this_slug,
                text=name.upper(),
                definition=defn,
                length=len(this_slug)
            )

    print("Committing.")
    writer.commit(optimize=True)
    return ix


if __name__ == '__main__':
    init_search_index()
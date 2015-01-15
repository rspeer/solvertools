from solvertools.wordlist import WORDS
from solvertools.normalize import slugify
from solvertools.util import data_path, corpus_path
from whoosh.fields import Schema, ID, TEXT, KEYWORD, NUMERIC
from whoosh.analysis import StemmingAnalyzer
from whoosh.index import create_in
import nltk
import os


schema = Schema(
    slug=ID,
    text=TEXT(stored=True, analyzer=StemmingAnalyzer()),
    definition=TEXT(stored=True, analyzer=StemmingAnalyzer()),
    length=NUMERIC
)


def init_search_index():
    nltk.download('wordnet')
    from nltk.corpus import wordnet
    get_synset = wordnet._synset_from_pos_and_offset
    
    def get_adjacent(synset):
        return [
            name
            for pointer_tuples in synset._pointers.values()
            for pos, offset in pointer_tuples
            for name in get_synset(pos, offset).lemma_names()
        ]


    os.makedirs(data_path('search'), exist_ok=True)
    ix = create_in(data_path('search'), schema)
    writer = ix.writer(procs=4)

    # Add lookups from a phrase to a word in that phrase
    count = 0
    for slug, freq, text in WORDS.iter_all_by_freq():
        words = text.split()
        if freq < 10000:
            break
        if len(words) > 1:
            count += 1
            if count % 10000 == 0:
                print("%s,%s" % (text, freq))
            for word in words:
                if WORDS.logprob(word) < -7:
                    writer.add_document(
                        slug=slug,
                        text=word,
                        definition=text,
                        length=len(slug)
                    )

    # Add crossword clues
    for line in open(corpus_path('crossword_clues.txt'), encoding='utf-8'):
        text, defn = line.rstrip().split('\t')
        slug = slugify(text)
        print(text, defn)
        writer.add_document(
            slug=slug,
            text=text,
            definition=defn,
            length=len(slug)
        )

    # Add WordNet glosses and links
    synsets = wordnet.all_synsets()
    for syn in synsets:
        lemmas = [lem.replace('_', ' ') for lem in syn.lemma_names()]
        slugs = [slugify(lemma) for lemma in lemmas]
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
            this_slug = slugify(name)

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

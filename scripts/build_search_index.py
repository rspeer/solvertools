from solvertools.wordlist import WORDS
from solvertools.normalize import slugify, sanitize
from solvertools.util import data_path, corpus_path
from whoosh.fields import Schema, ID, TEXT, KEYWORD, NUMERIC
from whoosh.analysis import StandardAnalyzer
from whoosh.index import create_in
import nltk
import os
from tqdm import tqdm

schema = Schema(
    slug=ID,
    text=TEXT(stored=True, analyzer=StandardAnalyzer()),
    definition=TEXT(stored=True, analyzer=StandardAnalyzer()),
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

    # Add Wikipedia links
    for line in tqdm(open(data_path('corpora/wikipedia.txt')), desc='wikipedia'):
        title, summary = line.split('\t', 1)
        summary = summary.rstrip()
        if title and summary:
            slug = slugify(title)
            writer.add_document(
                slug=slug,
                text=title,
                definition=summary,
                length=len(slug)
            )

    # Add lookups from a phrase to a word in that phrase
    for slug, freq, text in tqdm(WORDS.iter_all_by_freq(), desc='phrases'):
        words = text.split()
        if freq < 10000:
            break
        if len(words) > 1:
            for word in words:
                if WORDS.logprob(word) < -7:
                    writer.add_document(
                        slug=slug,
                        text=word,
                        definition=text,
                        length=len(slug)
                    )

    # Add crossword clues
    for corpus in ('crossword_clues.txt', 'more_crossword_clues.txt'):
        for line in tqdm(open(corpus_path(corpus), encoding='utf-8'), desc=corpus):
            text, defn = line.rstrip().split('\t')
            slug = slugify(text)
            writer.add_document(
                slug=slug,
                text=text,
                definition=defn,
                length=len(slug)
            )

    # Add WordNet glosses and links
    synsets = wordnet.all_synsets()
    for syn in tqdm(synsets, desc='wordnet'):
        lemmas = [lem.replace('_', ' ') for lem in syn.lemma_names()]
        related = [lem.replace('_', ' ') for lem in get_adjacent(syn)]
        related2 = lemmas + related
        links = ', '.join(related2).upper()
        defn_parts = [syn.definition()]
        for example in syn.examples():
            defn_parts.append('"%s"' % example)
        defn_parts.append(links)
        defn = '; '.join(defn_parts)
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

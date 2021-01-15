from solvertools.util import db_path, data_path, wordlist_path, corpus_path
from solvertools.normalize import slugify, unspaced_lower
from solvertools.regextools import is_exact, regex_len, regex_slice
from solvertools.letters import (
    alphagram, anahash, consonantcy, alphabytes, random_letters
)
import sqlite3
import re
import os
import mmap
from collections import defaultdict, Counter
from pprint import pprint
from math import log, exp
from itertools import islice
import logging
logger = logging.getLogger(__name__)


# The NULL_HYPOTHESIS_ENTROPY is the log-probability per letter of something
# that is just barely an answer. We've tuned this, with the following criteria:
#
# - (recall) At least 98% of real Mystery Hunt answers should get positive cromulence
# - (precision) Randomly-generated answers with letter frequencies should get negative
#   cromulence as often as possible
#
# Currently the recall is 98.09%, and the precision averages about 96.5%.

NULL_HYPOTHESIS_ENTROPY = -3.5
DECIBEL_SCALE = 20 / log(10)


class Wordlist:
    schema = [
        """
        CREATE TABLE words (
            slug TEXT,
            freq INT,
            text TEXT
        )
        """,
        "CREATE UNIQUE INDEX words_slug ON words (slug)",
        "CREATE INDEX words_freq ON words (freq)"
    ]
    wordplay_schema = [
        "CREATE TABLE wordplay (slug TEXT, alphagram TEXT, anahash TEXT, consonantcy TEXT)",
        "CREATE UNIQUE INDEX wordplay_slug on words (slug)",
        "CREATE INDEX wordplay_alphagram on wordplay (alphagram)",
        "CREATE INDEX wordplay_anahash on wordplay (anahash)",
        "CREATE INDEX wordplay_consonantcy on wordplay (consonantcy)",
    ]
    max_indexed_length = 25

    def __init__(self, name):
        """
        Load a wordlist, given its name.
        """
        self.name = name
        self.db = wordlist_db_connection(name + '.wl.db')
        self._word_cache = {}
        self._grep_maps = {}
        self._alpha_maps = {}
        self.logtotal = None

    def __contains__(self, word):
        """
        `word in wordlist` is a quick, idiomatic way to tell if the given word
        (or phrase) appears in the wordlist.

        The word can be entered in natural form, possibly with capital letters
        and spaces. It will be converted to a lowercase, unspaced 'slug' here.
        """
        slug = slugify(word)
        return self.lookup_slug(slug) is not None

    def lookup_slug(self, slug):
        """
        Given an alphabetic 'slug', find its corresponding row of the
        database. If there is such a row, return its unscaled frequency and
        its text (including spaces). If not, return None.
        """
        if slug in self._word_cache:
            return self._word_cache[slug]
        c = self.db.cursor()
        c.execute("SELECT freq, text FROM words WHERE slug=?", (slug,))
        result = c.fetchone()
        self._word_cache[slug] = result
        return result

    def segment_logprob(self, slug):
        """
        If this slug appears directly in the word list, return its log
        probability and its text. Otherwise, return None.
        """
        if self.logtotal is None:
            totalfreq, _ = self.lookup_slug('')
            self.logtotal = log(totalfreq)
        found = self.lookup_slug(slug)
        if found is None:
            return None
        freq, text = found
        logprob = (log(freq) - self.logtotal)
        return logprob, text

    def freq(self, word):
        """
        Get the frequency of a single item in the wordlist.
        Always returns just a number, which is 0 if it's not found.
        """
        if self.logtotal is None:
            totalfreq, _ = self.lookup_slug('')
            self.logtotal = log(totalfreq)
        found = self.lookup_slug(slugify(word))
        if found is None:
            return 0.
        else:
            return log(found[0]) - self.logtotal

    def logprob(self, word):
        """
        Get the log probability of a single word, or -1000 if it's not found.
        """
        seg_result = self.segment_logprob(word)
        if seg_result is None:
            return -1000.
        else:
            return seg_result[0]

    def text_logprob(self, text):
        """
        Get the log probability of this text, along with its most likely
        spacing, gluing it together with multiple "segments" if necessary.
        """
        slug = slugify(text)
        n = len(slug)
        best_partial_results = ['']
        best_logprobs = [0.]
        for right_edge in range(1, n + 1):
            found = self.segment_logprob(slug[:right_edge])
            if found:
                rprob, rtext = found
                best_partial_results.append(rtext)
                best_logprobs.append(rprob)
            else:
                best_logprobs.append(-1000.)
                best_partial_results.append(slug[:right_edge])
            for left_edge in range(1, right_edge):
                lprob = best_logprobs[left_edge]
                found2 = self.segment_logprob(slug[left_edge:right_edge])
                if found2:
                    rprob, rtext = found2
                    totalprob = lprob + rprob - log(10)
                    if totalprob > best_logprobs[right_edge]:
                        best_logprobs[right_edge] = totalprob
                        ltext = best_partial_results[left_edge]
                        best_partial_results[right_edge] = ltext + ' ' + rtext
        return best_logprobs[-1], best_partial_results[-1]

    def cromulence(self, text):
        """
        Estimate how likely this text is to be an answer. The "cromulence"
        scale is defined at the top of this module.
        """
        slug = slugify(text)
        if len(slug) == 0:
            return (0, '')
        logprob, found_text = self.text_logprob(slug)
        entropy = logprob / (len(slug) + 1)
        cromulence = round((entropy - NULL_HYPOTHESIS_ENTROPY) * DECIBEL_SCALE, 1)
        return cromulence, found_text

    def logprob_to_cromulence(self, logprob, length):
        """
        Convert a log probability to the 'cromulence' scale, which only
        requires knowing the length of the text.
        """
        entropy = logprob / (length + 1)
        cromulence = round((entropy - NULL_HYPOTHESIS_ENTROPY) * DECIBEL_SCALE, 1)
        return cromulence

    def grep(self, pattern, length=None, count=1000):
        """
        Search the wordlist quickly for words matching a given pattern.
        Yield them as they are found (not in sorted order).

        Yields (logprob, text) for each match.
        """
        pattern = unspaced_lower(pattern)
        if is_exact(pattern):
            if pattern in self:
                yield self.segment_logprob(pattern)
            return
        if length:
            minlen = maxlen = length
        else:
            minlen, maxlen = regex_len(pattern)
        if minlen < 1:
            minlen = 1
        if maxlen > self.max_indexed_length:
            maxlen = self.max_indexed_length

        num_found = 0
        for cur_length in range(minlen, maxlen + 1):
            if cur_length not in self._grep_maps:
                mm = self._open_mmap(
                    wordlist_path_from_name(
                        'greppable/%s.%d' % (self.name, cur_length)
                    )
                )
                self._grep_maps[cur_length] = mm
            else:
                mm = self._grep_maps[cur_length]
            pbytes = pattern.encode('ascii').replace(b'[^',b'[^,')
            pattern1 = b'^' + pbytes + b','
            pattern2 = b'\n' + pbytes + b','
            match = re.match(pattern1, mm)
            if match:
                found = mm[match.start():match.end() - 1].decode('ascii')
                num_found += 1
                yield self.segment_logprob(found)
            for match in re.finditer(pattern2, mm):
                found = mm[match.start() + 1:match.end() - 1].decode('ascii')

                num_found += 1
                yield self.segment_logprob(found)
                if num_found >= count:
                    return

    def grep_one(self, pattern, length=None):
        """
        Like .grep(), but returns only one result, or None if there are no
        results.
        """
        for result in self.grep(pattern, length):
            return result

    def search(self, pattern, length=None, count=10, use_cromulence=False):
        """
        Find results matching a given pattern, returning the cromulence
        and the text of each.

        If the length is known, it can be specified as an additional argument.
        """
        pattern = unspaced_lower(pattern)
        if is_exact(pattern):
            if use_cromulence:
                return [self.cromulence(pattern)]
            else:
                return [self.text_logprob(pattern)]

        minlen, maxlen = regex_len(pattern)
        if minlen != maxlen:
            # If there are variable-length matches, the dynamic programming
            # strategy won't work, so fall back on grepping for complete
            # matches in the wordlist.
            items = list(self.grep(pattern, length=length))
            items.sort(reverse=True)
            found = items[:count]
        else:
            if length is not None and not (minlen <= length <= maxlen):
                # This length is impossible, so there are no results.
                return []

            best_partial_results = [[]]
            for right_edge in range(1, maxlen + 1):
                segment = regex_slice(pattern, 0, right_edge)
                results_this_step = list(islice(self.grep(segment), count))

                for left_edge in range(1, right_edge):
                    if best_partial_results[left_edge]:
                        segment = regex_slice(pattern, left_edge, right_edge)
                        found = list(islice(self.grep(segment), count))
                        for lprob, ltext in best_partial_results[left_edge]:
                            for rprob, rtext in found:
                                results_this_step.append((
                                    lprob + rprob - log(10),
                                    ltext + ' ' + rtext
                                ))
                results_this_step.sort(reverse=True)
                best_partial_results.append(results_this_step[:count])
            found = best_partial_results[-1]

        if not use_cromulence:
            return found
        else:
            results = []
            for (logprob, text) in found:
                cromulence = self.logprob_to_cromulence(logprob, len(slugify(text)))
                results.append((cromulence, text))
            results.sort(reverse=True)
            return results


    def _iter_query(self, query, params=()):
        c = self.db.cursor()
        c.execute(query, params)
        while True:
            got = c.fetchmany()
            if not got:
                return
            for row in got:
                yield row

    def _iter_singletons(self, query, params=()):
        c = self.db.cursor()
        c.execute(query, params)
        while True:
            got = c.fetchmany()
            if not got:
                return
            for row in got:
                yield row[0]

    def iter_all_by_freq(self):
        """
        Read the database and iterate through it in descending order
        by frequency.
        """
        return self._iter_query(
            "SELECT slug, freq, text FROM words ORDER BY freq DESC"
        )

    def iter_all_by_cromulence(self):
        """
        Read the database and iterate through it in descending order
        by cromulence.
        """
        return self._iter_query(
            "SELECT slug, freq, text FROM words ORDER BY freq/(length(slug) + 1) DESC"
        )

    def find_sub_alphagrams(self, alpha, wildcard=False):
        if len(alpha) + wildcard < 2:
            return
        abytes = alphabytes(alpha)
        max_length = min(len(alpha) + wildcard - 2, self.max_indexed_length)
        if max_length < 2:
            max_length = 2
        if max_length not in self._alpha_maps:
            mm = self._open_mmap(
                wordlist_path_from_name(
                    'alphabytes/%s.%d' % (self.name, max_length)
                )
            )
            self._alpha_maps[max_length] = mm
        else:
            mm = self._alpha_maps[max_length]
        if wildcard:
            pattern = b'\n[' + abytes + b']*.[' + abytes + b']*\n'
        else:
            pattern = b'\n[' + abytes + b']+\n'
        for match in re.finditer(pattern, mm):
            found = mm[match.start() + 1:match.end() - 1]
            yield found

    def find_by_alphagram(self, alphagram):
        return self._iter_query(
            "SELECT w.* from wordplay wp, words w "
            "WHERE wp.slug=w.slug and wp.alphagram=? "
            "ORDER BY freq DESC",
            (alphagram,)
        )

    def find_by_alphagram_raw(self, alphagram):
        return self._iter_singletons(
            "SELECT w.slug from wordplay wp, words w "
            "WHERE wp.slug=w.slug and wp.alphagram=? "
            "ORDER BY freq DESC",
            (alphagram,)
        )

    def find_by_anahash_raw(self, anahash):
        return self._iter_singletons(
            "SELECT w.slug from wordplay wp, words w "
            "WHERE wp.slug=w.slug and wp.anahash=? "
            "ORDER BY freq DESC",
            (anahash,)
        )

    def find_by_consonantcy(self, consonants):
        return self._iter_query(
            "SELECT w.* from wordplay wp, words w "
            "WHERE wp.slug=w.slug and wp.consonantcy=? "
            "ORDER BY freq DESC",
            (consonants,)
        )

    def __getitem__(self, pattern):
        return self.grep_one(pattern)

    def __repr__(self):
        return "Wordlist(%r)" % self.name

    def _open_mmap(self, path):
        openfile = open(path, 'r+b')
        mm = mmap.mmap(openfile.fileno(), 0, access=mmap.ACCESS_READ)
        return mm

    # Below this are building steps that should only need to be run once.
    def build_db(self):
        """
        Build a SQLite database from a flat wordlist file.
        """
        self.db.execute("DROP TABLE IF EXISTS words")
        for statement in self.schema:
            self.db.execute(statement)

        total = 0
        with self.db:
            for i, slug, freq, text in read_wordlist(self.name):
                self.db.execute(
                    "INSERT INTO words (slug, freq, text) "
                    "VALUES (?, ?, ?)",
                    (slug, freq, text)
                )
                total += freq
                if i % 100000 == 0:
                    print("\t%s,%s" % (text, freq))

            # Use the empty string to record the total
            print("Total: %d" % total)
            self.db.execute(
                "INSERT INTO words (slug, freq, text) VALUES ('', ?, '')",
                (total,)
            )

    def build_wordplay(self):
        self.db.execute("DROP TABLE IF EXISTS wordplay")
        for statement in self.wordplay_schema:
            self.db.execute(statement)

        with self.db:
            for i, slug, freq, text in read_wordlist(self.name):
                alpha = alphagram(slug)
                ana = anahash(slug)
                cons = consonantcy(slug)
                self.db.execute(
                    "INSERT INTO wordplay (slug, alphagram, anahash, consonantcy) "
                    "VALUES (?, ?, ?, ?)",
                    (slug, alpha, ana, cons)
                )
                if i % 100000 == 0:
                    print("\t%s" % (text))

    def write_greppable_lists(self):
        """
        Separate the words by length and write them into separate files.
        """
        os.makedirs(wordlist_path('greppable'), exist_ok=True)
        length_files = {
            length: open(
                wordlist_path_from_name(
                    'greppable/%s.%d' % (self.name, length)
                ), 'w', encoding='ascii'
            )
            for length in range(1, self.max_indexed_length + 1)
        }
        i = 0
        for slug, freq, text in self.iter_all_by_cromulence():
            length = len(slug)
            if 1 <= length <= self.max_indexed_length:
                out = length_files[length]
                print("%s,%d" % (slug, freq), file=out)
            if i % 100000 == 0:
                print("\t%s,%d" % (slug, freq))
            i += 1
        for file in length_files.values():
            file.close()

    def write_alphabytes(self):
        os.makedirs(wordlist_path('alphabytes'), exist_ok=True)
        length_files = {
            length: open(
                wordlist_path_from_name(
                    'alphabytes/%s.%d' % (self.name, length)
                ), 'wb'
            )
            for length in range(2, self.max_indexed_length + 1)
        }
        i = 0
        used = set()
        for slug, freq, text in self.iter_all_by_freq():
            if len(slug) >= 2:
                maxlen = self.max_indexed_length
                abytes = alphabytes(slug)
                if abytes not in used:
                    for length in range(len(slug), maxlen + 1):
                        out = length_files[length]
                        out.write(b'\n')
                        out.write(abytes)
                        used.add(abytes)
        for file in length_files.values():
            file.write(b'\n')
            file.close()

    def test_cromulence(self):
        """
        This test runs a corpus of past Mystery Hunt answers through the cromulence
        function, so we can tune it to return positive numbers for real answers.

        It does this by generating fake answers with the lengths of real answers, but
        with the letters drawn randomly from a unigram distribution.

        Sometimes this comes up with neat fake answers such as:

            7.4  ON FRODO
            6.8  ENIAC
            6.6  AS I CAN
            6.4  IBM STOP
            5.4  AIR LOL
            3.8  USE MIT
            3.7  VON POOPIN
            2.1  NA BEER
            0.2  DNA ARRRGH AH
        """
        real_answers = []
        years = ['1994', '1997'] + [str(year) for year in range(1999, 2021)]
        for year in years:
            with open(corpus_path('mh_answers/mystery%s.txt' % year)) as file:
                for line in file:
                    line = line.strip()
                    if line:
                        answer, _typ = line.rsplit(',', 1)
                        if slugify(answer):
                            real_answers.append(answer)
        fake_answers = [
            random_letters(len(real)) for real in real_answers
        ]
        results = []
        for ans in real_answers:
            cromulence, spaced = self.cromulence(ans)
            logprob, _ = self.text_logprob(ans)
            if cromulence > 0:
                results.append((cromulence, logprob, spaced, 'true positive'))
            else:
                results.append((cromulence, logprob, spaced, 'false negative'))
        for ans in fake_answers:
            cromulence, spaced = self.cromulence(ans)
            logprob, _ = self.text_logprob(ans)
            if cromulence > 0:
                results.append((cromulence, logprob, spaced, 'false positive'))
            else:
                results.append((cromulence, logprob, spaced, 'true negative'))

        results.sort(reverse=True)
        counts = Counter([item[-1] for item in results])
        precision = counts['true positive'] / (counts['true positive'] + counts['false positive'])
        recall = counts['true positive'] / (counts['true positive'] + counts['false negative'])
        f_score = 2/(1/precision + 1/recall)
        for cromulence, logprob, spaced, category in results:
            print("%1.1f\t%2.2f\t%s\t%s" % (cromulence, logprob, category, spaced))
        print("Precision: %2.2f%%" % (precision * 100))
        print("Recall: %2.2f%%" % (recall * 100))
        return f_score

    def show_best_results(self, results, count=20):
        results.sort(reverse=True)
        print("Cromulence\tText\tInfo")
        for logprob, text, info in results[:count]:
            cromulence, spaced = self.cromulence(text)
            if info is None:
                info = ''
            print("%1.1f\t%s\t%s" % (cromulence, spaced, info))
        return results[:count]


def wordlist_path_from_name(name):
    """
    Get the path to the plain-text form of a wordlist.
    """
    return wordlist_path(name + '.txt')


def wordlist_db_connection(filename):
    """
    Get a SQLite DB connection for a wordlist. (The DB must previously
    have been built.)
    """
    os.makedirs(db_path(''), exist_ok=True)
    return sqlite3.connect(db_path(filename), check_same_thread=False)


def read_wordlist(name):
    """
    Read a wordlist from a comma-separated plain-text file, and iterate
    its entries in order.
    """
    filepath = wordlist_path_from_name(name)
    with open(filepath, encoding='utf-8') as wordfile:
        for i, line in enumerate(wordfile):
            if ',' not in line:
                continue
            line = line.rstrip()
            text, freq = line.split(',', 1)
            freq = int(freq)
            slug = slugify(text)
            if slug:
                yield (i, slug, freq, text)


def combine_wordlists(weighted_lists, out_name):
    """
    This function is used in building the combined wordlist called WORDS.
    It reads several wordlists from their plain-text form, and adds together
    the frequencies of the words they contain, applying a multiplicative
    weight to each.
    """
    freqs = defaultdict(float)
    texts = {}
    print("Combining %s" % weighted_lists)
    for name, weight in weighted_lists:
        for i, slug, freq, text in read_wordlist(name):
            # Turns out that things that just barely make our cutoff from
            # Google Books are worse than you'd think
            if name == 'google-books-1grams':
                freq -= 1000
                if freq <= 0:
                    continue

            # Replace an existing text if this spelling of it has a solid
            # majority of the frequency so far. Avoids weirdness such as
            # spelling "THE" as "T'HE".
            if slug not in texts or (freq * weight) > freqs[slug]:
                texts[slug] = text
            freqs[slug] += freq * weight
            if i % 100000 == 0:
                print("\t%s,%s" % (text, freq * weight))

    alphabetized = sorted(list(texts))
    out_filename = wordlist_path_from_name(out_name)
    with open(out_filename, 'w', encoding='utf-8') as out:
        print("Writing %r" % out)
        for i, slug in enumerate(alphabetized):
            freq = int(freqs[slug])
            if freq > 0:
                line = "%s,%s" % (texts[slug], freq)
                print(line, file=out)
            if i % 100000 == 0:
                print("\t%s,%s" % (texts[slug], freq))


def build_extras(name):
    """
    Load a wordlist with a particular name, and create additional files that
    enable more operations on the wordlist -- a file that can be mmapped and
    grepped quickly, a file of 'alphabytes' that can be mmapped and grepped to
    find anagrams, and a database of 'wordplay' properties of words.
    """
    dbw = Wordlist(name)
    dbw.build_db()
    dbw.write_greppable_lists()
    dbw.write_alphabytes()
    dbw.build_wordplay()


WORDS = Wordlist('combined')
SCRAB = Wordlist('scrab')


def cromulence(text):
    return WORDS.cromulence(text)


def find_by_alphagram(text):
    return WORDS.find_by_alphagram(alphagram(slugify(text)))


def find_by_consonantcy(text):
    return WORDS.find_by_consonantcy(consonantcy(slugify(text)))


if __name__ == '__main__':
    WORDS.test_cromulence()

from flask import Flask, render_template, request, redirect, Response
from solvertools.search import search
from solvertools.anagram import anagrams
import re
application = app = Flask(__name__)


@app.route('/')
def main_page():
    return render_template('main.html', section='main')


@app.route('/search')
@app.route('/search/')
def search_page():
    clue = request.args.get('clue') or None
    pattern = request.args.get('pattern') or None
    length = request.args.get('length') or None
    if length:
        try:
            length = int(length)
        except IndexError:
            length = None

    try:
        search_results = [
            (score, answer) for (answer, score) in
            search(pattern=pattern, clue=clue, length=length, count=100)
        ]
        return render_template(
            'main.html', section='clue', results=search_results,
            pattern=pattern, clue=clue, length=length
        )
    except Exception as e:
        return render_template(
            'main.html', section='clue', error=str(e),
            pattern=pattern, clue=clue, length=length
        )


def _render_search_results(caption, search_results):
    results = '\n'.join('% 4.1f  %s' % (item[0], item[1]) for item in search_results)
    return 'Results for: {}\n{}'.format(caption, results)


@app.route('/api/pattern')
@app.route('/api/pattern/')
def pattern_api():
    text = request.args.get('text')
    if not text:
        response = "Type /pattern followed by the regex to search for, such as '/pattern .a.b.c..'"
    else:
        search_results = search(pattern=text.strip('/'), count=16)
        response = _render_search_results(text.strip('/'), search_results)
    return Response(response, mimetype='text/plain')


PATTERN_RE = re.compile(r'/([^/]+)/$')
ENUMERATION_RE = re.compile(r'\(([0-9]+)\)$')


@app.route('/api/clue')
@app.route('/api/clue/')
def clue_api():
    text = request.args.get('text').strip()
    if not text:
        response = "Type /clue followed by the clue text to look up, such as '/clue Lincoln assassin (15)' or '/clue meat /.a.b..../'"
    else:
        pattern = None
        length = None
        clue = text
        match = PATTERN_RE.search(text)
        if match:
            clue = text[:match.start()].strip()
            pattern = match.group(1)
        
        match = ENUMERATION_RE.search(text)
        if match:
            clue = text[:match.start()].strip()
            length = int(match.group(1))

        search_results = search(clue=clue, pattern=pattern, length=length)
        response = _render_search_results(text, search_results)
    return Response(response, mimetype='text/plain')


@app.route('/api/anagram')
@app.route('/api/anagram/')
def anagram_api():
    text = request.args.get('text').strip()
    if not text:
        response = "Type /anagram followed by letters to anagram. You can add or subtract letters: '/anagram warehouse+2' or '/anagram warehouse-1'"
    else:
        wildcards = 0
        if '+' in text:
            letters, wildcard_str = text.split('+', 1)
            wildcards = int(wildcard_str)
        elif '-' in text:
            letters, wildcard_str = text.split('-', 1)
            wildcards = -(int(wildcard_str))
        elif '.' in text:
            letters = ''.join(let for let in text if let != '.')
            wildcards = text.count('.')
        else:
            letters = text
        found_anagrams = anagrams(letters, wildcards, count=15, quiet=True, time_limit=1.5)
        response = _render_search_results(text, found_anagrams)
    return Response(response, mimetype='text/plain')


@app.route('/anagram')
@app.route('/anagram/')
def anagram_page():
    letters = request.args.get('letters') or ''
    wildcards = request.args.get('wildcards') or 0
    if wildcards:
        try:
            wildcards = int(wildcards)
        except IndexError:
            wildcards = 0

    if not letters:
        return render_template(
            'main.html', section='anagram', results=[],
            letters=letters, wildcards=wildcards
        )

    try:
        found_anagrams = anagrams(letters, wildcards, count=100, quiet=True, time_limit=2.0)
        return render_template(
            'main.html', section='anagram', results=found_anagrams,
            letters=letters, wildcards=wildcards
        )
    except Exception as e:
        return render_template(
            'main.html', section='clue', error=str(e),
            letters=letters, wildcards=wildcards
        )


@app.route('/static/anagrampage')
@app.route('/static/anagrampage/')
def anagram_interactive_page():
    return redirect('/static/anagrampage/index.html')

if __name__ == '__main__':
    app.run('0.0.0.0')

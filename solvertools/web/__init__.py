from flask import Flask, render_template, request, redirect
from solvertools.search import search
from solvertools.anagram import anagrams
app = Flask(__name__)


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
        search_results = search(pattern=pattern, clue=clue, length=length, count=100)
        return render_template(
            'main.html', section='clue', results=search_results,
            pattern=pattern, clue=clue, length=length
        )
    except Exception as e:
        return render_template(
            'main.html', section='clue', error=str(e),
            pattern=pattern, clue=clue, length=length
        )


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
    app.run(debug=True)

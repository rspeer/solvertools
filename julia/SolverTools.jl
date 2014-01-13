# ## Getting stuff set up
using PyCall
using DataFrames
using Base
importall Base

# If we decide to make this a module, uncomment these:
#
#    export is_ascii_letter, letter_index, letter_unindex
#    export unicode_category, unicode_name, unicode_normalize
#    export roman_letters, roman_letters_and_spaces
#    export caesar_shift, vigenere, vigenere_1based
#    export load_wordframe, load_wordlist, grep, logprob
#    export trim_bigrams
#    export interpret_text, interpret_pattern
#    export letter_bigrams, letter_table, bigram_table

BASE_PATH = "."
if haskey(ENV, "SOLVERTOOLS_BASE")
    BASE_PATH = ENV["SOLVERTOOLS_BASE"]
end

MIN_LOGPROB = -1000.

# ## Letter operations
# Some functions for working with the 26 capital English letters. If your letters
# might be lowercase, be sure to use Julia's `uppercase` function on them first.
function is_ascii_letter(ch::Char)
    ('A' <= ch <= 'Z') || ('a' <= ch <= 'z')
end

# `letter_index`: convert a capital letter to a number from 1 to 26.
function letter_index(ch::Char)
    ch - '@'
end

# `letter_unindex`: convert a number from 1 to 26 to a capital letter.
# To make modular arithmetic more convenient, 0 will also convert to 'Z'.
function letter_unindex(i::Int)
    if i == 0
        'Z'
    else
        '@' + i
    end
end

# ## Unicode operations
# These operations have significant overhead, because they have to make an
# external call to Python 3. Julia itself doesn't have a library that gives
# access to metadata about Unicode characters.
#
# As far as I can tell, PyCall does not support Unicode strings in Python 2, so
# you must be running Julia in a Python 3 environment for these functions to
# work.
@pyimport unicodedata
function unicode_category(ch::Char)
    unicodedata.category(string(ch))
end

function unicode_name(ch::Char)
    unicodedata.name(string(ch), "<unknown>")
end

function unicode_normalize(s::String)
    unicodedata.normalize("NFKC", s)
end

function unicode_decompose(s::String)
    unicodedata.normalize("NFKD", s)
end

# `roman_letters`: Remove accents, convert to uppercase, and keep only
# the letters A-Z.
function roman_letters(s::UTF8String)
    if is_valid_ascii(s)
        decomposed = s
    else
        decomposed = unicodedata.normalize("NFKD", uppercase(s))
    end
    replace(decomposed, r"[^A-Z]", "")
end

function roman_letters_and_spaces(s::UTF8String)
    if is_valid_ascii(s)
        decomposed = s
    else
        decomposed = unicodedata.normalize("NFKD", uppercase(s))
    end
    replace(decomposed, r"[^A-Z ]", "")
end

function remove_spaces(s::UTF8String)
    replace(s, " ", "")
end

# ## Ciphers

# ### The Caesar cipher
# `caesar_shift`: shift a string or character around the alphabet by a
# constant number of letters.
#
# If the shift amount is given as a character, 'A' corresponds to the
# identity, 'B' corresponds to a shift of 1, and so on.
function caesar_shift(letters::String, shift::Int)
    join(map(letter -> caesar_shift(letter, shift), letters))
end

function caesar_shift(letter::Char, shift::Int)
    upl = uppercase(letter)
    if is_ascii_letter(upl)
        idx = letter_index(upl)
        letter_unindex(mod1(idx + shift, 26))
    else
        letter
    end
end

caesar_shift(letters::String, shift::Char) = caesar_shift(letters, letter_index(uppercase(shift)) - 1)
caesar_shift(letter::Char, shift::Char) = caesar_shift(letter, letter_index(uppercase(shift)) - 1)

# ### The Vigenère cipher
# `vigenere`: shift a string around the alphabet according to a cycle of
# offsets.
#
# If the offsets are given as a string (as they often are), each character
# specifies what 'A' maps to in that position. The key 'A' is therefore the
# identity.
function vigenere(letters::String, key::String)
    key = roman_letters(key)
    keylen = length(key)
    keypos = 1
    shifted = Char[]
    for char in letters
        if is_ascii_letter(char)
            shift = key[keypos]
            push!(shifted, caesar_shift(char, shift))
            keypos = mod1(keypos + 1, keylen)
        else
            push!(shifted, char)
        end
    end
    join(shifted)
end

# `vigenere_1based`: an ahistorical version of the Vigenere cipher, popular
# in the Mystery Hunt.
#
# In Vigenere's system, A + A = A. In the Mystery Hunt, often, A + A = B.
# This version of the Vigenere cipher is equivalent to adding the
# one-based letter indexes modulo 26.
function vigenere_1based(letters::String, key::String)
    caesar_shift(vigenere(letters, key), 1)
end

# ## Wordlists
type Wordlist
    wordmap::(String => Float64)
    quickstrings::(Int => (Char => String))
    sortstring::String

    function Wordlist()
        new((String => Float64)[], (Int => (Char => String))[], "")
    end
end

function load_wordframe(filename::String, filepath::String=BASE_PATH, T::Type=Int64)
    path = joinpath(filepath, filename)
    wordframe::DataFrame = readtable(
        path, separator='\t', header=false,
        nastrings=ASCIIString[], colnames=["word", "freq"],
        coltypes={UTF8String, T}
    )
    wordframe
end

function load_wordlist(filename::String, filepath::String=BASE_PATH)
    wordframe = load_wordframe(filename, filepath, Int64)
    build_wordlist(wordframe)
end

function build_wordlist(wordframe::DataFrame)
    wordlist::Wordlist = Wordlist()
    sublists = (Int => (Char => Array{String}))[]
    total = sum(wordframe[2])
    for row=1:nrow(wordframe)
        word = remove_spaces(wordframe[row, 1])
        if haskey(wordlist.wordmap, word)
            continue
        end
        freq = wordframe[row, 2]
        wordlist.wordmap[word] = log2(freq) - log2(total)

        wordlength = length(word)
        if wordlength > 30
            continue
        end
        if !haskey(sublists, wordlength)
            sublists[wordlength] = (Char => Array{String})[]
        end
        lengthlists = sublists[wordlength]

        startchar = word[1]
        if !haskey(lengthlists, startchar)
            lengthlists[startchar] = String[]
        end
        push!(lengthlists[startchar], word)
        if row % 100000 == 0
            println("Read $row words")
        end
    end
    for len=sort(collect(keys(sublists)))
        println("Handling words of length $len")
        wordlist.quickstrings[len] = (Char => String)[]
        for startchar=keys(sublists[len])
            sublist = sublists[len][startchar]
            wordlist.quickstrings[len][startchar] = join(sublist, '\n')
        end
    end
    println("Storing greppable string")
    sorted = [remove_spaces(x) for x=wordframe[1]]
    wordlist.sortstring = join(sorted, '\n')
    wordlist
end

length(w::Wordlist) = length(w.wordmap)
keys(w::Wordlist) = keys(w.wordmap)
start(w::Wordlist) = start(w.wordmap)
next(w::Wordlist, i) = next(w.wordmap, i)
done(w::Wordlist, i) = done(w.wordmap, i)

function print(io::IO, w::Wordlist)
    len = length(w.wordmap)
    (sample, state) = next(w, start(w))
    print(io, "Wordmap with $len entries like $sample")
end
show(io::IO, w::Wordlist) = print(io, w)

function getindex(wordlist::Wordlist, word)
    if haskey(wordlist.wordmap, word)
        wordlist.wordmap[word]
    else
        MIN_LOGPROB
    end
end

# ### Optimized grep
function grep(wordlist::Wordlist, pattern::String, func)
    regex = Regex("^" * pattern * "\$", "im")
    for thematch=eachmatch(regex, wordlist.sortstring)
        func(thematch.match)
    end
end

function grep(wordlist::Wordlist, pattern::String)
    results = UTF8String[]
    grep(regex, wordlist, x -> push!(results, x))
    results
end

# ### Frequency statistics
function logprob(wordlist::Wordlist, word::String)
    wordlist[word]
end

function haskey(wordlist::Wordlist, word::String)
    haskey(wordlist.wordmap, word)
end

function interpret_text(wordlist::Wordlist, text::String)
    best_partial_results = UTF8String[]
    best_partial_logprob = Float64[]
    indexes = [chr2ind(text, chr) for chr=1:length(text)]

    # I keep track of indexes and character offsets separately, so that
    # this code could keep working given non-ASCII input. For example,
    # I may want to do things with IPA.
    for (rind, right_edge)=enumerate(indexes)
        push!(best_partial_results, text[1:right_edge])
        push!(best_partial_logprob, logprob(wordlist, text[1:right_edge]))
        for (lind, left_edge)=enumerate(indexes)
            if left_edge >= right_edge
                break
            end
            right_string = text[(left_edge+1):right_edge]
            left_logprob = best_partial_logprob[lind]
            right_logprob = logprob(wordlist, right_string)
            if left_logprob + right_logprob > best_partial_logprob[rind]
                best_partial_logprob[rind] = left_logprob + right_logprob
                best_partial_results[rind] = best_partial_results[lind] * " " * right_string
            end
        end
    end
    return best_partial_results[end], best_partial_logprob[end]
end

function wordness(wordlist::Wordlist, text::String)
    if length(text) == 0
        return 0.
    else
        logprob = interpret_text(wordlist, text)[2]
        return logprob / length(text)
    end
end

# ## Filtering word bigrams
# Take in a table of word bigrams, and use a unigram wordlist to keep
# only the interesting ones.

function trim_bigrams(unigram_filename::String, bigram_filename::String, ratio::Real)
    bigram_frame = load_wordframe(bigram_filename)
    unigram_list = load_wordlist(unigram_filename)
    total_bigrams = sum(bigram_frame[2])
    logratio = log2(ratio)
    logtotal = log2(total_bigrams)

    for row=1:nrow(bigram_frame)
        bigram = bigram_frame[row, 1]
        freq = bigram_frame[row, 2]
        (word1, word2) = split(bigram, " ")
        if haskey(unigram_list, word1) && haskey(unigram_list, word2)
            bigram_logprob = log2(freq) - logtotal
            unigram_logprob = logprob(unigram_list, word1) + logprob(unigram_list, word2)
            score = bigram_logprob - unigram_logprob
            if score > logratio
                println("$bigram\t$freq\t$score")
            end
        end
    end
end

# ## Regex operations
# We'll need some help from Python for this.

@pyimport regextools
function interpret_pattern(wordlist::Wordlist, pattern::String, func, max::Int=100)
    if regextools.is_deterministic(pattern)
        return interpret_text(wordlist, pattern)
    end

    min, max = regextools.regex_len(pattern)
    if min != max
        return grep(wordlist, pattern)
    end

    # Subtract 1 from all indices, because Python is 0-based
    pieces = UTF8String[regextools.regex_index(pattern, i-1) for i=1:max]
    deterministic = Bool[regextools.is_deterministic(piece) for piece=pieces]

    pqueue = PriorityQueue{(Int64, String, Float64), Float64}()
    best_at_position = (Int64 => Float64)[]
    pqueue[(0, "", 0.)] = 0.

    for len=1:max
        if haskey(wordlist.quickstrings, len)
            start_letter = regextools.regex_index(pattern, 0)
            if is_deterministic(start_letter)
                greplist = wordlist.quickstrings[len][start_letter]
            else
                greplist = wordlist.sortstring
            end
        end
    end

    results = 0
    while results < max
        pos, string_so_far, score = pop!(pqueue)
        # not done yet
    end
end



# ## Letter distribution statistics

function letter_bigrams(s::UTF8String)
    result = UTF8String[]
    i = 1
    lasti = endof(s)
    while i < lasti
        nexti = nextind(s, i)
        push!(result, s[i:nexti])
        i = nexti
    end
    result
end

function letter_bigrams(s::ASCIIString)
    [s[i:i+1] for i=1:length(s) - 1]
end

function letter_table(wordlist::Wordlist)
    utable = zeros(Int64, 26)
    for (word, freq)=wordlist
        if is_valid_ascii(word)
            aword = ascii(word)
            for letter in aword
                utable[letter_index(letter)] += freq
            end
        end
    end
    utable
end

function bigram_table(wordlist::Wordlist)
    btable = zeros(Int64, (27, 27))
    boundary = 27
    for (word, freq)=wordlist
        if is_valid_ascii(word)
            aword = ascii(word)
            btable[boundary, letter_index(aword[1])] += freq
            for b=letter_bigrams(aword)
                i1 = letter_index(b[1])
                i2 = letter_index(b[2])
                btable[i1, i2] += freq
            end
            btable[letter_index(aword[end]), boundary] += freq
        end
    end
    btable
end

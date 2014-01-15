# ## Getting stuff set up
using PyCall

# `importall Base` means that, when we define methods such as `print()` and
# `haskey()`, we're automatically extending the built-in functions. Otherwise
# we'd have to be explicit about the fact that we're extending them, not
# replacing them. This is much more convenient.
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

# I split Wordlist into a separate file because it defines a new type, and types are really hard to reload interactively.
#require(joinpath(BASE_PATH, "julia", "wordlists.jl"))
require("wordlists.jl")
using Wordlists

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


# ### Optimized grep

# We'll need some help from Python for regex manipulation.
@pyimport regextools

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

function grep_fixed(wordlist::Wordlist, pattern::String, len::Int, func)
    # We're calling Python, so it's 0-indexed
    regex_first = uppercase(regextools.regex_index(pattern, 0))
    if !regextools.is_deterministic(regex_first)
        grep(wordlist, pattern, func)
    else
        regex = Regex("^" * pattern * "\$", "im")
        if !haskey(wordlist.quickstrings, len)
            return
        end
        lengthdict = wordlist.quickstrings[len]
        if !haskey(lengthdict, regex_first)
            return
        end
        quickstring = lengthdict[regex_first]
        for thematch=eachmatch(regex, quickstring)
            func(thematch.match)
        end
    end
end

function grep_fixed(wordlist::Wordlist, pattern::String, len::Int)
    results = UTF8String[]
    grep_fixed(wordlist, pattern, len, x -> push!(results, x))
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
function interpret_pattern(wordlist::Wordlist, pattern::String, 
                           limit::Int=100, beam::Int=5)
    if regextools.is_deterministic(pattern)
        return interpret_text(wordlist, pattern)
    end

    # If this isn't a fixed-length regex, fall back on ordinary "grep",
    # without assembling phrases.
    minlen, maxlen = regextools.regex_len(pattern)
    if minlen != maxlen
        return grep(wordlist, pattern)
    end
    regex_len::Int = maxlen

    # Subtract 1 from all indices, because Python is 0-based
    pieces = UTF8String[regextools.regex_index(pattern, i-1) for i=1:regex_len]

    # Don't be confused by the type syntax. These aren't arrays of strings,
    # they're (ragged) arrays of arrays of strings. Maybe Julia will add syntax
    # for this with two sets of brackets someday.
    left_partials = Array{String}[]
    results = String[]

    for split_point=1:(regex_len-1)
        left_regex = join(pieces[1:split_point])
        matches = grep_fixed(wordlist, left_regex, split_point)
        push!(left_partials, matches)
    end
    for split_point=1:regex_len
        right_regex = join(pieces[split_point:regex_len])
        rmatches = grep_fixed(wordlist, right_regex, regex_len - split_point + 1)
        lmatches = String[""]
        if split_point > 1
            lmatches = left_partials[split_point - 1]
        end
        for i=1:min(beam, length(lmatches))
            for j=1:min(beam, length(rmatches))
                push!(results, lmatches[i] * rmatches[j])
            end
        end     
    end
    eval_results = [interpret_text(wordlist, word) for word=results]
    sort!(eval_results, by=(x -> -x[2]))
    eval_results[1:limit]
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

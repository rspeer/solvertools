# ## Getting stuff set up
using PyCall

# `importall Base` means that, when we define methods such as `print()` and
# `haskey()`, we're automatically extending the built-in functions. Otherwise
# we'd have to be explicit about the fact that we're extending them, not
# replacing them. This is much more convenient.
importall Base
using DataFrames

BASE_PATH = "."
if haskey(ENV, "SOLVERTOOLS_BASE")
    BASE_PATH = ENV["SOLVERTOOLS_BASE"]
end
MIN_LOGPROB = -1000.

# Types are really hard to reload interactively.
require("custom_types.jl")
using SolverToolsTypes

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
function roman_letters(s::String)
    if is_valid_ascii(s)
        decomposed = s
    else
        decomposed = unicodedata.normalize("NFKD", uppercase(s))
    end
    replace(decomposed, r"[^A-Z]", "")
end

function roman_letters_and_spaces(s::String)
    if is_valid_ascii(s)
        decomposed = s
    else
        decomposed = unicodedata.normalize("NFKD", uppercase(s))
    end
    replace(decomposed, r"[^A-Z ]", "")
end

function remove_spaces(s::String)
    replace(s, " ", "")
end

# ## Wordlists
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
    println("Loading wordlist: $filename")
    wordframe = load_wordframe(filename, filepath, Int64)
    build_wordlist(wordframe)
end

function build_wordlist(wordframe::DataFrame)
    wordlist::Wordlist = Wordlist()
    total = sum(wordframe[2])
    for row=1:nrow(wordframe)
        origword = wordframe[row, 1]
        word = remove_spaces(origword)
        if haskey(wordlist.wordmap, word)
            continue
        end
        if word != origword
            wordlist.canonical[word] = origword
        end
        
        freq = wordframe[row, 2]
        wordlist.wordmap[word] = log2(freq) - log2(total)

        if row % 1000000 == 0
            println("\tRead $row words")
        end
    end
    println("\tStoring greppable string")
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

function logprob(wordlist::Wordlist, word::String)
    if word == "~"  # a flag for impossible constraints
        MIN_LOGPROB * 2
    else
        wordlist[word]
    end
end

function haskey(wordlist::Wordlist, word::String)
    haskey(wordlist.wordmap, word)
end

function canonicalize(wordlist::Wordlist, word::String)
    if haskey(wordlist.canonical, word)
        wordlist.canonical[word]
    else
        word
    end
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

function grep(wordlist::Wordlist, pattern::String, func, limit::Int=10)
    regex = Regex("^" * pattern * "\$", "im")
    count = 0
    for thematch=eachmatch(regex, wordlist.sortstring)
        func(thematch.match)
        count += 1
        if count >= limit
            return
        end
    end
end

function grep(wordlist::Wordlist, pattern::String, limit::Int=10)
    results = UTF8String[]
    grep(wordlist, pattern, x -> push!(results, x), limit)
    results
end

# ### Frequency statistics
function interpret_text(wordlist::Wordlist, text::String)
    best_partial_results = UTF8String[]
    best_partial_logprob = Float64[]
    indexes = [chr2ind(text, chr) for chr=1:length(text)]

    # I keep track of indexes and character offsets separately, so that
    # this code could keep working given non-ASCII input. For example,
    # I may want to do things with IPA.
    for (rind, right_edge)=enumerate(indexes)
        push!(best_partial_results, canonicalize(wordlist, text[1:right_edge]))
        push!(best_partial_logprob, logprob(wordlist, text[1:right_edge]))
        for (lind, left_edge)=enumerate(indexes)
            if left_edge >= right_edge
                break
            end
            right_string = canonicalize(wordlist, text[(left_edge+1):right_edge])
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
# `interpret_pattern` is like `interpret_text` for a regex.
function interpret_pattern(wordlist::Wordlist, pattern::String)
    best_partial_results = UTF8String[]
    best_partial_logprob = Float64[]
    
    if regextools.is_deterministic(pattern)
        return interpret_text(wordlist, pattern)
    end
    # If this isn't a fixed-length regex, fall back on ordinary "grep",
    # without assembling phrases.
    minlen, maxlen = regextools.regex_len(pattern)
    if minlen != maxlen
        word = grep(wordlist, pattern, 1)
        if length(word) > 0
            return word
        else
            return "~"
        end
    end
    regex_len::Int = maxlen

    pieces = UTF8String[regextools.regex_index(pattern, i-1) for i=1:regex_len]
    for right_edge=1:length(pieces)
        best_match = [grep(wordlist, join(pieces[1:right_edge]), 1), "~"][1]
        push!(best_partial_results, best_match)
        push!(best_partial_logprob, logprob(wordlist, best_match))
        
        for left_edge=1:(right_edge - 1)
            right_regex = join(pieces[(left_edge+1):right_edge])
            right_match = [grep(wordlist, right_regex, 1), "~"][1]

            left_logprob = best_partial_logprob[left_edge]
            right_logprob = logprob(wordlist, right_match)
            if left_logprob + right_logprob > best_partial_logprob[right_edge]
                best_partial_logprob[right_edge] = left_logprob + right_logprob
                best_partial_results[right_edge] = best_partial_results[left_edge] * " " * right_match
            end
        end
    end
    return best_partial_results[end], best_partial_logprob[end]
end

# `phrase_grep` returns multiple results like `grep`, but allows the string to
# split into two pieces that match the wordlist separately.
#
# This probably isn't enough. Nutrimatic probably does this better.
function phrase_grep(wordlist::Wordlist, pattern::String,
                     limit::Int=20, beam::Int=3)
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
        matches = grep(wordlist, left_regex, beam)
        push!(left_partials, matches)
    end

    for split_point=1:regex_len
        right_regex = join(pieces[split_point:regex_len])
        rmatches = grep(wordlist, right_regex, beam)
        lmatches = String[""]
        if split_point > 1
            lmatches = left_partials[split_point - 1]
        end
        for lmatch=lmatches
            for rmatch=rmatches
                push!(results, lmatch * rmatch)
            end
        end
    end

    eval_results = [interpret_text(wordlist, word) for word=results]
    sort!(eval_results, by=(x -> -x[2]))
    #elapsed = time() - st
    #println("interpret_pattern: $elapsed")
    eval_results[1:min(limit, length(eval_results))]
end
metatron = phrase_grep

# ## Letter distribution statistics

function letter_bigrams(s::String)
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

# ## Anagrams
# A LetterCountVec is a vector of 26 integers, representing the counts of
# letters in a string. A LetterProportionVec is a vector of 26 floats,
# representing their relative proportions.
#
# These objects also have 2-D matrix equivalents.
typealias LetterCountVec Vector{Int8}
typealias LetterCountMat Matrix{Int8}
typealias LetterProportionVec Vector{Float32}
typealias LetterProportionMat Matrix{Float32}

letter_freqs = Float32[
    0.08331452,  0.01920814,  0.04155464,  0.03997236,  0.11332581,
    0.01456622,  0.02694035,  0.02517641,  0.08116646,  0.00305369,
    0.00930784,  0.05399477,  0.02984008,  0.06982714,  0.06273243,
    0.0287359 ,  0.00204801,  0.07181286,  0.07714659,  0.06561591,
    0.03393991,  0.01232891,  0.01022719,  0.0037979 ,  0.01733258,
    0.00303336
]

function proportional_vector(v::LetterCountVec)
    float32(v / sum(v))::LetterProportionVec
end

function letters_to_vec(letters::String)
    vec = zeros(Int8, 26)
    for ch in letters
        vec[letter_index(ch)] += 1
    end
    if any(vec .< 0)
        error("too many letters")
    end
    vec::LetterCountVec
end

function alphagram(letters::String)
    join(sort(collect(remove_spaces(letters))))
end

function alphagram(vec::LetterCountVec)
    lets = Char[]
    for i=1:26
        for j=1:vec[i]
            push!(lets, letter_unindex(i))
        end
    end
    join(lets)
end

function anahash(vec::LetterProportionVec)
    anomaly = vec - letter_freqs
    indices = (1:26)[anomaly .> 0.0]
    join(map(unindex, indices))
end

function anahash(letters::String)
    anahash(to_proportion(letters_to_vec(letters)))
end

function build_anagram_table(wordlist)
    alpha_map = Dict{String, Vector{String}}()
    labels = String[]
    table::LetterCountMat = zeros(Int8, 26, length(wordlist))
    col = 0
    wordorder = sort(collect(split(wordlist.sortstring, "\n")), by=length, alg=MergeSort)
    offsets = Int[1]
    cur_offset = 1
    for word=wordorder
        alph = alphagram(word)
        if haskey(alpha_map, alph)
            if length(alpha_map[alph]) < 3
                push!(alpha_map[alph], canonicalize(wordlist, word))
            end
        else
            col += 1
            table[:, col] = letters_to_vec(alph)
            push!(labels, alph)
            alpha_map[alph] = String[canonicalize(wordlist, word)]

            wordlen = length(alph)
            if wordlen > cur_offset
                push!(offsets, col)
                cur_offset += 1
                println("\tgenerating alphagrams of $wordlen letters")
            end
        end
    end
    AnagramTable(alpha_map, labels, table, offsets, wordlist)
end

function anagram_single(atable::AnagramTable, vec::LetterCountVec)
    alph = alphagram(vec)
    if haskey(atable.alpha_map, alph)
        return atable.alpha_map[alph]
    else
        return []
    end
end

function anagram_single(atable::AnagramTable, vec::LetterCountVec, wildcards::Int)
    if wildcards == 0
        return anagram_single(atable, vec)
    end
    nletters = sum(vec) + wildcards
    if nletters + 1 > length(atable.offsets)
        error("Too many letters")
    end
    mincol = atable.offsets[nletters]
    maxcol = atable.offsets[nletters + 1] - 1
    results = (String, Float32)[]
    tempvec = zeros(Int8, 26)
    for col=mincol:maxcol
        remain = wildcards
        for row=26:-1:1
            diff = vec[row] - atable.table[row, col]
            if diff < 0
                remain += diff
                if remain < 0
                    break
                end
            end
        end
        if remain == 0
            alph = atable.labels[col]
            append!(results, atable.alpha_map[alph])
        end
    end
    sort!(results, by=x -> -x[2])
    results
end

function anagram_double(atable::AnagramTable, vec::LetterCountVec, limit::Int=10000)
    results = (String, Float32)[]
    tempvec = zeros(Int8, 26)
    halflen = div(sum(vec) + 1, 2) + 1
    if halflen > length(atable.offsets)
        error("Too many letters")
    end
    for simple_result=anagram_single(atable, vec)
        logprob1 = logprob(atable.wordlist, remove_spaces(simple_result))
        push!(results, (simple_result, logprob1))
    end
    endcol = atable.offsets[halflen] - 1
    for col=1:endcol
        ok = true
        for row=26:-1:1
            diff = vec[row] - atable.table[row, col]
            if diff < 0
                ok = false
                break
            else
                tempvec[row] = diff
            end
        end
        if ok
            alph = atable.labels[col]
            thesewords = atable.alpha_map[alph]
            otherwords = anagram_single(atable, tempvec)
            if length(otherwords) > 0
                for word1=thesewords
                    logprob1 = logprob(atable.wordlist, remove_spaces(word1))
                    for word2=otherwords
                        logprob2 = logprob(atable.wordlist, remove_spaces(word2))
                        phrase = "$word1 $word2"
                        push!(results, (phrase, logprob1 + logprob2))
                    end
                end
            end
            if length(results) > limit
                break
            end
        end
    end
    sort!(results, by=x -> -x[2])
    results
end

function anagram(atable, text)
    anagram_double(atable, letters_to_vec(uppercase(remove_spaces(text))))
end

function print(io::IO, at::AnagramTable)
    print(io, "AnagramTable with offsets ")
    show(io, at.offsets)
end
show(io::IO, at::AnagramTable) = print(io, at)

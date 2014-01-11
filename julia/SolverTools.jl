# ## Getting stuff set up
using PyCall
using DataFrames
using Base
importall Base

BASE_PATH = "."
if haskey(ENV, "SOLVERTOOLS_BASE")
    BASE_PATH = ENV["SOLVERTOOLS_BASE"]
end
WORDLIST_PATH = joinpath(BASE_PATH, "wordlists")

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

# ## Wordlists
type Wordlist{T}
    wordmap::Dict{String, T}
    quicklists::Dict{Int, Dict{Char, Array{String}}}
    
    function Wordlist()
        new(Dict{String, T}(),
            Dict{Int, Dict{Char, Array{String}}}())
    end
end

function load_wordlist(filename::String, filepath::String=WORDLIST_PATH, T::Type=Int64)
    path = joinpath(filepath, filename)
    wordframe::DataFrame = readtable(
        path, separator='\t', header=false,
        nastrings=ASCIIString[], colnames=["word", "freq"],
        coltypes={UTF8String, T}
    )
    build_wordlist(wordframe, T)
end

function build_wordlist(wordframe::DataFrame, T::Type)
    Wordlist{T} result = Wordlist
end

length(w::Wordlist) = nrow(w.frame)

start(w::Wordlist) = 1
next(w::Wordlist, i) = (w[i], i+1)
done(w::Wordlist, i) = i > length(w)

function words(wordlist::Wordlist)
    wordlist.frame["word"]
end

function asciiwords(wordlist::Wordlist)
    ret::Array{ASCIIString,1}
    ret = wordlist.frame["word"]
end

function getindex(wordlist::Wordlist, i)
    wordlist.frame[i, "word"], wordlist.frame[i, "freq"]
end

function grep(regex::Regex, wordlist::Wordlist, func)
    for word=words(wordlist)
        if ismatch(regex, word)
            func(word)
        end
    end
end

function grep(regex::Regex, wordlist::Wordlist)
    results = UTF8String[]
    grep(regex, wordlist, x -> push!(results, x))
    results
end

function bigrams(s::UTF8String)
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

function bigrams(s::ASCIIString)
    [s[i:i+1] for i=1:length(s) - 1]
end

function letter_table(wordlist::Wordlist)
    utable = zeros(Int64, 26)
    for i=1:length(wordlist)
        (word, freq) = wordlist[i]
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
    for i=1:length(wordlist)
        (word, freq) = wordlist[i]
        if is_valid_ascii(word)
            aword = ascii(word)
            btable[boundary, letter_index(aword[1])] += freq
            for b=bigrams(aword)
                i1 = letter_index(b[1])
                i2 = letter_index(b[2])
                btable[i1, i2] += freq
            end
            btable[letter_index(aword[end]), boundary] += freq
        end
    end
    btable
end

## DAWGs: Directed Acyclic Word Graphs
# A DAWG is a DAG for testing whether something is in a wordlist; think of it
# as a trie that can rejoin itself for sets of common endings.
#
# So far, we're assuming that the strings being stored in a DAWG are made of
# a contiguous set of ASCII characters -- particularly the English capital
# letters starting at A. This is a limiting assumption but it makes things
# very efficient.

type Dawg
    # If `is_key` is true, the path you took to get here is a word.
    is_key::Bool

    # `children` is a cell array, one cell per symbol in the alphabet, whose
    # defined members are child Dawgs.
    children::Array{Any,1}

    Dawg(nsymbols) = new(false, cell(nsymbols))
end

function lookup(dawg::Dawg, key::ASCIIString, pos::Int, len::Int)
    if pos > len
        return dawg.is_key
    else
        idx = letter_index(key[pos])
        if isdefined(dawg.children, idx)
            return lookup(dawg.children[idx], key, pos + 1, len)
        else
            return false
        end
    end
end

function haskey(dawg::Dawg, key::ASCIIString)
    lookup(dawg, key, 1, length(key))
end

function traverse(dawg::Dawg, prefix::ASCIIString, func)
    if dawg.is_key
        func(dawg, prefix)
    end
    for i=1:length(dawg.children)
        if isdefined(dawg.children, i)
            child = dawg.children[i]
            letter = string(letter_unindex(i))
            traverse(child, prefix * letter, func)
        end
    end
end

function keys(dawg::Dawg)
    result = ASCIIString[]
    function action(dawg::Dawg, prefix::ASCIIString)
        push!(result, prefix)
    end
    traverse(dawg, "", action)
    result
end

function add!(dawg::Dawg, key::ASCIIString)
    if key == ""
        dawg.is_key = true
    else
        idx = letter_index(key[1])
        if !isdefined(dawg.children, idx)
            dawg.children[idx] = Dawg(26)
        end
        add!(dawg.children[idx], key[2:end])
    end
end

function build_dawg(words)
    root = Dawg(26)
    for word=words
        add!(root, ascii(word))
    end
    optimize(root)
end

# This duplicates a lot of code for traversing a Dawg, but keeps track of much
# more information that we won't want to have when we're not optimizing a Dawg.
# That's why it needs to be a separate function.
function collect_keysets(dawg::Dawg, fwdmap::Dict{Uint64, Dawg}, backmap::ObjectIdDict)
    keyset = ASCIIString[]
    if dawg.is_key
        push!(keyset, "")
    end
    for i=1:length(dawg.children)
        if isdefined(dawg.children, i)
            child = dawg.children[i]
            letter = string(letter_unindex(i))
            for newkey=collect_keysets(child, fwdmap, backmap)
                push!(keyset, letter * newkey)
            end
        end
    end
    keyhash = hash(keyset)
    if !haskey(fwdmap, keyhash)
        fwdmap[keyhash] = dawg
    end
    backmap[dawg] = keyhash
    keyset
end

function optimize(dawg::Dawg)
    fwdmap = Dict{Uint64, Dawg}()
    backmap = ObjectIdDict()

    collect_keysets(dawg, fwdmap, backmap)
    println("Optimized to $(length(fwdmap)) nodes, from $(length(backmap)) originally")
    optimize_subdawg(dawg, fwdmap, backmap)
end

function optimize_subdawg(dawg, fwdmap, backmap)
    for i=1:length(dawg.children)
        if isdefined(dawg.children, i)
            child = dawg.children[i]
            keyhash = backmap[child]
            if fwdmap[keyhash] == child
                optimize_subdawg(child, fwdmap, backmap)
            else
                dawg.children[i] = fwdmap[keyhash]
            end
        end
    end
    dawg
end

function show(io::IO, dawg::Dawg)
    show(io, keys(dawg))
end

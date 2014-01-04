# ## Getting stuff set up
using PyCall
using DataFrames

function getenv(var::String, default::String)
    val = ccall( (:getenv, "libc"),
                Ptr{Uint8}, (Ptr{Uint8},), bytestring(var))
    if val == C_NULL
        default
    else
        bytestring(val)
    end
end

WORDLIST_PATH = getenv("SOLVERTOOLS_WORDLISTS", "../wordlists")

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
type Wordlist
    frame::DataFrame
end

function load_wordlist(filename::String, filepath::String=WORDLIST_PATH)
    path = joinpath(filepath, filename)
    wordlist::DataFrame = readtable(
        path, separator='\t', header=false,
        nastrings=ASCIIString[], colnames=["word", "freq"],
        coltypes={UTF8String, Int64}
    )
    Wordlist(wordlist)
end

Base.length(w::Wordlist) = nrow(w.frame)

Base.start(w::Wordlist) = 1
Base.next(w::Wordlist, i) = (w[i], i+1)
Base.done(w::Wordlist, i) = i > length(w)

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


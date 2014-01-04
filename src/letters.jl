using PyCall

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

# `standardize_letters`: Remove accents, convert to uppercase, and keep only
# the letters A-Z.
function standardize_letters(s::UTF8String)
    decomposed = unicodedata.normalize("NFKD", uppercase(s))
    replace(decomposed, r"[^A-Z]", "")
end

function standardize_letters(s::ASCIIString)
    replace(uppercase(s), r"[^A-Z]", "")
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

function caesar_shift(letters::String, shift::Char)
    caesar_shift(letters, letter_index(uppercase(shift)) - 1)
end

function caesar_shift(letter::Char, shift::Char)
    caesar_shift(letter, letter_index(uppercase(shift)) - 1)
end

# ### The Vigenère cipher
# `vigenere`: shift a string around the alphabet according to a cycle of
# offsets.
#
# If the offsets are given as a string (as they often are), each character
# specifies what 'A' maps to in that position. The key 'A' is therefore the
# identity.
function vigenere(letters::String, key::String)
    key = standardize_letters(key)
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

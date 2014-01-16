# # Wordlists
module Wordlists
using DataFrames
using Base
importall Base

export Wordlist, load_wordframe, load_wordlist, build_wordlist, logprob, canonicalize

BASE_PATH = "."
if haskey(ENV, "SOLVERTOOLS_BASE")
    BASE_PATH = ENV["SOLVERTOOLS_BASE"]
end

MIN_LOGPROB = -1000.

type Wordlist
    wordmap::Dict{String, Float32}
    canonical::Dict{String, String}
    sortstring::String

    function Wordlist()
        new(
            Dict{String, Float32}(),
            Dict{String, String}(),
            ""
        )
    end
end

function remove_spaces(s::UTF8String)
    replace(s, " ", "")
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
    wordlist[word]
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

# End of module Wordlists
end

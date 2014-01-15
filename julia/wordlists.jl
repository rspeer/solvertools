# # Wordlists
module Wordlists
using DataFrames
using Base
importall Base

export Wordlist, load_wordframe, load_wordlist, build_wordlist

BASE_PATH = "."
if haskey(ENV, "SOLVERTOOLS_BASE")
    BASE_PATH = ENV["SOLVERTOOLS_BASE"]
end

MIN_LOGPROB = -1000.

type Wordlist
    wordmap::Dict{String, Float64}
    quickstrings::Dict{Int, Dict{Char, String}}
    sortstring::String

    function Wordlist()
        new(
            Dict{String, Float64}(),
            Dict{Int, Dict{Char, String}}(),
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
    wordframe = load_wordframe(filename, filepath, Int64)
    build_wordlist(wordframe)
end

function build_wordlist(wordframe::DataFrame)
    wordlist::Wordlist = Wordlist()
    sublists = Dict{Int, Dict{Char, Array{String}}}()
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
            sublists[wordlength] = Dict{Char, Array{String}}()
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
        wordlist.quickstrings[len] = Dict{Char, String}()
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

# End of module Wordlists
end

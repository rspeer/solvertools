require("wordlists.jl")
using Wordlists

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
    wordorder = sort(collect(keys(wordlist)), by=length)
    offsets = Int[]
    for word=wordorder
        alph = alphagram(word)
        if haskey(alpha_map, alph)
            push!(alpha_map[alph], canonicalize(wordlist, word))
        else
            col += 1
            table[:, col] = letters_to_vec(alph)
            push!(labels, alph)
            alpha_map[alph] = [canonicalize(wordlist, word)]

            wordlen = length(alph)
            if wordlen > length(offsets) + 1
                offsets.push!(col)
                println("\tgenerating alphagrams of $wordlen letters")
            end
        end
    end
    AnagramTable(alpha_map, labels, table, offsets, wordlist)
end

function anagram_single(atable::AnagramTable, vec::LetterCountVec)
    alph = alphagram(vec)
    if haskey(atable.alpha_map, alph)
        return atable.alph_map[alph]
    else
        return []
    end
end

function anagram_double(atable::AnagramTable, vec::LetterCountVec, limit::Int=10000)
    results = (String, Float32)[]
    tempvec = zeros(Int8, 26)
    halflen = div(sum(vec) + 1, 2)
    if halflen > length(atable.offsets)
        error("Too many letters")
    end
    endcol = atable.offsets(halflen)
    for col=1:endcol
        ok = true
        for row=26:-1:1
            diff = vec[row] - atable.table[row, col]
            if diff < 0
                ok = False
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
                    logprob1 = logprob(atable.wordlist, word1)
                    for word2=otherwords[1:3]
                        logprob2 = logprob(atable.wordlist, word2)
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


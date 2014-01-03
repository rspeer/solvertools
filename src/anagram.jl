include("letters.jl")

const letter_freqs = [
    0.08331452,  0.01920814,  0.04155464,  0.03997236,  0.11332581,
    0.01456622,  0.02694035,  0.02517641,  0.08116646,  0.00305369,
    0.00930784,  0.05399477,  0.02984008,  0.06982714,  0.06273243,
    0.0287359 ,  0.00204801,  0.07181286,  0.07714659,  0.06561591,
    0.03393991,  0.01232891,  0.01022719,  0.0037979 ,  0.01733258,
    0.00303336
]

# A LetterCountVec is a vector of 26 integers, representing the counts of
# letters in a string. A LetterProportionVec is a vector of 26 floats,
# representing their relative proportions.
#
# These objects also have 2-D matrix equivalents.
typealias LetterCountVec Vector{Int8}
typealias LetterCountMat Matrix{Int8}
typealias LetterProportionVec Vector{Float32}
typealias LetterProportionMat Matrix{Float32}

function proportional_vector(v::LetterCountVec)
    float32(v / sum(v))::LetterProportionVec
end

function letters_to_vec(letters::String)
    letters2 = standardize(letters)
    vec = zeros(Int8, 26)
    for ch in letters2
        vec[letter_index(ch)] += 1
    end
    if any(vec .< 0)
        error("too many letters")
    end
    vec::LetterCountVec
end

function alphagram(letters::String)
    join(sort(collect(standardize_letters(letters))))
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

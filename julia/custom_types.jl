# # SolverToolsTypes
module SolverToolsTypes
using DataFrames
export Wordlist, AnagramTable

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

type AnagramTable
    alpha_map::Dict{String, Vector{String}}
    labels::Vector{String}
    table::Matrix{Int8}
    offsets::Vector{Int}
    wordlist::Wordlist
end

# End of module SolverToolsTypes
end

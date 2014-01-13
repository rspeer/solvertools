include("julia/SolverTools.jl")
require("ArgParse")
using ArgParse


function main()
    settings = ArgParseSettings()
    @add_arg_table settings begin
        "unigram_file"
            help="File to read a DataFrame of unigrams from"
            required=true
        "bigram_file"
            help="File to read a DataFrame of bigrams from"
            required=true
    end

    args = parse_args(settings)
    trim_bigrams(args["unigram_file"], args["bigram_file"], 8)
end

main()

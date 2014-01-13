#!/usr/bin/env julia
# This is a fork of jocco, by lcw: https://github.com/lcw/jocco
#
# __Jocco__ is a [Julia] port of [Docco], the quick-and-dirty,
# hundred-line-long, literate-programming-style documentation generator. It
# produces HTML that displays your comments alongside your code. Comments are
# passed through [Pandoc], and code is syntax highlighted with [Pygments].
# This page is the result of running Jocco against its own source file:
#
#     julia jocco.jl jocco.jl
#
# and the HTML file is generated in the `docs` directory.
#
# Using [Pandoc] allows us to have math inline $x=y$ or in display mode
# $$
#   \begin{aligned}
#     \nabla \times \vec{\mathbf{B}} -\, \frac1c\,
#     \frac{\partial\vec{\mathbf{E}}}{\partial t} &=
#     \frac{4\pi}{c}\vec{\mathbf{j}} \\
#     \nabla \cdot \vec{\mathbf{E}} &= 4 \pi \rho \\
#     \nabla \times \vec{\mathbf{E}}\, +\, \frac1c\,
#     \frac{\partial\vec{\mathbf{B}}}{\partial t} &= \vec{\mathbf{0}} \\
#     \nabla \cdot \vec{\mathbf{B}} &= 0
#   \end{aligned}
# $$
# if you wish.  This uses the [MathJax] Content Distribution Network script to
# turn $\LaTeX$ source into rendered output and thus an internet connection is
# required.  [MathJax] may be installed locally if offline access is desired.
#
# @Knuth:1984:LP might be something we should read when building a literate
# programming tool.  We can also reference this in a note.[^1]
#
# This [Julia] port of [Docco] is roughly structured the same as the [Lua]
# port [Locco].  Its source is released in the public domain and is available
# on [GitHub](http://github.com/lcw/jocco).
#

# We use comments to separate the different chunks of code so that they can all
# be processed together with [Pygments] and the HTML can be split up after.
# Likewise, we use level five headers to separate the chunks of documentation.
const code_sep = "# CUT HERE\n"
const code_sep_html = "<span class=\"c\"># CUT HERE</span>\n"
const docs_sep = "\n##### CUT HERE\n\n"
const docs_sep_html = r"<h5 id=\"cut-here.*\">CUT HERE</h5>\n"

# For now we leave the HTML template hard coded.
const header = "<!DOCTYPE html>

<html>
<head>
  <title>%title%</title>
  <meta http-equiv=\"content-type\" content=\"text/html; charset=UTF-8\">
  <link rel=\"stylesheet\" media=\"all\" href=\"jocco.css\" />
  <script type=\"text/javascript\"
    src=\"http://cdn.mathjax.org/mathjax/latest/MathJax.js?config=TeX-AMS-MML_HTMLorMML\">
  </script>
</head>
<body>
  <div id=\"container\">
    <div id=\"background\"></div>
    <table cellpadding=\"0\" cellspacing=\"0\">
      <thead>
        <tr>
          <th class=\"docs\">
            <h1>
              %title%
            </h1>
          </th>
          <th class=\"code\">
          </th>
        </tr>
      </thead>
      <tbody>
"

const table_entry = "
<tr id=\"section-%index%\">
<td class=\"docs\">
  <div class=\"pilwrap\">
    <a class=\"pilcrow\" href=\"#section-%index%\">&#182;</a>
  </div>
  %docs_html%
</td>
<td class=\"code\">
<div class=\"highlight\"><pre>%code_html%
</pre></div>
</td>
</tr>
"

const footer = "
      </tbody>
    </table>
  </div>
</body>
</html>"

#
# This function splits the `source` text into an array of documentation
# sections and code sections.
#
# ----------------------------------------------------------------------------
# Parameters:
# ----------- ----------------------------------------------------------------
# `source`    An `UTF8String`{.julia} of the document source to be parsed.
# ----------------------------------------------------------------------------
#
# ----------------------------------------------------------------------------
# Returns:
# ---------   ----------------------------------------------------------------
# `code`      An array of the code sections.
#
# `docs`      An array of the documentation sections.
# ----------------------------------------------------------------------------
#
function parse_source(source)
    code, docs = UTF8String[], UTF8String[]
    f = open(source)

    has_code = false
    code_text, docs_text = "", ""

    while (!eof(f))
        line = readline(f)
        line = chomp(line)
        m = match(r"^\s*(?:#\s(.*?)\s*$|$)", line)
        if m == nothing
            m = match(r"^\s*#()$", line)
        end
        if m == nothing || m.captures == (nothing,)
            has_code = true
            code_text = "$code_text$line\n"
        else
            if has_code
                push!(code, code_text)
                push!(docs, docs_text)

                has_code = false
                code_text, docs_text = "", ""
            end
            (doc_line,) = m.captures
            if(doc_line != nothing)
                docs_text = "$docs_text$doc_line\n"
            end
        end
    end
    push!(code, code_text)
    push!(docs, docs_text)

    close(f)
    code, docs
end

# This function is common to the code and documentation highlighting.  It is
# used to join text segments using `sep_in` to be processed by `cmd` as one
# file and then split back into sections using `sep_out`.
#
# ----------------------------------------------------------------------------
# Parameters:
# ------------ ---------------------------------------------------------------
# `text_array` An array of text segments to be highlighted as one document.
#
# `sep_in`     An `UTF8String`{.julia} which is inserted between text
#              segments.
#
# `sep_out`    An `UTF8String`{.julia} searched for as a `--- CUT HERE ---`
#              line to split the sections.  This string is removed from the
#              returned from returned segments.
#
# `cmd`        The joined text will be written to this `Cmd`{.julia} and the
#              text which will be split and returned will also be read from
#              this `Cmd`{.julia}.
# ----------------------------------------------------------------------------
#
# ----------------------------------------------------------------------------
# Returns:
# ---------   ----------------------------------------------------------------
#             An array of highlighted text with a corresponding entry for each
#             passed in segment.
# ----------------------------------------------------------------------------
#
function highlight(text_array, sep_in, sep_out, cmd)
    read_stream, write_stream, proc = readandwrite(cmd)

    write(write_stream, join(text_array, sep_in))
    close(write_stream)

    text_out = readall(read_stream)
    close(read_stream)

    split(text_out, sep_out)
end

# This highlights the code using `pygmentize`.  Here we assume the code is
# written in [Julia].  We remove the `<div>`{.html} and `<pre>`{.html} tags
# first and last segments so that each segment can be wrapped in their own
# tags using the template.
function highlight_code(code)
    cmd = `pygmentize -l julia -f html -O encoding=utf8`
    code = highlight(code, code_sep, code_sep_html, cmd)
    if length(code) > 0
        code[1] = replace(code[1], "<div class=\"highlight\"><pre>", "")
        code[length(code)] = replace(code[length(code)], "</pre></div>", "")
    end
    #unshift!(code,"")
    code
end

# This returns an array of file names in the directory `dir` with the
# extension `wanted_ext`.
function get_files_with_extension(dir, wanted_ext)
    files = split(chomp(readall(`ls $dir`)), "\n")
    ext_files = Array(UTF8String, 1, 0)
    for f in files
        filename = joinpath(dir, f)
        ext = splitext(filename)[2]
        pathname, filebase = splitdir(filename)
        if(ext == wanted_ext)
            ext_files = [ext_files filename]
        end
    end
    ext_files
end

# This joins an argument `arg` array `vals` such that `args` is returned as:
#
#     args = [arg, vals[1], arg, vals[2], arg, vals[3], ...]
#
function join_arg_vals(arg, vals)
    args = Array(UTF8String, 1, 2*length(vals))
    args[1:2:end] = arg
    args[2:2:end] = vals
    args
end

# Here the documentation is passed through [Pandoc] using its extension of
# markdown to generate the HTML.  BibTeX files that are stored in the
# `docs` directory are passed into [Pandoc] through with the `--bibliography`
# argument.  Like wise [Citation Style Language](http://citationstyles.org/)
# (CSL) files found in the `docs` directory are passed into [Pandoc] with the
# `--csl` argument.
#
# To use jocco with any other project, copy the contents of the /jocco/docs
# directory to the docs directory of the project.
#
# Further any files with the extension `.hs` in the `docs` directory are
# considered [Pandoc]
# [scripting](http://johnmacfarlane.net/pandoc/scripting.html) filters which
# read and write [Pandoc] AST in [JSON] format.  In the Jocco docs directory
# there are two such filters, which also must be copied to the docs directory of
# any project you wish to use with jocco. You must also have Haskell (ghc) and the
# Haskell platform installed (haskell-platform), and then run 'cabal update" and
# 'cabal install pandoc'; errors such as 'Could not find module `Text.Pandoc' result
# from not doing this. If you don't wish to do this, purge the docs directory of
# the two .hs files
#
# The first `doiLinks.hs` adds a
# hyperlink to DOI citation entries.  The second `pygments.hs` from [Matti
# Pastell](https://bitbucket.org/mpastell/pandoc-filters/) uses [Pygments] to
# highlight code blocks.  This way we can have highlighted Julia code on the
# documentation side too like this:
#
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~ {.julia .numberLines}
# function foo(bar)
#     bar
# end
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#
function highlight_docs(docs, path)
    bib_files = get_files_with_extension(path, ".bib")
    csl_files = get_files_with_extension(path, ".csl")
    pan_files = get_files_with_extension(path, ".hs")

    bib_args = join_arg_vals("--bibliography", bib_files)
    csl_args = join_arg_vals("--csl",          csl_files)

    pan_args = ["-S" bib_args csl_args "-f" "markdown" "-t" "json"]

    cmd = `pandoc $pan_args`
    for p in pan_files
        cmd = cmd |> `runhaskell $p`
    end
    cmd  = cmd |> `pandoc -S --mathjax -f json -t html`

    docs = highlight(docs, docs_sep, docs_sep_html, cmd)

end

# Here the generated code and documentation is substituted into the templates
# and written to the HTML file.
function generate_html(source, path, file, code, docs, jump_to)
    outfile = joinpath(path, replace(file, r"jl$", "html"))
    f = open(outfile, "w")

    h = replace(header, r"%title%", source)
    write(f, h)

    lines = max(length(docs), length(code))

    # Pad code and docs arrays so they have the same number of lines
    while (length(docs) < lines)
        push!(docs, "")
    end
    while (length(code) < lines)
        push!(code, "")
    end

    assert(length(code)==length(docs))
    for i = 1:lines
        t = replace(table_entry, r"%index%", i)
        t = replace(t, r"%docs_html%", docs[i])
        t = replace(t, r"%code_html%", code[i])
        write(f, t)
    end

    write(f, footer)

    close(f)
    println("$file --> $outfile")
end

function generate_documentation(source, path, file, jump_to)
    code, docs = parse_source(source)
    assert(length(code) == length(docs))
    code, docs = highlight_code(code), highlight_docs(docs, path)
    assert(length(code) == length(docs))
    generate_html(source, path, file, code, docs, jump_to)
end

# Documentation is generated in the `docs` directory for all of the files pass
# in as arguments to this program.
function main()
    jump_to = ""

    for source in ARGS
        file = chomp(readall(`basename $source`))
        path = "docs"

        run(`mkdir -p $path`)

        generate_documentation(source, path, file, jump_to)
    end
end

main()

# ## References
#
# [^1]: A citation without locators [@Knuth:1984:LP].
#
# [Docco]: http://jashkenas.github.com/docco/
# [Pandoc]: http://johnmacfarlane.net/pandoc/
# [JSON]: http://www.json.org/
# [Julia]: http://julialang.org/
# [Lua]: http://lua.org/
# [Locco]: http://rgieseke.github.com/locco/
# [MathJax]: http://www.mathjax.org/
# [Pygments]: http://pygments.org/

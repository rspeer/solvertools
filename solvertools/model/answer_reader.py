from solvertools.util import get_datafile

def answer_reader(year):
    f = open(get_datafile("corpora/answers/mystery%s.dat" % year))
    for line in f:
        parts = line.split('"')
        if len(parts) < 2: continue
        yield parts[1]
    f.close()

use grep_regex::RegexMatcher;
use grep_searcher::sinks::UTF8;
use grep_searcher::{MmapChoice, Searcher, SearcherBuilder};
use std::error::Error;
use std::fs::File;
use std::io::prelude::*;

// If you know how to handle errors better than this, you do it.
// I'm not going to get bogged down in it.
type BoxResult<T> = Result<T, Box<dyn Error>>;

#[derive(Debug)]
pub struct GreppableWordlist {
    file: File,
    searcher: Searcher,
}

impl GreppableWordlist {
    pub fn new(filename: &str) -> BoxResult<GreppableWordlist> {
        let file = File::open(&filename)?;
        GreppableWordlist::new_from_file(file)
    }

    pub fn new_from_file(file: File) -> BoxResult<GreppableWordlist> {
        let mut builder = SearcherBuilder::new();
        let mmap_auto = unsafe { MmapChoice::auto() };
        builder
            .bom_sniffing(false)
            .line_number(true)
            .memory_map(mmap_auto);
        let searcher = builder.build();
        Ok(GreppableWordlist {
            file: file,
            searcher: searcher,
        })
    }

    pub fn grep(&mut self, pattern: &str) -> BoxResult<Vec<String>> {
        let matcher = RegexMatcher::new(pattern)?;
        let mut matches: Vec<String> = vec![];
        self.searcher.search_file(
            matcher,
            &self.file,
            UTF8(|_lnum, line| {
                matches.push(line.to_string());
                Ok(true)
            }),
        )?;
        Ok(matches)
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::io::SeekFrom;
    use tempfile::tempfile;

    #[test]
    fn it_works() -> BoxResult<()> {
        let mut file: File = tempfile()?;
        writeln!(file, "clue\nanswer\ncoin\n")?;
        file.seek(SeekFrom::Start(0))?;
        let mut wordlist = GreppableWordlist::new_from_file(file)?;
        let result = wordlist.grep(r"co.n")?;
        assert_eq!(result, vec!["coin\n"]);

        let result2 = wordlist.grep(r"c...")?;
        assert_eq!(result2, vec!["clue\n", "coin\n"]);

        Ok(())
    }
}

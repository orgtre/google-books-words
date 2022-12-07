# Google Books words

This repository (work-in-progress) creates datasets of all the words in the [Google Books Ngram Corpus](https://storage.googleapis.com/books/ngrams/books/datasetsv3.html) (v3/20200217, all languages). Other than just listing the words and their frequency, like is already done in the repositories [hackerb9/gwordlist](https://github.com/hackerb9/gwordlist) and [orgtre/google-books-ngram-frequency](https://github.com/orgtre/google-books-ngram-frequency), this repository aims to include additional useful metadata for each word, such as part-of-speech (POS) tags and its word family. Hopefully this can become a comprehensive resource for creating language learning materials.


## Python code

All the code is in the [src](src) directory. To download the [source data](src/source-data-paths.txt), parse it, and produce the datasets of words in each language run [google-books-words.py](src/google-books-words.py). The necessary dependencies can be installed using [Poetry](https://python-poetry.org) and they are listed in [pyproject.toml](src/pyproject.toml). Note that the code is heavy on memory: When parsing the English subcorpus, which is the largest by far, a computer with 16GB RAM will have to resort to swapping at times; however, for other languages this doesn't occur.

The code outputs a range of csv files for each language (currently not uploaded as they are too big). The higher the number in the suffix, the higher the degree of cleaning. Currently the final outputs are the files suffixed `_2b`. In these files words containing non-word characters have been omitted, plus same words whose case differs have been merged into one entry, as have entries whose part-of-speech tag differs. They contain the following columns:

- `word` The word to which the data on the corresponding row refers.
- `freq` The frequency with which the word occurs in the corpus. The unit is number of times per 1 billion words. The file suffixed `_2b_totals` provides the necessary total counts for converting this into absolute frequencies.
- `freq50` Like 'freq' but only for books published from 1970.
- `freq10` Like 'freq' but only for books published from 2010.
- `nvol` The share of volumes (books) in which the word is found. The largest number of different books a word occurs in is used as denominator; this value can also be found in the '_2b_totals' file.
- `pos` The part-of-speech tags Google has assigned to the word, see [this paper](https://storage.googleapis.com/pub-tools-public-publication-data/pdf/38277.pdf).
- `rel` The relative frequency with which each POS tag is assigned (in percent). Tags making up less than 10% are omitted by default (the 'pos_cutoff' setting controls this).

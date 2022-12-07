# Build the google-boooks-words repository

import gzip, os, re, csv
import requests
from timeit import default_timer as timer
import pandas as pd


###############################################################################
# Settings

# List of languages for which code should run
langs = ["german"]
# langs = ["chinese_simplified", "english", "french", 
#          "german", "hebrew", "italian", "russian", "spanish"]
# each element has to be one of "english", "english-us", "english-gb", 
# "english-fiction", "chinese_simplified", "french", "german", 
# "hebrew", "italian", "russian", or "spanish"

download_chunk_size = 1000000
# Influences the download time.
# The default works well with a bandwidth of 50MB/s,
# bringing the download speed close to that.

# Control which parts to rerun if output files are already there:
redownload_files = False
reparse_files = False
reclean_1_to_2 = False

pos_cutoff = 10
# Omit part-of-speech (POS) uses making up less than this percentage for word.

lowcase_cutoff = 0.5
# Cutoff for the share of uses of a word where it is lowercase above which
# the whole entry will be lowercase.
# Set to 0.5 to get words faster.
# Only 0.5 currently works.


###############################################################################
# Info

# The compressed raw data for all langauges takes up around 38GB.
# Reading in all gz files for English takes 5.5GB of memory.


###############################################################################
# Constants etc.

urllistfile = "src/source-data-paths.txt"
raw_data_path = "bld/raw-data"
tmp_path = "bld/tmp"


langcode = {"english": "eng", "english-us": "eng-us", "english-gb": "eng-gb", 
            "english-fiction": "eng-fiction", "chinese_simplified": "chi_sim", 
            "french": "fre", "german": "ger", "hebrew": "heb", 
            "italian": "ita", "russian": "rus", "spanish": "spa"}

langcode_reverse = {"eng": "english", "eng-us": "english-us",
                    "eng-gb": "english-gb", "eng-fiction": "english-fiction",
                    "chi_sim": "chinese_simplified", "fre": "french",
                    "ger": "german", "heb": "hebrew", "ita": "italian",
                    "rus": "russian", "spa": "spanish"}


###############################################################################
# Functions

def check_cwd():
    if not os.path.isfile('src/google-books-words.py'):
        print("Warning: 'src/google-books-words.py' not found "
              + "where expected. Trying to switch to parent directory.")
        os.chdir("..")
        if not os.path.isfile('src/google-books-words.py'):
            raise Exception("Error: Working directory is not the repository "
                            + "base directory. "
                            + "'src/google-books-words.py' "
                            + "not found.")


def download_data():

    for file_url in get_urls():

        file_name = file_url.split(sep="/")[-1]
        file_langcode = file_url.split(sep="/")[-2]
        file_lang = langcode_reverse[file_langcode]
        
        if file_lang in langs:

            file_path = raw_data_path + '/' + file_lang
            file_fullname = file_path + '/' + file_name

            if file_name == "totalcounts-1":
                file_fullname = file_fullname + '.txt'

            if not os.path.exists(file_path):
                os.makedirs(file_path)

            if redownload_files or (not os.path.isfile(file_fullname)):
                start = timer()
                download_file(file_url, file_fullname)
                end = timer()
                print(f"   download time: {round(end - start, 2)}s")


def get_urls():
    """Returns a list of urls from which to actually download a file."""

    urls = list()

    with open(urllistfile) as f:
        for line in f:
            urls += [line.strip()]

    return urls

                
def download_file(url, local_filename):
    with requests.get(url, stream=True) as r:
        r.raise_for_status()
        total_length = int(r.headers.get('content-length'))
        print(f"   downloading {total_length/1e6:.1f} MB...")
        print_period = max(round(total_length/download_chunk_size/10), 1)
        download_length = 0
        i = 1
        with open(local_filename, 'wb') as f:
            for chunk in r.iter_content(chunk_size=download_chunk_size):
                download_length += len(chunk)
                f.write(chunk)
                if i % print_period == 0:
                    print(f"   {download_length/total_length*100:.0f}% done")
                i += 1
    return local_filename


def get_data_for_lang(lang, small=True, filter=False):
    print("Getting data from: ")
    data = list()
    dir = raw_data_path + '/' + lang
    for file in sorted(os.listdir(dir)):
        if file.endswith(".gz"):
            print(dir + '/' + file)
            data += get_data_from_gz_file(dir + '/' + file,
                                          lang, small, filter)
    return data


def get_data_from_gz_file(gz_file, lang, small=True, filter=False):
    with gzip.open(gz_file, 'rt') as f:
        if small:
            data = [extract_word_freqs_small(line) for line in f]
        else:
            if filter:
                data = [d for line in f if
                        (d := extract_filter_word_freqs(line, lang))
                        is not None]
            else:
                data = [extract_word_freqs(line) for line in f]
    return data


def extract_word_freqs_small(line):
    """Extracts ngram and frequencies from one line of a .gz file."""

    # split line by tab
    list_of_line_elements = line.strip().split('\t')

    # first element is always the ngram
    ngram = list_of_line_elements[0]
    
    # remainder is always a list with elements of form
    # "year,frequency,number_of_volumes"
    # sorted increasingly by year but with gaps
    year_freq = list_of_line_elements[1:]

    # split out year frequencies

    freq = 0

    for yf in year_freq:

        yfs = yf.split(",")
        freq += int(yfs[1])
    
    return (ngram, freq)



def extract_word_freqs(line):
    """Extracts ngram and frequencies from one line of a .gz file."""

    # split line by tab
    list_of_line_elements = line.strip().split('\t')

    # first element is always the ngram
    ngram = list_of_line_elements[0]

    # remainder is always a list with elements of form
    # "year,frequency,number_of_volumes"
    # sorted increasingly by year but with gaps
    year_freq = list_of_line_elements[1:]

    # split out year frequencies

    freq = 0
    freq50 = 0
    freq10 = 0
    nvol = 0

    for yf in year_freq:

        yfs = yf.split(",")
        year_now = int(yfs[0])
        nvol += int(yfs[2])

        if year_now < 1970:
            freq += int(yfs[1])            
        elif year_now < 2010:
            freq50 += int(yfs[1])
        else:
            freq10 += int(yfs[1])

    freq += freq50 + freq10
    freq50 += freq10

    return  (ngram, freq, freq50, freq10, nvol)


def extract_filter_word_freqs(line, lang):
    """Extracts ngram and frequencies from one line of a .gz file."""

    # split line by tab
    list_of_line_elements = line.strip().split('\t')

    # first element is always the ngram
    ngram = list_of_line_elements[0]

    # filter
    if lang == 'russian':
        nonword_regex = r"[^\w'-]|[0-9]"
    elif lang == 'hebrew':
        nonword_regex = r"[^\w'\"]|[0-9]"
    else:
        nonword_regex = r"[^\w']|[0-9]"
        
    if re.search(nonword_regex, ngram):
        return None
        
    # remainder is always a list with elements of form
    # "year,frequency,number_of_volumes"
    # sorted increasingly by year but with gaps
    year_freq = list_of_line_elements[1:]

    # split out year frequencies

    freq = 0
    freq50 = 0
    freq10 = 0
    nvol = 0

    for yf in year_freq:

        yfs = yf.split(",")
        year_now = int(yfs[0])
        nvol += int(yfs[2])

        if year_now < 1970:
            freq += int(yfs[1])            
        elif year_now < 2010:
            freq50 += int(yfs[1])
        else:
            freq10 += int(yfs[1])

    freq += freq50 + freq10
    freq50 += freq10

    return  (ngram, freq, freq50, freq10, nvol)


def get_data_0():
    if not os.path.exists(tmp_path):
        os.makedirs(tmp_path)
    for lang in langs:
        outfile = tmp_path + '/' + lang + '_0.csv'
        if reparse_files or (not os.path.isfile(outfile)):
            print(f"Getting data 0 for {lang}")
            d = get_data_for_lang(lang, small=True)
            print("Sorting...")
            d.sort(key=lambda tup: tup[1], reverse=True)
            print("Saving...")
            with open(outfile, 'w') as f:
                writer = csv.writer(f)
                writer.writerow(['word', 'freq'])
                writer.writerows(d)

                
def get_data_1():
    if not os.path.exists(tmp_path):
        os.makedirs(tmp_path)
    for lang in langs:
        outfile = tmp_path + '/' + lang + '_1.csv'
        if reparse_files or (not os.path.isfile(outfile)):
            print(f"Getting data 1 for {lang}")
            d = get_data_for_lang(lang, small=False, filter=True)
            print("Sorting...")
            d.sort(key=lambda tup: tup[1], reverse=True)
            print("Saving...")
            with open(outfile, 'w') as f:
                writer = csv.writer(f)
                writer.writerow(['word', 'freq', 'freq50', 'freq10', 'nvol'])
                writer.writerows(d)



def clean_1_to_2(lang):

    infile = tmp_path + '/' + lang + '_1.csv'
    d = pd.read_csv(infile)
    # takes 1GB in memory

    icols = d.select_dtypes('integer').columns
    d[icols] = d[icols].apply(pd.to_numeric, downcast='unsigned')
    d = d.astype({"word":"string[pyarrow]"})
    # takes only 370MB like this with 11,061,370 rows

    # handle entries ending with "_" (note: no grouping here as done later)
    d.word = d.word.str.replace(r"_+$", "", regex=True)
    d = d[~d.word.str.contains("^$")]

    dt = d[["word", "freq"]][d.word.str.contains("_")]
    d = d[~d.word.str.contains("_")]

    d_tmp_path = tmp_path + '/' + "d.csv"
    d.to_csv(d_tmp_path, index=False)
    del d

    
    ## dt

    # remove entries with multiple _
    dt = dt[~dt.word.str.contains("_.*_")]

    # remove entries starting with _
    dt = dt[~dt.word.str.contains(r"^_")]

    # collapse case
    dt.word = dt.word.str.lower()
    dt = dt.groupby("word", as_index=False)['freq'].sum()
    dt = dt.sort_values(by="freq", ascending=False).reset_index(drop=True)

    # split out POS and keep only entries with valid POS tag
    dt = (pd.concat([dt['word']
                     .str.split("_", expand=True), dt['freq']], axis=1))
    dt.columns = ['word', 'pos', 'freq']
    pos_tags = "(?:noun|adj|verb|adp|adv|conj|x|det|pron|prt|num)"
    dt = dt[dt.pos.str.contains(rf"^{pos_tags}$")]

    # create relative frequency of POS within word group
    dt['rel'] = ((100 * dt['freq'] /
                  dt['freq'].groupby(dt['word']).transform('sum'))
                 .round(0).astype(int))

    # drop POS entries not making the cutoff
    dt = dt[dt.rel >+ pos_cutoff]
    del dt['freq']

    # group by word and concat pos and rel columns
    # much faster like this!
    dt = dt.astype({"pos":"string", "rel":"string"})
    dt.pos += " "
    dt.rel += " "
    dt = dt.groupby('word', as_index=False)[["pos", "rel"]].sum()
    dt.pos = dt.pos.str[:-1]
    dt.rel = dt.rel.str[:-1]

    dt_tmp_path = tmp_path + '/' + "dt.csv"
    dt.to_csv(dt_tmp_path, index=False)
    del dt


    ## d

    d = pd.read_csv(d_tmp_path)
    icols = d.select_dtypes('integer').columns
    d[icols] = d[icols].apply(pd.to_numeric, downcast='unsigned')
    d = d.astype({"word":"string[pyarrow]"})

    d = collapse_case(d, "word", "freq", "wordlow", lowcase_cutoff)
    # fast for 0.5 but takes like 30 min and more than 8GB
    # when not at 0.5 for italian
    # and that is without adjusting the code for more columns


    # merge d and df

    #d.to_csv(d_tmp_path, index=False)
    #d = pd.read_csv(d_tmp_path)
    dt = pd.read_csv(dt_tmp_path)
    d = d.merge(dt, how='left', on="word")
    
    del dt
    os.remove(dt_tmp_path)
    os.remove(d_tmp_path)

    d.to_csv(tmp_path + '/' + lang + "_2a.csv", index=False)
    # d = pd.read_csv(tmp_path + '/' + lang + "_2.csv")

    ds = pd.DataFrame([[d.freq.sum(), d.freq50.sum(), d.freq10.sum(),
                        d.nvol.max()]],
                      columns = ['freq', 'freq50', 'freq10', 'nvol'])
    ds.to_csv(tmp_path + '/' + lang + "_2b_totals.csv", index=False)
    
    fdenum = 1000000000
    d.freq = (d.freq/d.freq.sum() * fdenum).round(0).astype(int)
    d.freq50 = (d.freq50/d.freq50.sum() * fdenum).round(0).astype(int)
    d.freq10 = (d.freq10/d.freq10.sum() * fdenum).round(0).astype(int)
    d.nvol = (d.nvol/d.nvol.max()).round(3)

    d.to_csv(tmp_path + '/' + lang + "_2b.csv", index=False)
    


def collapse_case(df, word, count, wordlow, cutoff=0.5):
    aggdict = {word:'first'}
    aggdict.update({x: 'sum' for x in
                    [x for x in list(df) if x not in [word, wordlow]]})
    if cutoff == 0.5:
        return (df
                .sort_values(by=[count], ascending=False)
                .assign(wordlow=df[word].str.lower())
                .groupby(wordlow, as_index=False)
                .agg(aggdict)
                .drop(columns=[wordlow])
                .sort_values(by=[count], ascending=False)
                .reset_index(drop=True))
    else:
        return (df
                .assign(wordlow=df["word"].str.lower())
                .groupby(wordlow, as_index=False)
                .apply(wordcase_by_cutoff, word, count, wordlow, cutoff)
                .drop(columns=[wordlow])
                .sort_values(by=[count], ascending=False)
                .reset_index(drop=True))


def wordcase_by_cutoff(df, word, count, wordlow, cutoff):
    """Return series of word case and count based on a cutoff value.
    If it exists, the lowercase version of 'word' is returned as long
    as its share of all words in 'df' is larger than 'cutoff'.
    Else the most common version is returned.
    """
    group_count = sum(df[count])
    share = df[count]/group_count
    is_low = df[word] == df[wordlow]
    if (is_low & (share > cutoff)).any():
        return pd.Series([df.loc[(is_low & (share > cutoff)).idxmax(), wordlow],
                          group_count], index=[word, count])
    else:
        return pd.Series([df.loc[share.idxmax(), word],
                          group_count], index=[word, count])
                
                
def main():
    check_cwd()
    download_data()
    get_data_0()
    get_data_1()
    for lang in langs:
        if reclean_1_to_2 or (not os.path.isfile(tmp_path + '/' +
                                                 lang + "_2b.csv")):
            print(f"Cleaning {lang} from 1 to 2...")
            clean_1_to_2(lang)

    
###############################################################################
# Run

# if __name__ == "__main__":
main()


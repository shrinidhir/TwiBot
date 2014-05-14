"""Common utilities for working with text, etc."""

import os
import math
from collections import defaultdict
from nltk import tokenize

PROJECT_ROOT = '/home/vidhisha/TwiBot/summarizer'
INPUT_ROOT = PROJECT_ROOT + '/input'
MODELS_ROOT = PROJECT_ROOT + '/rouge/models'
BASELINE_ROOT = PROJECT_ROOT + '/rouge/baseline'

STEMMED_IDF_FILE = 'bgIdfValues.stemmed.txt'
UNSTEMMED_IDF_FILE = '/home/vidhisha/TwiBot/summarizer/bgIdfValues.unstemmed.txt'

# The max and min word count to consider for a summary sentance.
MIN_SENT_LEN = 5
MAX_SENT_LEN = 200 #for long sentences

# The maximum similarity between two sentences that one should be
# considered a duplicate of the other.
MAX_SIM_CUTOFF = 0.4



# Token and document utils
# ------------------------

def ls(path):
    return [os.path.join(path, item) for item in os.listdir(path)]


def load_file_sents(path):
    return [sent.lower()
            for sent in tokenize.sent_tokenize(open(path).read())]


def load_collection_sents(path):
    sents = []
    for f in ls(path):
        sents.extend(load_file_sents(f))
    return sents


def get_sentences(path):
    """ loads sentences from the given path (collection or file) """
    sents = []
    try:
        # treat as a single file
        open(path).read()
        sents = load_file_sents(path)
    except IOError:
        # it's a directory!
        sents = load_collection_sents(path)
    return sents


def get_toks(path):
    return [tokenize.word_tokenize(sent) for sent in get_sentences(path)]



def get_collections(fullpath=True):
    """Return a list of tuples of (documents, summaries, baselines)
    for each collection."""
    docs = sorted(ls(collection) if fullpath else os.listdir(collection)
                  for collection in ls(INPUT_ROOT))
    models = sorted(ls(collection) if fullpath else os.listdir(collection)
                    for collection in ls(MODELS_ROOT))
    baselines = sorted(ls(BASELINE_ROOT) if fullpath else
                       os.listdir(BASELINE_ROOT))
    return zip(range(50), docs, models, baselines)


# Vectors and similarities
# ------------------------

def cosine_sim(x, y, vect_fun=None):
    """Return the cosine similarity between two vectors, defined as:

    (sum over X, Y of (x * w)) /
    sqrt(sum over X of x^2) * sqrt(sum over Y of y^2)

    If a vectorize function is provided, assumes that x, y are a list 
    of tokens and compares by vectorizing with the given vector function.
    """
    if vect_fun:
        feat_space = feature_space(x, y)
        x, y = vect_fun(feat_space, x), vect_fun(feat_space, y)

    assert len(x) == len(y), 'Vectors are not the same length.'
    zipped = zip(x, y)
    top = float(sum(v * w for v, w in zipped))
    bot = (math.sqrt(sum(pow(v, 2) for v in x))
           * math.sqrt(sum(pow(w, 2) for w in y)))
    try:
        return top / bot
    except ZeroDivisionError:
        return top / 0.00001


def binary_vectorize(feature_space, doc):
    """Given a set of words as a feature space and a tokenized document,
    return a (binary) vector representation of that document."""
    return [1 if point in doc else 0 for point in feature_space]


def freq_vectorize(feature_space, doc):
    freqs = defaultdict(lambda: 0)
    for word in doc:
        freqs[word] += 1
    return [freqs[point] if point in freqs else 0
            for point in feature_space]

def load_idf_weights():
    f = open(UNSTEMMED_IDF_FILE, 'r')
    f.readline() # Ignore first line
    return {line.split()[0]: float(line.split()[1]) for line in f}


def tfidf_vectorize(feature_space, doc):
    idfs = load_idf_weights()
    freq_vect = freq_vectorize(feature_space, doc)
    return [freq * idfs[point] if point in idfs else 0
            for freq, point in zip(freq_vect, feature_space)]


def feature_space(doc1, doc2):
    """Given two lists of tokens, return a common feature set."""
    return sorted(set(doc1) | set(doc2))


# Summarizer utils
# ----------------

def is_valid_sent_len(sent, min_len=MIN_SENT_LEN, max_len=MAX_SENT_LEN):
    """Takes a list of tokens, returns if valid token length."""
    return min_len <= len(sent) <= max_len


def is_repeat(sent, sents, vect_fun=tfidf_vectorize, max_sim=MAX_SIM_CUTOFF):
    """Given a tokenized sentence and a list of tokenized sentences,
    return whether the sentences overlaps too highly in content with any
    of the others."""
    # TODO: Incorporate synonyms to better discern similarity
    for other_sent in sents:
        feat_space = feature_space(sent, other_sent)
        x, y = vect_fun(feat_space, sent), vect_fun(feat_space, other_sent)
        if cosine_sim(x, y) > max_sim:
            return True
    return False


def gen_summaries(name, summary_fun, start=0, end=50):
    collections = get_collections()[start:end]
    sums = []
    for i, docs, models, baseline in collections:
        collection = os.path.dirname(docs[0])
        sum_name = 'summary%02d.txt' % i
        collection_sents = get_sentences(collection)
        summary = '\n'.join(summary_fun(collection_sents, 100))
        with open(os.path.join('rouge', name, sum_name), 'w') as f:
            f.write(summary)
        sums.append((sum_name, map(os.path.basename, models)))
    return sums


if __name__ == '__main__':
    pass

"General settings."

import re

import yaml

import constants


keywords = {}        # Key: keyword in text; value: canonical keyword.
canonical_keywords = {} # Key: canonical keyword: set of keywords in text.

def read():
    global keywords
    global canonical_keywords
    try:
        with open(constants.DATA_DIR / ".chaos.yaml") as infile:
            lookup = yaml.safe_load(infile)
    except OSError:
        lookup = {}
    keywords = {}
    canonical_keywords = {}
    for keyword, canonical in lookup.get("keywords", {}).items():
        add_keyword(keyword, canonical)

def add_keyword_canonical(keyword):
    "Add keyword specifying it as 'keyword: canonical'."
    parts = keyword.split(":")
    if len(parts) == 1:
        canonical = keyword
    else:
        keyword = parts[0].strip()
        canonical = ":".join(parts[1:]).strip()
    add_keyword(keyword, canonical)

def add_keyword(keyword, canonical):
    global keywords
    global canonical_keywords
    if keyword != canonical and keywords.get(canonical) == keyword:
        raise ValueError("Circular definition of canonical keyword disallowed.")
    keywords[keyword] = canonical
    keywords[canonical] = canonical
    canonical_keywords.setdefault(canonical, set()).add(keyword)
    canonical_keywords[canonical].add(canonical)

def write():
    global keywords
    with open(constants.DATA_DIR / ".chaos.yaml", "w") as outfile:
        yaml.safe_dump({"keywords": keywords}, outfile)


read()


def get_canonical_keywords(text):
    "Get the set of canonical keywords in the given text."
    result = set()
    for keyword, canonical in keywords.items():
        if re.search(fr"\b{keyword}\S*\s?", text, re.IGNORECASE):
            result.add(canonical)
    return result

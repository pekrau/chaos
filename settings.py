"General settings."

import re

import yaml

import constants


keywords = set()


def read():
    global keywords
    try:
        with open(constants.DATA_DIR / ".chaos.yaml") as infile:
            data = yaml.safe_load(infile)
    except OSError:
        data = {}
    keywords = data.get("keywords", [])
    if isinstance(keywords, dict):
        keywords = set(keywords.values())
        write()
    else:
        keywords = set(keywords)


def write():
    global keywords
    with open(constants.DATA_DIR / ".chaos.yaml", "w") as outfile:
        yaml.safe_dump({"keywords": list(keywords)}, outfile, allow_unicode=True)


def get_all_keywords():
    "Get the list of all keywords sorted lexically."
    global keywords
    result = list(keywords)
    result.sort(key=lambda k: k.casefold())
    return result


def get_keywords(text, external_keywords=None):
    "Get the set of keywords found in the given text."
    global keywords
    kws = external_keywords or keywords
    result = set()
    for keyword in kws:
        if re.search(rf"\b{keyword}\S*\s?", text, re.IGNORECASE):
            result.add(keyword)
    return result

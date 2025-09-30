"General settings."

import yaml

import constants


def read():
    global lookup
    try:
        with open(constants.DATA_DIR / ".chaos.yaml") as infile:
            lookup = yaml.safe_load(infile)
    except OSError:
        # Key: casefolded keyword; value: original keyword
        lookup = {"keywords": {}}

def write():
    global lookup
    with open(constants.DATA_DIR / ".chaos.yaml", "w") as outfile:
        yaml.safe_dump(lookup, outfile)

lookup = {}
read()


def get_keywords(text):
    "Get the set of keywords in the given text."
    result = set()
    text = text.casefold()
    for keyword in lookup["keywords"]:
        if keyword in text:
            result.add(keyword)
    return result

def get_original_keywords(keywords):
    global lookup
    return [lookup["keywords"].get(k, k) for k in keywords]

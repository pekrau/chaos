"""chaos: Extract keywords from the text in PDF and other textual files
for entries in the www instance that request it.
"""

# Done first, to measure all work including loading modules.
from timer import Timer
timer = Timer()

from http import HTTPStatus as HTTP
import io
import mimetypes
import os
from pathlib import Path
import sys

import pymupdf
import requests

# This must be done before importing 'constants'.
from dotenv import load_dotenv

load_dotenv(override=True)

# Allow finding chaos modules.
sys.path.insert(0, str(Path(sys.path[0]).parent))

import constants
import settings


def extract(url, apikey):
    """Fetch which entries to extract keywords from, and upload the result.
    Return a dictionary with statistics.
    """
    response = requests.get(url + "/api/keywords", headers=dict(apikey=apikey))
    if response.status_code != HTTP.OK:
        raise IOError(f"invalid response: {response.status_code=} {response.content=}")
    if response.text:
        keywords = response.json()
    else:
        keywords = {}

    response = requests.get(url + "/api/keyword/extract_keywords", headers=dict(apikey=apikey))
    if response.status_code != HTTP.OK:
        raise IOError(f"invalid response: {response.status_code=} {response.content=}")

    # Remove entries not having a file attached.
    if response.text:
        data = response.json()
    else:
        data = {}
    file_entries = dict([(k, v) for k, v in data.items() if v is not None])

    failed = set()
    headers = dict(apikey=apikey)

    for entry in file_entries:
        response = requests.get(url + f"/file/{entry}/data", headers=headers)
        if response.status_code != HTTP.OK:
            failed.add(filename + ": could not fetch file data")
            continue

        content_type = response.headers["Content-Type"]
        if content_type not in constants.TEXTUAL_CONTENT_TYPES:
            failed.add(filename + ": not textual file")
            continue

        filename = entry + (mimetypes.guess_extension(content_type) or ".bin")
        filepath = Path("/tmp") / filename
        with open(filepath, "wb") as outfile:
            outfile.write(response.content)
        file_text = []
        doc = pymupdf.open(str(filepath))
        for page in doc:
            file_text.append(page.get_text())
        doc.close()
        file_text = " ".join(file_text)
        found = settings.get_canonical_keywords(file_text, external_keywords=keywords)
        if found:
            found = ", ".join(sorted(found))
        else:
            found = "*none*"
        os.unlink(filepath)

        response = requests.get(url + f"/api/entry/{entry}", headers=headers)
        if response.status_code != HTTP.OK:
            failed.add(filename + ": could not get text")
            continue
        try:
            text = response.json()["text"]
        except KeyError:
            failed.add(filename + ": no text in response")
            continue

        text = text.replace("extract_keywords", "")
        text = f"{text}\n\n## Keywords extracted from file\n\n{found}"
        response = requests.post(url + f"/api/entry/{entry}", headers=headers, data={"text": text})
        if response.status_code != HTTP.OK:
            failed.add(filename + ": could not update text")
            continue

    result = {"file_entries": len(file_entries),
              "failed": list(failed)}
    result["time"] = str(timer)
    return result


if __name__ == "__main__":
    url = os.environ["CHAOS_REMOTE_URL"]
    print(f"chaos {timer.now}, instance {url}")
    result = extract(url, os.environ["CHAOS_APIKEY"])
    if result:
        print(", ".join([f"{k}={v}" for k, v in result.items()]))

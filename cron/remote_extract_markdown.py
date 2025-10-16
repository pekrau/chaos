"""chaos: Extract Markdown from the text in PDF and other textual files
for entries in the www instance that request it.
"""

from http import HTTPStatus as HTTP
import io
import mimetypes
import os
from pathlib import Path
import sys

import requests

# This must be done before importing 'constants'.
from dotenv import load_dotenv

load_dotenv()

# Allow finding chaos modules.
sys.path.insert(0, str(Path(sys.path[0]).parent))

import constants
import settings
from timer import Timer

timer = Timer()


def extract(url, apikey):
    """Fetch which entries to extract keywords from, and upload the result.
    Return a dictionary with statistics.
    """
    response = requests.get(url + "/api/keywords", headers=dict(apikey=apikey))
    if response.status_code in (HTTP.BAD_GATEWAY, HTTP.SERVICE_UNAVAILABLE):
        raise IOError(f"invalid response: {response.status_code=}")
    elif response.status_code != HTTP.OK:
        raise IOError(f"invalid response: {response.status_code=} {response.content=}")

    if response.text:
        keywords = response.json()
    else:
        keywords = {}

    response = requests.get(
        url + "/api/keyword/extract_markdown", headers=dict(apikey=apikey)
    )
    if response.status_code in (HTTP.BAD_GATEWAY, HTTP.SERVICE_UNAVAILABLE):
        raise IOError(f"invalid response: {response.status_code=}")
    elif response.status_code != HTTP.OK:
        raise IOError(f"invalid response: {response.status_code=} {response.content=}")

    # Remove entries not having a file attached.
    if response.text:
        data = response.json()
    else:
        data = {}
    file_entries = dict([(k, v) for k, v in data.items() if v is not None])

    # Just return if no entries to process.
    if not file_entries:
        return {}

    # Process at most one page of entries in one go.
    file_entries = file_entries[0 : constants.MAX_PAGE_ENTRIES]

    # Saves time doing this here, if no entries.
    import pymupdf4llm

    failed = set()
    headers = dict(apikey=apikey)

    for entry in file_entries:
        response = requests.get(url + f"/file/{entry}/data", headers=headers)
        if response.status_code != HTTP.OK:
            failed.add(filename + ": could not fetch file data")
            continue

        mimetype = response.headers["Content-Type"]
        if mimetype not in constants.TEXTUAL_MIMETYPES:
            failed.add(filename + ": not textual file")
            continue

        filename = entry + (mimetypes.guess_extension(mimetype) or ".bin")
        filepath = Path("/tmp") / filename
        with open(filepath, "wb") as outfile:
            outfile.write(response.content)
        md_text = pymupdf4llm.to_markdown(str(filepath))
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

        text = text.replace("extract_markdown", "")
        text = f"{text}\n\n## Extracted Markdown from file\n\n{md_text}"
        response = requests.post(
            url + f"/api/entry/{entry}", headers=headers, data={"text": text}
        )
        if response.status_code != HTTP.OK:
            failed.add(filename + ": could not update text")
            continue

    result = {"file_entries": len(file_entries), "failed": list(failed)}
    result.update(time.current)
    return result


if __name__ == "__main__":
    url = os.environ["CHAOS_REMOTE_URL"]
    result = extract(url, os.environ["CHAOS_APIKEY"])
    if result:
        print(f"{timer.now}, instance {url}")
        print(", ".join([f"{k}={v}" for k, v in result.items()]))

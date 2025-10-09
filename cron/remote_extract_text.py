"chaos: Perform OCR text extraction for entries in the www instance that request it."

# Done first, to measure all work including loading modules.
from timer import Timer

timer = Timer()

from http import HTTPStatus as HTTP
import io
import mimetypes
import os
from pathlib import Path
import sys

import requests

# This must be done before importing 'constants'.
from dotenv import load_dotenv

load_dotenv(override=True)

# Allow finding chaos modules.
sys.path.insert(0, str(Path(sys.path[0]).parent))

import constants


def extract(url, apikey):
    """Fetch which entries to do OCR on, extract the text and upload it.
    Return a dictionary with statistics.
    """
    response = requests.get(
        url + "/api/keyword/extract_text", headers=dict(apikey=apikey)
    )
    if response.status_code != HTTP.OK:
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
    while len(file_entries) > constants.MAX_PAGE_ENTRIES:
        file_entries.popitem()

    failed = set()
    import easyocr  # Saves time doing this here, if no entries.

    reader = easyocr.Reader(constants.OCR_LANGUAGES, gpu=constants.OCR_GPU)
    headers = dict(apikey=apikey)

    for entry in file_entries:
        response = requests.get(url + f"/file/{entry}/data", headers=headers)
        if response.status_code != HTTP.OK:
            failed.add(filename + ": could not fetch file data")
            continue

        mimetype = response.headers["Content-Type"]
        if mimetype not in constants.IMAGE_MIMETYPES:
            failed.add(filename + ": not image file")
            continue

        filename = entry + (mimetypes.guess_extension(mimetype) or ".bin")
        filepath = Path("/tmp") / filename
        with open(filepath, "wb") as outfile:
            outfile.write(response.content)
        image_text = " ".join(reader.readtext(str(filepath), detail=0))
        os.unlink(filepath)

        response = requests.get(url + f"/api/entry/{entry}", headers=headers)
        if response.status_code != HTTP.OK:
            failed.add(filename + ": could not get entry")
            continue
        try:
            text = response.json()["text"]
        except KeyError:
            failed.add(filename + ": no entry text in response")
            continue
        text = text.replace("extract_text", "")
        text = f"{text}\n\n## Extracteded text from image\n\n{image_text}"
        response = requests.post(
            url + f"/api/entry/{entry}", headers=headers, data={"text": text}
        )
        if response.status_code != HTTP.OK:
            failed.add(filename + ": could not update text")
            continue

    result = {"file_entries": len(file_entries), "failed": list(failed)}
    result["time"] = str(timer)
    return result


if __name__ == "__main__":
    url = os.environ["CHAOS_REMOTE_URL"]
    print(f"chaos {timer.now}, instance {url}")
    result = extract(url, os.environ["CHAOS_APIKEY"])
    if result:
        print(", ".join([f"{k}={v}" for k, v in result.items()]))

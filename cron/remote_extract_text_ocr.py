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

import easyocr
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
    response = requests.get(url + "/api/keyword/extract_text_ocr", headers=dict(apikey=apikey))
    if response.status_code != HTTP.OK:
        raise IOError(f"invalid response: {response.status_code=}")

    # Remove entries not having a file attached.
    if response.text:
        data = response.json()
    else:
        data = {}
    file_entries = dict([(k, v) for k, v in data.items() if v is not None])

    failed = set()
    reader = easyocr.Reader(constants.OCR_LANGUAGES, gpu=constants.OCR_GPU)
    headers = dict(apikey=apikey)

    for entry in file_entries:
        response = requests.get(url + f"/file/{entry}/data", headers=headers)
        if response.status_code != HTTP.OK:
            failed.add(filename + ": could not fetch file data")
            continue

        content_type = response.headers["Content-Type"]
        if content_type not in constants.IMAGE_CONTENT_TYPES:
            failed.add(filename + ": not image file")
            continue

        filename = entry + (mimetypes.guess_extension(content_type) or ".bin")
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
        text = text.replace("extract_text_ocr", "")
        text = f"{text}\n\n## Text extracted from image\n\n{image_text}"
        response = requests.post(url + f"/api/entry/{entry}", headers=headers, data={"text": text})
        if response.status_code != HTTP.OK:
            failed.add(filename + ": could not update text")
            continue

    result = {"file_entries": len(file_entries),
              "failed": list(failed)}
    result["time"] = str(timer)
    return result


if __name__ == "__main__":
    url = os.environ["CHAOS_LOCAL_URL"]
    print(f"chaos instance {url}")
    result = extract(url, os.environ["CHAOS_APIKEY"])
    print(", ".join([f"{k}={v}" for k, v in result.items()]))

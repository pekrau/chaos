"chaos: Perform OCR text extraction for items in the www instance that request it."

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
from timer import Timer

timer = Timer()


def extract(url, apikey):
    """Fetch which items to do OCR on, extract the text and upload it.
    Return a dictionary with statistics.
    """
    response = requests.get(
        url + "/api/process/extract_text", headers=dict(apikey=apikey)
    )
    if response.status_code in (HTTP.BAD_GATEWAY, HTTP.SERVICE_UNAVAILABLE):
        raise IOError(f"invalid response: {response.status_code=}")
    elif response.status_code != HTTP.OK:
        raise IOError(f"invalid response: {response.status_code=} {response.content=}")

    # Remove items not having a file attached.
    if response.text:
        data = response.json()
    else:
        data = {}
    file_items = dict([(k, v) for k, v in data.items() if v is not None])

    # Just return if no items to process.
    if not file_items:
        return {}

    # Process at most one page of items in one go.
    while len(file_items) > constants.MAX_PAGE_ITEMS:
        file_items.popitem()

    # Saves time doing this here, if no items.
    import easyocr

    reader = easyocr.Reader(constants.OCR_LANGUAGES, gpu=constants.OCR_GPU)

    failed = set()
    headers = dict(apikey=apikey)

    for item in file_items:
        response = requests.get(url + f"/data/{item}", headers=headers)
        if response.status_code != HTTP.OK:
            failed.add(item + ": could not fetch file data")
            continue

        mimetype = response.headers["Content-Type"]
        if mimetype not in constants.IMAGE_MIMETYPES:
            failed.add(item + ": not image")
            continue

        filename = item + (mimetypes.guess_extension(mimetype) or ".bin")
        filepath = Path("/tmp") / filename
        with open(filepath, "wb") as outfile:
            outfile.write(response.content)
        image_text = " ".join(reader.readtext(str(filepath), detail=0))
        os.unlink(filepath)

        response = requests.get(url + f"/api/item/{item}", headers=headers)
        if response.status_code != HTTP.OK:
            failed.add(item + ": could not get item")
            continue
        try:
            text = response.json()["text"]
        except KeyError:
            failed.add(item + ": no item text in response")
            continue
        text = text.replace("extract_text", "")
        text = f"{text}\n\n## Extracted text from image\n\n{image_text}"
        response = requests.post(
            url + f"/api/item/{item}",
            headers=headers,
            data={"text": text, "process": "extract_text"},
        )
        if response.status_code != HTTP.OK:
            failed.add(item + ": could not update text")
            continue

    result = {
        "file_items": len(file_items),
        "failed": list(failed),
    }
    result.update(timer.current)
    return result


if __name__ == "__main__":
    url = os.environ["CHAOS_REMOTE_URL"]
    result = extract(url, os.environ["CHAOS_APIKEY"])
    if result:
        print(f"{timer.now}, instance {url}")
        print(", ".join([f"{k}={v}" for k, v in result.items()]))

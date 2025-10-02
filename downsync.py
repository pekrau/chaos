"chaos: Update the local directory from the www instance."

from http import HTTPStatus as HTTP
import io
import json
import os
from pathlib import Path
import tarfile
import sys

import requests

# This must be done before importing 'constants'.
with open(Path(__file__).parent / "cronenv.json") as infile:
    for name, value in json.load(infile).items():
        os.environ[name] = value

import constants
import entries


def update(url, apikey):
    """Get the current state of the remote site and update the local data.
    Return a tuple with the number of modified and deleted files.
    """

    print(f"fetching data from remote instance {url}")
    response = requests.get(url + "/api/current", headers=dict(apikey=apikey))

    if response.status_code != HTTP.OK:
        raise IOError(f"invalid response: {response.status_code=}")

    remote_entries = response.json()

    entries.read_entry_files()
    local_entries = entries.get_current()

    print(f"# local={len(local_entries)}, # remote={len(remote_entries)}")

    # Fetch the set of files with different modified timestamps from the remote.
    fetch_entries = set()
    for name, modified in remote_entries.items():
        if (name not in local_entries) or (local_entries[name] != modified):
            fetch_entries.add(name)

    if fetch_entries:
        response = requests.post(url + "/api/fetch", json={"entries": list(fetch_entries)})
        if response.status_code != HTTP.OK:
            raise IOError(f"invalid response: {response.status_code=}")
        if response.headers["Content-Type"] != constants.GZIP_CONTENT_TYPE:
            raise IOError("invalid file type from remote")
        content = response.content
        if not content:
            raise IOError("empty TGZ file from remote")
        try:
            tf = tarfile.open(fileobj=io.BytesIO(content), mode="r:gz")
            tf.extractall(path=os.environ["CHAOS_DIR"])
        except tarfile.TarError as message:
            raise IOError(f"tar file error: {message}")

    # Delete local entries that do not exist in the remote.
    delete_entries = set(local_entries.keys()).difference(remote_entries.keys())
    for name in delete_entries:
        path = constants.DATA_DIR / name
        if not path.suffix:
            path = path.with_suffix(".md")
        path.unlink()

    return (len(fetch_entries), len(delete_entries))


if __name__ == "__main__":
    fetched, deleted = update(os.environ["CHAOS_REMOTE_URL"], os.environ["CHAOS_APIKEY"])
    print(f"# {fetched=}, # {deleted=}")

"chaos: Update the local directory from the www instance."

from http import HTTPStatus as HTTP
import io
import os
from pathlib import Path
import sys
import tarfile

import requests

# This must be done before importing 'constants'.
from dotenv import load_dotenv

load_dotenv()

# Allow finding chaos modules.
sys.path.insert(0, str(Path(sys.path[0]).parent))

import constants
import entries
from timer import Timer

timer = Timer()


def update(url, apikey, targetdir):
    """Get the current state of the remote site and update the local data.
    Return a dictionary with statistics.
    """
    response = requests.get(url.rstrip("/") + "/api/", headers=dict(apikey=apikey))
    if response.status_code in (HTTP.BAD_GATEWAY, HTTP.SERVICE_UNAVAILABLE):
        raise IOError(f"invalid response: {response.status_code=}")
    elif response.status_code != HTTP.OK:
        raise IOError(f"invalid response: {response.status_code=} {response.content=}")

    remote_entries = response.json()

    targetdir = Path(targetdir)
    entries.read_entry_files()
    local_entries = entries.get_all()

    # Download the set of files with different modified timestamps from the remote.
    download_entries = set()
    for name, modified in remote_entries.items():
        if (name not in local_entries) or (local_entries[name] != modified):
            download_entries.add(name)

    if download_entries:
        response = requests.post(
            url + "/api/download",
            json={"entries": list(download_entries)},
            headers=dict(apikey=apikey),
        )
        if response.status_code in (HTTP.BAD_GATEWAY, HTTP.SERVICE_UNAVAILABLE):
            raise IOError(f"invalid response: {response.status_code=}")
        elif response.status_code != HTTP.OK:
            raise IOError(
                f"invalid response: {response.status_code=} {response.content=}"
            )

        if response.headers["Content-Type"] != constants.GZIP_MIMETYPE:
            raise IOError("invalid file type from remote")

        content = response.content
        if not content:
            raise IOError("empty TGZ file from remote")
        try:
            tf = tarfile.open(fileobj=io.BytesIO(content), mode="r:gz")
            tf.extractall(path=targetdir)
        except tarfile.TarError as message:
            raise IOError(f"tar file error: {message}")

    # Delete local entries that do not exist in the remote.
    delete_entries = set(local_entries.keys()).difference(remote_entries.keys())
    for name in delete_entries:
        path = targetdir / name
        if not path.suffix:
            path = path.with_suffix(".md")
        path.unlink()

    if not download_entries and not delete_entries:
        return {}
    else:
        result = {
            "local": len(local_entries),
            "remote": len(remote_entries),
            "downloaded": len(download_entries),
            "deleted": len(delete_entries),
        }
        result.update(timer.current)
    return result


if __name__ == "__main__":
    url = os.environ["CHAOS_REMOTE_URL"]
    targetdir = os.environ["CHAOS_DIR"]
    result = update(url, os.environ["CHAOS_APIKEY"], targetdir)
    if result:
        print(f"{timer.now}, instance {url}, target {targetdir}")
        print(", ".join([f"{k}={v}" for k, v in result.items()]))

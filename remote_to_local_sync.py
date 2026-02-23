"chaos: Update the local directory from the www instance."

from http import HTTPStatus as HTTP
import io
import os
from pathlib import Path
import sys
import tarfile

import requests

# This must be done before importing 'constants'.
import dotenv

dotenv.load_dotenv()

import constants
import items
from timer import Timer

timer = Timer()


def update(url, apikey, target_dir):
    """Get the current state of the remote site and update the local data.
    Return a dictionary with statistics.
    """
    response = requests.get(url.rstrip("/") + "/api/", headers=dict(apikey=apikey))
    if response.status_code in (HTTP.BAD_GATEWAY, HTTP.SERVICE_UNAVAILABLE):
        raise IOError(f"invalid response: {response.status_code=}")
    elif response.status_code != HTTP.OK:
        raise IOError(f"invalid response: {response.status_code=} {response.content=}")

    remote_items = response.json()

    target_dir = Path(target_dir)
    items.read_items()
    local_items = items.get_all()

    # Download the set of files with different modified timestamps from the remote.
    download_items = set()
    for name, modified in remote_items.items():
        if (name not in local_items) or (local_items[name] != modified):
            download_items.add(name)

    if download_items:
        response = requests.post(
            url + "/api/download",
            json={"items": list(download_items)},
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
            tf.extractall(path=target_dir)
        except tarfile.TarError as message:
            raise IOError(f"tar file error: {message}")

    # Delete local items that do not exist in the remote.
    delete_items = set(local_items.keys()).difference(remote_items.keys())
    for name in delete_items:
        path = target_dir / name
        if not path.suffix:
            path = path.with_suffix(".md")
        path.unlink()

    if not download_items and not delete_items:
        return {}
    else:
        result = {
            "local": len(local_items),
            "remote": len(remote_items),
            "downloaded": len(download_items),
            "deleted": len(delete_items),
        }
        result.update(timer.current)
    return result


if __name__ == "__main__":
    url = os.environ["CHAOS_REMOTE_URL"]
    target_dir = os.environ["CHAOS_DIR"]
    try:
        result = update(url, os.environ["CHAOS_APIKEY"], target_dir)
        if result:
            print(f"{timer.now}, instance {url}, target {target_dir}")
            print(", ".join([f"{k}={v}" for k, v in result.items()]))
    except IOError as error:
        print(str(error))

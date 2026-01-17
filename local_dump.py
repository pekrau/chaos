"chaos: Create a tar dump of the local production directory."

import datetime
import os
from pathlib import Path
import sys
import tarfile

# This must be done before importing 'constants'.
import dotenv

dotenv.load_dotenv()

import constants


def dump(source_dir, target_dir):
    source_dir = Path(source_dir)
    target_dir = Path(target_dir)
    tarfilepath = target_dir / f"chaos_{datetime.date.today()}.tgz"

    with tarfile.open(tarfilepath, mode="w:gz") as outfile:
        for dirpath, dirnames, filenames in os.walk(source_dir):
            abspath = Path(dirpath)
            relpath = Path(dirpath).relative_to(source_dir)
            for filename in filenames:
                outfile.add(
                    abspath.joinpath(filename), arcname=relpath.joinpath(filename)
                )


if __name__ == "__main__":
    dump(os.environ["CHAOS_DIR"], os.environ["CHAOS_DUMP_DIR"])
    print(
        str(datetime.date.today()),
        "from",
        os.environ["CHAOS_DIR"],
        "to",
        os.environ["CHAOS_DUMP_DIR"],
    )

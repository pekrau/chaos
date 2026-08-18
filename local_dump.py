"chaos: Create a tar dump of the local production directory."

import datetime
import os
from pathlib import Path
import sys
import tarfile

import dotenv


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
    dotenv.load_dotenv()   # '.env' file exists only on the local machine.
    target_dir = os.environ["CHAOS_TARGET_DIR"]
    dump_dir = os.environ["CHAOS_DUMP_DIR"]
    dump(target_dir, dump_dir)
    print(f"{datetime.date.today()} from {target_dir} to {dump_dir}")

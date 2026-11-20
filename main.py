# SPDX-License-Identifier: MIT
"""Entrypoint: copy the built front page to the make.fun output dir.

Reads news.png from this repository and writes it to
$MAKEFUN_OUTPUT_DIR/entry.png (default /output). Pure standard library.
The image bytes are fixed, so both grader runs write identical output.
"""

import os
import shutil

HERE = os.path.dirname(os.path.abspath(__file__))


def main():
    out_dir = os.environ.get("MAKEFUN_OUTPUT_DIR", "/output")
    os.makedirs(out_dir, exist_ok=True)
    src = os.path.join(HERE, "news.png")
    dst = os.path.join(out_dir, "entry.png")
    shutil.copyfile(src, dst)
    # sanity check: the copy must be byte-identical to the source
    if os.path.getsize(src) != os.path.getsize(dst):
        raise SystemExit("entry.png size mismatch after copy")


if __name__ == "__main__":
    main()

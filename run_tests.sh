#!/bin/sh
# Run the full suite with the working directory expected by the older tests,
# regardless of where this script is invoked from.
set -eu
repo_root=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
cd "$repo_root/src"
python -m unittest discover -s ../tests -p 'test_*.py'

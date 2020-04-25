#!/usr/bin/env bash
set -e # from now on exit on any error
source prepare_python_env.sh
cd "$(dirname "$0")"


pip3 install matplotlib==3.2.1
python3 -u ./testing/test.py $@

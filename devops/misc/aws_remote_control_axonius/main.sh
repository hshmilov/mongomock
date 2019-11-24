#!/usr/bin/env bash
set -e # from now on exit on any error

source venv/bin/activate
cd "$(dirname "$0")"
python3 -u main.py $@

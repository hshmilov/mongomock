#!/usr/bin/env bash

cd "$(dirname "$0")"

python3 -m virtualenv --python=python3 venv

python3 ./devops/create_pth.py

source venv/bin/activate

pip install -r requirements.txt

# Most of our python2 code is in unit tests. so just use the actual file
pip2 install --user -r ./libs/axonius-base-image/requirements2.txt
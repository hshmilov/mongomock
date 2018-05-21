#!/usr/bin/env bash

cd "$(dirname "$0")"

python3 -m virtualenv --python=python3 venv

python3 ./devops/create_pth.py

source venv/bin/activate

pip install -r requirements.txt

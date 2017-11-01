#!/usr/bin/env bash

cd "$(dirname "$0")"

python3.6 -m virtualenv venv

source venv/bin/activate

pip install -r requirements.txt

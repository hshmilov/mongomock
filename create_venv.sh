#!/usr/bin/env bash

cd "$(dirname "$0")"

virtualenv venv

source venv/bin/activate

pip install -r requirements.txt

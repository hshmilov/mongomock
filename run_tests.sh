#!/usr/bin/env bash

./create_venv.sh

source venv/bin/activate

cd testing

python run_tests.py
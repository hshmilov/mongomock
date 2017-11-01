#!/usr/bin/env bash

./create_venv.sh

source ./venv/bin/activate

cd ./testing

timeout 600 python ./run_tests.py
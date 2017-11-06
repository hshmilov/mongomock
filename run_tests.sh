#!/usr/bin/env bash

source ./venv/bin/activate
echo "Start tests"
cd ./testing
timeout 500 python run_tests.py

#!/usr/bin/env bash

source ./prepare_python_env.sh
echo "Start tests"
cd ./testing
timeout 500 python run_tests.py

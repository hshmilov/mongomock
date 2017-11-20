#!/usr/bin/env bash

source ./prepare_python_env.sh

echo "Running unitests"
pytest --ignore=testing
echo "Finished unitests"

echo "Start integration tests"
cd ./testing
timeout 500 python run_tests.py
echo "Finished integration tests"
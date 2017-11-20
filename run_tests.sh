#!/usr/bin/env bash

source ./prepare_python_env.sh

if [ $(autopep8 --exclude venv --recursive . --diff | wc -l) -ne 0 ]; then
    echo "Formatting failed!"
    autopep8 --exclude venv --recursive . --diff
    exit 1
fi

echo "Running unitests"
pytest --ignore=testing
if [ $? -ne 0 ]
then
  echo "Unitests failed"
  exit 1
fi
echo "Finished unitests"

echo "Start integration tests"
cd ./testing
timeout 500 python run_tests.py
echo "Finished integration tests"

cd ..
./format_code.sh
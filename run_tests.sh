#!/usr/bin/env bash

source ./prepare_python_env.sh

if [ $(autopep8 --exclude venv --recursive . --diff | wc -l) -ne 0 ]; then
    echo "Formatting failed!"
    autopep8 --exclude venv --recursive . --diff
    exit 1
fi

echo "Running unitests"
pytest --ignore=testing --ignore=gui/node_modules/
if [ $? -ne 0 ]
then
  echo "Unitests failed"
  exit 1
fi
echo "Finished unitests"

echo "Start integration tests"
cd ./testing
timeout 500 python run_tests.py
if [ $? -ne 0 ]
then
  echo "Integration tests failed"
  exit 1
fi
echo "Finished integration tests"

cd ..
./format_code.sh

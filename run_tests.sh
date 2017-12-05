#!/usr/bin/env bash

source ./prepare_python_env.sh

if [ $(git ls-files | grep "\.py" | xargs autopep8 --max-line-length 120 --diff | wc -l) -ne 0 ]; then
    echo "Formatting failed!"
    git ls-files | grep "\.py" | xargs autopep8 --max-line-length 120 --diff
    exit 1
fi

echo "Running unitests"
pytest --ignore=testing --ignore=plugins/gui/src/frontend --junitxml=testing/reporting/ut_report.xml
if [ $? -ne 0 ]
then
  echo "Unitests failed"
  exit 1
fi
echo "Finished unitests"

echo "Start integration tests"
cd ./testing
timeout 600 python3 run_tests.py -s -v -l --junitxml=reporting/integ_report.xml tests $@
if [ $? -ne 0 ]
then
  echo "Integration tests failed"
  exit 1
fi
echo "Finished integration tests"

cd ..
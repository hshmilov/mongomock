#!/usr/bin/env bash

source ./prepare_python_env.sh

if [ $(git ls-files | grep "\.py" | xargs autopep8 --max-line-length 120 --diff | wc -l) -ne 0 ]; then
    echo "Formatting failed!"
    git ls-files | grep "\.py" | xargs autopep8 --max-line-length 120 --diff
    exit 1
fi

if [ $(git ls-files | grep -E "(\.py|\.sh|\.yml|Dockerfile)" | xargs grep $(printf "\r") -r | wc -l) -ne 0 ]; then
    echo "Windows ending files failed!"
    exit 1
fi

# We must delete old data, or else tests will fail.
docker volume rm `docker volume ls -q`

echo "Running unitests"
pytest --ignore=testing --ignore=plugins/gui/src/frontend --ignore=adapters/juniper_adapter/py-space-platform --junitxml=testing/reporting/ut_report.xml
if [ $? -ne 0 ]
then
  echo "Unitests failed"
  exit 1
fi
echo "Finished unitests"

echo "Start integration tests"
cd ./testing
timeout 900 python3 run_tests.py tests $@
if [ $? -ne 0 ]
then
  echo "Integration tests failed"
  exit 1
fi
cd ..
echo "Finished integration tests"

echo "Start parallel tests"
cd ./testing
timeout 900 python3 run_parallel_tests.py parallel_tests/test_\*.py
if [ $? -ne 0 ]
then
  echo "parallel tests failed"
  exit 1
fi
echo "Finished parallel tests"
cd ..
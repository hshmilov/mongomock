#!/usr/bin/env bash

echo "Running unitests"
pytest -vv -s --ignore=testing \
              --ignore=deployment \
              --ignore=plugins/gui/src/frontend \
              --ignore=plugins/gui/frontend/node_modules \
              --ignore=adapters/juniper_adapter/py-space-platform
if [ $? -ne 0 ]
then
  echo "Unitests failed"
  exit 1
fi
echo "Finished unitests"

echo "Start integration tests"
cd ./testing
timeout 900 python3 run_tests.py --sanity tests $@
if [ $? -ne 0 ]
then
  echo "Integration tests failed"
  exit 1
fi
cd ..
echo "Finished integration tests"

echo "Start parallel tests"
cd ./testing
timeout 3600 python3 run_parallel_tests.py --sanity parallel_tests/test_\*.py
if [ $? -ne 0 ]
then
  echo "parallel tests failed"
  exit 1
fi
echo "Finished parallel tests"
cd ..

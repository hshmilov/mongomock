#!/usr/bin/env bash

echo "Start UI tests"
cd ./testing
timeout 900 python3 run_ui_tests.py ui_tests/tests
if [ $? -ne 0 ]
then
  echo "UI tests failed"
  exit 1
fi
echo "Finished UI tests"
cd ..

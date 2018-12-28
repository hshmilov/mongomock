#!/usr/bin/env bash

source ./prepare_python_env.sh

echo "Running rest mock server"
python3 -u ./testing/mocks/rest_server.py &> ./logs/mock_server.log &

echo "Running unitests"
python3 -u ./testing/run_pytest.py --ignore=testing --ignore=deployment --ignore=plugins/gui/src/frontend --ignore=adapters/juniper_adapter/py-space-platform $@
RC=$?
if [ $RC -ne 0 ]
then
  echo "Unitests failed with code $RC"
  exit $RC
fi

echo "Finished unit tests successfully"

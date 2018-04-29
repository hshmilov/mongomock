#!/usr/bin/env bash

CURRENT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

source ${CURRENT_DIR}/../devops/super_clean.sh

set -e # from now on exit on any error

echo "Logging to docker hub and pulling axonius-base-image"
source ${CURRENT_DIR}/../testing/test_credentials/docker_login.sh

echo "Creating venv"
./create_venv.sh

echo "Running Deployment tests"
timeout 1800 ${CURRENT_DIR}/venv_wrapper.sh ${CURRENT_DIR}/run_tests.py ${CURRENT_DIR}/tests
if [ $? -ne 0 ]
then
  echo "Deployment tests failed"
  exit 1
fi
cd ..
echo "Finished Deployment tests"

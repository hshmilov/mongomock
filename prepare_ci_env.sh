#!/usr/bin/env bash

set -e # from now on exit on any error

devops/super_clean.sh

echo "Logging to docker hub and pulling axonius-base-image"
source testing/test_credentials/docker_login.sh
time docker pull axonius/axonius-base-image

echo "Creating network"
docker network create axonius

# Note! prepare_setup.py should be the last thing in the script, since the return value
# of the whole script will be its return value. The CI uses this return value to know if
# we continue to the other stages.

echo "Building all images"
python3.6 devops/prepare_setup.py

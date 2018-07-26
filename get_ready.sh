#!/usr/bin/env bash

devops/super_clean.sh

echo "Logging to docker hub and pulling axonius-base-image"
source testing/test_credentials/docker_login.sh
time docker pull axonius/axonius-base-image

docker network create --subnet=171.17.0.0/16 axonius

docker build axonius-libs -t axonius/axonius-libs

#!/usr/bin/env bash
set -e # from now on exit on any error
source bash_imports.sh
cd "$(dirname "$0")"

sudo ./testing/test_credentials/docker_login.sh
sudo docker pull nexus.pub.axonius.com/axonius/axonius-manager
env > $TMP_ENV_FILE
sudo ./run_axonius_manager.sh
sudo docker ps
rm -f $TMP_ENV_FILE
sudo docker exec axonius-manager python3 -m pip install matplotlib==3.2.1
sudo docker exec axonius-manager python3 -u ./testing/test.py $@

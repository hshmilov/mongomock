#!/bin/bash
source bash_imports.sh
sudo /bin/sh ./testing/test_credentials/docker_login.sh
sudo docker pull nexus.pub.axonius.com/axonius/axonius-manager
env > $TMP_ENV_FILE
sudo ./run_axonius_manager.sh
sudo docker exec axonius-manager python3 ./testing/run_test_tunnel.py $@

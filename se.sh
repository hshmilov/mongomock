#!/usr/bin/env bash
set -e # from now on exit on any error
source bash_imports.sh

if [ ! -f /.dockerenv ]; then
  create_axonius_manager
  docker exec $DOCKER_NAME python3 ./devops/create_pth.py
  docker exec $DOCKER_NAME ipython -c "exit()"
  docker exec $DOCKER_NAME python3 ./devops/scripts/fast_axonius/install.py
  docker exec -w /home/ubuntu/cortex/devops/SE $DOCKER_NAME python3 se.py $@
  unset_docker_if_needed
else
  run_in_axonius_manager_se $@
fi

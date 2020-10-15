#!/usr/bin/env bash
set -e # from now on exit on any error
source bash_imports.sh

if [ ! -f /.dockerenv ]; then
  create_axonius_manager
  docker exec axonius-manager ./axonius.sh $@
  unset_docker_if_needed
else
  run_in_axonius_manager $@
fi

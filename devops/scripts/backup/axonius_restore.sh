#!/usr/bin/env bash
set -e # from now on exit on any error

source $(dirname "$0")/../../../bash_imports.sh
RESTORE_PATH="$CORTEX_PATH/devops/scripts/backup/"

if [ `docker ps | grep -c $DOCKER_NAME` -eq "0" ]; then
  echo "host container is not running..."
  exit 1
fi

if [[ "$@" =~ "-si" ]]; then
 docker exec -w "$RESTORE_PATH" "$DOCKER_NAME" python3 axonius_restore.py "$@" 2>&1 | tee axonius_restore.log
else
 docker exec -it -w "$RESTORE_PATH" "$DOCKER_NAME" python3 axonius_restore.py "$@" 2>&1 | tee axonius_restore.log
fi

#!/bin/bash
set -e
docker exec -it axonius-manager python3 devops/scripts/instances/setup_node.py
INSTANCES_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
"$INSTANCES_DIR"/change_user_pass.sh
"$INSTANCES_DIR"/add_upgrade_user.sh
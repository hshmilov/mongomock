#!/bin/bash
set -e
echo "Please enter connection string:"
read master_ip weave_pass init_name
docker exec axonius-manager python3 devops/scripts/instances/setup_node.py $master_ip $weave_pass $init_name
wait
INSTANCES_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
"$INSTANCES_DIR"/change_user_pass.sh
"$INSTANCES_DIR"/add_upgrade_user.sh
echo "Node successfully joined Axonius cluster."
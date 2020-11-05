#!/bin/bash

CORTEX_PATH="/home/ubuntu/cortex"
UPGRADE_SCRIPT_PATH="$CORTEX_PATH/devops/scripts/instances/run_upgrade_script.sh"
UPGRADE_USERNAME="axonius_upgrade"

NODE_ID_PATH="$CORTEX_PATH/.axonius_settings/.node_id"
PASSWORD_GET_URL="https://core.axonius.local/api/node/"
NODE_ID=$(cat $NODE_ID_PATH)
new_password=$(docker exec instance-control curl -kfsSL $PASSWORD_GET_URL"$NODE_ID")
echo "Password Length is: ${#new_password}"

[ $(grep -c sudo /etc/group) -eq "0" ] && sudoers_group_name='wheel' || sudoers_group_name='sudo'
sudo /usr/sbin/useradd -s $UPGRADE_SCRIPT_PATH -d $CORTEX_PATH -G docker,$sudoers_group_name $UPGRADE_USERNAME
sudo /usr/sbin/usermod --password "$(openssl passwd -1 "$new_password")" $UPGRADE_USERNAME
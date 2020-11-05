#!/bin/bash
echo "Changing node_maker password"
CORTEX_PATH='/home/ubuntu/cortex'
NODE_ID_PATH="$CORTEX_PATH/.axonius_settings/.node_id"
PASSWORD_GET_URL="https://core.axonius.local/api/node/"
NODE_ID=$(cat $NODE_ID_PATH)
new_password=$(docker exec instance-control curl -kfsSL $PASSWORD_GET_URL"$NODE_ID")
echo "Password Length is: ${#new_password}"
sudo /usr/sbin/usermod --password "$(openssl passwd -1 "$new_password")" node_maker
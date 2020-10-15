#!/bin/bash
CORTEX_PATH='/home/ubuntu/cortex'
NODE_ID_PATH="$CORTEX_PATH/.axonius_settings/.node_id"
PASSWORD_GET_URL="https://$(weave dns-lookup core)/api/node/"
NODE_ID=$(cat $NODE_ID_PATH)
new_password=$(docker exec axonius-manager curl -kfsSL $PASSWORD_GET_URL"$NODE_ID")
echo "Password Length is: ${#new_password}"
sudo /usr/sbin/usermod --password "$(openssl passwd -1 "$new_password")" node_maker
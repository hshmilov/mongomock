#!/bin/bash -xev

exec 1> >(logger -s -t $(basename $0)) 2>&1

if [[ $EUID -ne 0 ]]; then
   echo "This script must be run with root privileges"
   exit 1
fi

if [ ! -f /home/ubuntu/CHEF_PROVISION.marker ]; then
    echo "provision marker not present, exiting"
    exit 0
fi

if pgrep -x "chef-client" > /dev/null
then
   echo "chef-client is already running"
   exit 0
fi

NODE_NAME=node-$(cat /dev/urandom | tr -dc 'a-z0-9' | fold -w 8 | head -n 1)

# Create client.rb

mkdir -p /etc/chef
rm -rf /etc/chef/*

cat > /etc/chef/client.rb << EOF
chef_server_url  "https://diag-c.axonius.com/organizations/axonius"
node_name  "${NODE_NAME}"
validation_key "/home/ubuntu/axonius-validator.pem"
validation_client_name "axonius-validator"
EOF

# Create first-boot.json
cat > "/etc/chef/first-boot.json" << EOF
{
   "chef_environment": "prod",
   "run_list" :[
   "role[provision]",
   "role[after_provision]"
   ]
}
EOF

chef-client -j /etc/chef/first-boot.json
service chef-client restart